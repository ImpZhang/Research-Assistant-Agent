from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
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
    def __init__(self, session: Session, *, worker_id: str | None = None):
        self.session = session
        self.worker_id = worker_id or default_worker_id()

    def run_once(self) -> WorkflowWorkerResult:
        job = self.claim_next_job()
        if job is None:
            return WorkflowWorkerResult(
                worker_id=self.worker_id,
                status="idle",
                message="No pending workflow jobs available.",
            )

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
