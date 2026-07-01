from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
import socket
import uuid

from sqlalchemy import update
from sqlalchemy.orm import Session

from backend.research.models import Job, utc_now
from backend.research.services.workflow_service import JobCanceledError, WorkflowService


SUPPORTED_WORKFLOW_JOB_TYPES = ("literature_to_ideas_workflow",)


@dataclass
class WorkflowWorkerResult:
    worker_id: str
    status: str
    job_id: str = ""
    job_type: str = ""
    message: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def default_worker_id() -> str:
    return f"{socket.gethostname()}:{uuid.uuid4().hex[:8]}"


class WorkflowWorkerService:
    def __init__(
        self,
        session: Session,
        *,
        worker_id: str | None = None,
        stale_lease_seconds: int = 3600,
        max_auto_retries: int = 0,
        retry_backoff_seconds: int = 300,
    ):
        self.session = session
        self.worker_id = worker_id or default_worker_id()
        self.stale_lease_seconds = max(0, stale_lease_seconds)
        self.max_auto_retries = max(0, max_auto_retries)
        self.retry_backoff_seconds = max(0, retry_backoff_seconds)

    def run_once(self) -> WorkflowWorkerResult:
        stale_recovered = self.recover_stale_leases()
        if stale_recovered:
            return WorkflowWorkerResult(
                worker_id=self.worker_id,
                status="recovered_stale",
                message=f"Recovered {stale_recovered} stale workflow job leases.",
            )

        retry_created = self.retry_failed_jobs()
        if retry_created:
            return WorkflowWorkerResult(
                worker_id=self.worker_id,
                status="retry_queued",
                message=f"Queued {retry_created} failed workflow job retries.",
            )

        job = self.claim_next_job()
        if job is None:
            return WorkflowWorkerResult(
                worker_id=self.worker_id,
                status="idle",
                message="No pending workflow jobs available.",
            )
        return self._run_claimed_job(job)

    def run_job(self, job_id: str) -> WorkflowWorkerResult:
        job = self.session.get(Job, job_id)
        if job is None:
            return WorkflowWorkerResult(
                worker_id=self.worker_id,
                status="not_found",
                job_id=job_id,
                message="Workflow job not found.",
            )
        if job.job_type not in SUPPORTED_WORKFLOW_JOB_TYPES:
            return WorkflowWorkerResult(
                worker_id=self.worker_id,
                status="unsupported",
                job_id=job.id,
                job_type=job.job_type,
                message="Workflow job type is not supported by this worker.",
            )
        if job.status == "pending":
            job = self._claim_job(job)
        if job is None:
            return WorkflowWorkerResult(
                worker_id=self.worker_id,
                status="claim_conflict",
                job_id=job_id,
                message="Workflow job could not be claimed.",
            )
        if job.status != "running":
            return WorkflowWorkerResult(
                worker_id=self.worker_id,
                status=job.status,
                job_id=job.id,
                job_type=job.job_type,
                message="Workflow job is not runnable.",
            )
        return self._run_claimed_job(job)

    def _run_claimed_job(self, job: Job) -> WorkflowWorkerResult:
        try:
            WorkflowService(self.session).run_literature_to_ideas_job(job.id)
        except JobCanceledError:
            return WorkflowWorkerResult(
                worker_id=self.worker_id,
                status="canceled",
                job_id=job.id,
                job_type=job.job_type,
                message="Workflow job was canceled.",
            )
        except Exception as exc:
            return WorkflowWorkerResult(
                worker_id=self.worker_id,
                status="failed",
                job_id=job.id,
                job_type=job.job_type,
                message=str(exc),
            )

        finished = self.session.get(Job, job.id)
        return WorkflowWorkerResult(
            worker_id=self.worker_id,
            status=finished.status if finished is not None else "completed",
            job_id=job.id,
            job_type=job.job_type,
            message="Workflow job processed.",
        )

    def recover_stale_leases(
        self,
        *,
        job_types: tuple[str, ...] = SUPPORTED_WORKFLOW_JOB_TYPES,
    ) -> int:
        if self.stale_lease_seconds <= 0:
            return 0

        cutoff = utc_now() - timedelta(seconds=self.stale_lease_seconds)
        recovered = 0
        candidates = (
            self.session.query(Job)
            .filter(Job.status == "running", Job.job_type.in_(job_types))
            .order_by(Job.updated_at.asc())
            .limit(20)
            .all()
        )
        for job in candidates:
            output = dict(job.output_json or {})
            lease = dict(output.get("lease") or {})
            heartbeat_at = parse_utc_datetime(lease.get("heartbeat_at", ""))
            if heartbeat_at is None or heartbeat_at > cutoff:
                continue
            recovery_count = int(output.get("worker_recovery_count") or 0) + 1
            output["lease_history"] = [*(output.get("lease_history") or []), lease][-10:]
            output["lease"] = {}
            output["worker_recovery_count"] = recovery_count
            output["stage"] = "requeued_after_stale_lease"
            output["stage_message"] = (
                "Requeued by local worker after stale lease heartbeat "
                f"older than {self.stale_lease_seconds} seconds."
            )
            job.status = "pending"
            job.output_json = output
            job.error = ""
            job.finished_at = None
            recovered += 1
        if recovered:
            self.session.commit()
        return recovered

    def retry_failed_jobs(
        self,
        *,
        job_types: tuple[str, ...] = SUPPORTED_WORKFLOW_JOB_TYPES,
    ) -> int:
        if self.max_auto_retries <= 0:
            return 0

        cutoff = utc_now() - timedelta(seconds=self.retry_backoff_seconds)
        created = 0
        candidates = (
            self.session.query(Job)
            .filter(Job.status == "failed", Job.job_type.in_(job_types))
            .order_by(Job.finished_at.desc().nullslast(), Job.updated_at.desc())
            .limit(20)
            .all()
        )
        workflow_service = WorkflowService(self.session)
        for job in candidates:
            finished_at = ensure_utc_datetime(job.finished_at)
            if finished_at is not None and finished_at > cutoff:
                continue
            output = dict(job.output_json or {})
            retry_count = int(output.get("worker_retry_count") or 0)
            if retry_count >= self.max_auto_retries:
                continue
            if output.get("worker_retry_child_job_id"):
                continue

            retry = workflow_service.retry_job(job.id)
            retry.output_json = {
                **(retry.output_json or {}),
                "worker_retry_of_job_id": job.id,
                "worker_retry_attempt": retry_count + 1,
                "stage_message": "Queued automatic retry for failed workflow job.",
            }
            output["worker_retry_count"] = retry_count + 1
            output["worker_retry_child_job_id"] = retry.id
            output["worker_retry_queued_at"] = utc_now().isoformat()
            job.output_json = output
            self.session.commit()
            created += 1
        return created

    def claim_next_job(
        self,
        *,
        job_types: tuple[str, ...] = SUPPORTED_WORKFLOW_JOB_TYPES,
    ) -> Job | None:
        candidates = (
            self.session.query(Job)
            .filter(Job.status == "pending", Job.job_type.in_(job_types))
            .order_by(Job.created_at.asc())
            .limit(10)
            .all()
        )
        for candidate in candidates:
            claimed = self._claim_job(candidate)
            if claimed is not None:
                return claimed
        return None

    def _claim_job(self, job: Job) -> Job | None:
        now = utc_now()
        output = dict(job.output_json or {})
        output.update(
            {
                "stage": "leased",
                "stage_message": "Workflow job leased by local worker.",
                "lease": self._lease_payload(now),
            }
        )
        result = self.session.execute(
            update(Job)
            .where(Job.id == job.id, Job.status == "pending")
            .values(
                status="running",
                progress=max(float(job.progress or 0.0), 0.02),
                output_json=output,
                started_at=job.started_at or now,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            self.session.rollback()
            return None
        self.session.commit()
        claimed = self.session.get(Job, job.id)
        if claimed is not None:
            self.session.refresh(claimed)
        return claimed

    def _lease_payload(self, now: datetime) -> dict:
        timestamp = now.astimezone(UTC).isoformat()
        return {
            "worker_id": self.worker_id,
            "claimed_at": timestamp,
            "heartbeat_at": timestamp,
            "mode": "local_sqlite_worker",
        }


def parse_utc_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def ensure_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
