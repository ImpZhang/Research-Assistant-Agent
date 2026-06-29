from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
import re
from typing import Any

from sqlalchemy.orm import Session

from backend.research.config import settings
from backend.research.models import Job, WorkflowArtifact, WorkflowStageRun, utc_now


FAILURE_TAXONOMY_VERSION = "workflow_failure_taxonomy_v1"
LINEAGE_SCHEMA_VERSION = "workflow_lineage_v1"
SECRET_VALUE_PATTERN = re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|Bearer\s+[A-Za-z0-9._\-]{8,})")
STANDALONE_ARTIFACT_JOB_ID = "standalone_artifact_lineage"


@dataclass(frozen=True)
class FailureClassification:
    error_type: str
    is_retriable: bool = False
    needs_manual_review: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.error_type,
            "is_retriable": self.is_retriable,
            "needs_manual_review": self.needs_manual_review,
            "taxonomy_version": FAILURE_TAXONOMY_VERSION,
        }


class WorkflowLineageService:
    def __init__(self, session: Session):
        self.session = session

    def run_metadata(self, job: Job) -> dict[str, Any]:
        return {
            "lineage_schema_version": LINEAGE_SCHEMA_VERSION,
            "code_commit": current_code_commit(),
            "config_hash": workflow_config_hash(job.input_json or {}),
            "config": workflow_config_payload(),
        }

    def begin_stage(
        self,
        *,
        job: Job,
        stage_name: str,
        paper_id: str = "",
        input_artifact_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowStageRun:
        prior_count = (
            self.session.query(WorkflowStageRun)
            .filter(
                WorkflowStageRun.job_id == job.id,
                WorkflowStageRun.stage_name == stage_name,
            )
            .count()
        )
        stage = WorkflowStageRun(
            job_id=job.id,
            paper_id=paper_id,
            stage_name=stage_name,
            status="running",
            input_artifact_ids_json=list(input_artifact_ids or []),
            retry_count=prior_count,
            code_commit=current_code_commit(),
            config_hash=workflow_config_hash(job.input_json or {}),
            metadata_json={
                "lineage_schema_version": LINEAGE_SCHEMA_VERSION,
                **(metadata or {}),
            },
            started_at=utc_now(),
        )
        self.session.add(stage)
        self.session.commit()
        self.session.refresh(stage)
        return stage

    def finish_stage(
        self,
        stage_run_id: str,
        *,
        status: str = "succeeded",
        output_artifact_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowStageRun:
        stage = self.session.get(WorkflowStageRun, stage_run_id)
        if stage is None:
            raise ValueError("Workflow stage run not found")
        stage.status = status
        stage.output_artifact_ids_json = list(output_artifact_ids or [])
        if metadata:
            stage.metadata_json = {**(stage.metadata_json or {}), **metadata}
        stage.finished_at = utc_now()
        self.session.commit()
        self.session.refresh(stage)
        return stage

    def fail_stage(
        self,
        stage_run_id: str,
        *,
        error: str,
        stage_name: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowStageRun:
        stage = self.session.get(WorkflowStageRun, stage_run_id)
        if stage is None:
            raise ValueError("Workflow stage run not found")
        classification = classify_failure(error, stage_name or stage.stage_name)
        stage.status = "failed"
        stage.error_type = classification.error_type
        stage.error_message = redact_text(error)
        stage.is_retriable = classification.is_retriable
        stage.needs_manual_review = classification.needs_manual_review
        stage.metadata_json = {
            **(stage.metadata_json or {}),
            **classification.as_dict(),
            **(metadata or {}),
        }
        stage.finished_at = utc_now()
        self.session.commit()
        self.session.refresh(stage)
        return stage

    def record_artifact(
        self,
        *,
        artifact_type: str,
        job: Job,
        paper_id: str = "",
        stage_name: str = "",
        entity_type: str = "",
        entity_id: str = "",
        path: str = "",
        content: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowArtifact:
        content_hash = hash_text(
            content
            or stable_json(
                {"entity_type": entity_type, "entity_id": entity_id, "metadata": metadata or {}}
            )
        )
        existing = None
        if entity_type and entity_id:
            existing = (
                self.session.query(WorkflowArtifact)
                .filter(
                    WorkflowArtifact.job_id == job.id,
                    WorkflowArtifact.artifact_type == artifact_type,
                    WorkflowArtifact.entity_type == entity_type,
                    WorkflowArtifact.entity_id == entity_id,
                )
                .first()
            )
        if existing is not None:
            existing.stage_name = existing.stage_name or stage_name
            existing.path = existing.path or path
            existing.content_hash = existing.content_hash or content_hash
            existing.metadata_json = {
                **(existing.metadata_json or {}),
                **(metadata or {}),
                "lineage_schema_version": LINEAGE_SCHEMA_VERSION,
            }
            self.session.commit()
            self.session.refresh(existing)
            return existing

        artifact = WorkflowArtifact(
            artifact_type=artifact_type,
            paper_id=paper_id,
            job_id=job.id,
            stage_name=stage_name,
            entity_type=entity_type,
            entity_id=entity_id,
            path=path,
            content_hash=content_hash,
            metadata_json={
                "lineage_schema_version": LINEAGE_SCHEMA_VERSION,
                "code_commit": current_code_commit(),
                "config_hash": workflow_config_hash(job.input_json or {}),
                **(metadata or {}),
            },
        )
        self.session.add(artifact)
        self.session.commit()
        self.session.refresh(artifact)
        return artifact

    def record_standalone_artifact(
        self,
        *,
        artifact_type: str,
        entity_type: str,
        entity_id: str,
        paper_id: str = "",
        stage_name: str = "",
        path: str = "",
        content: str = "",
        metadata: dict[str, Any] | None = None,
        created_by: str = "workflow",
    ) -> WorkflowArtifact:
        content_hash = hash_text(
            content
            or stable_json(
                {
                    "artifact_type": artifact_type,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "metadata": metadata or {},
                }
            )
        )
        existing = (
            self.session.query(WorkflowArtifact)
            .filter(
                WorkflowArtifact.job_id == STANDALONE_ARTIFACT_JOB_ID,
                WorkflowArtifact.artifact_type == artifact_type,
                WorkflowArtifact.entity_type == entity_type,
                WorkflowArtifact.entity_id == entity_id,
            )
            .first()
        )
        payload = {
            "lineage_schema_version": LINEAGE_SCHEMA_VERSION,
            "code_commit": current_code_commit(),
            "config_hash": workflow_config_hash({}),
            **(metadata or {}),
        }
        lineage_job = self._standalone_artifact_job()
        if existing is not None:
            existing.paper_id = paper_id or existing.paper_id
            existing.job_id = lineage_job.id
            existing.stage_name = stage_name or existing.stage_name
            existing.path = path or existing.path
            existing.content_hash = content_hash
            existing.metadata_json = {**(existing.metadata_json or {}), **payload}
            self.session.commit()
            self.session.refresh(existing)
            return existing

        artifact = WorkflowArtifact(
            artifact_type=artifact_type,
            paper_id=paper_id,
            job_id=lineage_job.id,
            stage_name=stage_name,
            entity_type=entity_type,
            entity_id=entity_id,
            path=path,
            content_hash=content_hash,
            metadata_json=payload,
            created_by=created_by or "workflow",
        )
        self.session.add(artifact)
        self.session.commit()
        self.session.refresh(artifact)
        return artifact

    def list_stage_runs(self, job_id: str) -> list[WorkflowStageRun]:
        return (
            self.session.query(WorkflowStageRun)
            .filter(WorkflowStageRun.job_id == job_id)
            .order_by(WorkflowStageRun.created_at.asc())
            .all()
        )

    def list_artifacts(self, job_id: str) -> list[WorkflowArtifact]:
        return (
            self.session.query(WorkflowArtifact)
            .filter(WorkflowArtifact.job_id == job_id)
            .order_by(WorkflowArtifact.created_at.asc())
            .all()
        )

    def list_entity_artifacts(self, entity_type: str, entity_id: str) -> list[WorkflowArtifact]:
        return (
            self.session.query(WorkflowArtifact)
            .filter(
                WorkflowArtifact.entity_type == entity_type,
                WorkflowArtifact.entity_id == entity_id,
            )
            .order_by(WorkflowArtifact.created_at.asc())
            .all()
        )

    def _standalone_artifact_job(self) -> Job:
        job = self.session.get(Job, STANDALONE_ARTIFACT_JOB_ID)
        if job is not None:
            return job
        job = Job(
            id=STANDALONE_ARTIFACT_JOB_ID,
            job_type="standalone_artifact_lineage",
            status="completed",
            input_json={},
            output_json={
                "stage": "lineage_registry",
                "stage_message": "Synthetic system job for standalone artifact lineage.",
                "workflow_run_metadata": self.run_metadata(
                    Job(input_json={}, output_json={}, job_type="standalone_artifact_lineage")
                ),
            },
            progress=1.0,
            started_at=utc_now(),
            finished_at=utc_now(),
        )
        self.session.add(job)
        self.session.flush()
        return job


def classify_failure(error: str, stage_name: str = "") -> FailureClassification:
    normalized = f"{stage_name} {error}".lower()
    if "cancel" in normalized:
        return FailureClassification("canceled", is_retriable=False)
    if "rate limit" in normalized or "429" in normalized or "too many requests" in normalized:
        return FailureClassification("provider_rate_limited", is_retriable=True)
    if "timeout" in normalized or "timed out" in normalized:
        return FailureClassification("timeout", is_retriable=True)
    if "embedding" in normalized and ("provider" in normalized or "external" in normalized):
        return FailureClassification("embedding_provider_error", is_retriable=True)
    if "rerank" in normalized and ("provider" in normalized or "external" in normalized):
        return FailureClassification("rerank_provider_error", is_retriable=True)
    if "paper not found" in normalized:
        return FailureClassification("paper_missing", needs_manual_review=True)
    if "parse" in normalized or "pdf" in normalized:
        return FailureClassification("pdf_parse_error", needs_manual_review=True)
    if "benchmark" in normalized and ("missing" in normalized or "artifact" in normalized):
        return FailureClassification("benchmark_artifact_missing", needs_manual_review=True)
    if "evidence" in normalized and ("insufficient" in normalized or "missing" in normalized):
        return FailureClassification("insufficient_evidence", needs_manual_review=True)
    if "retrieval" in normalized and "miss" in normalized:
        return FailureClassification("retrieval_miss", needs_manual_review=True)
    return FailureClassification("workflow_stage_error", is_retriable=True)


def workflow_config_payload() -> dict[str, Any]:
    return {
        "main_model": settings.main_model,
        "extraction_model": settings.extraction_model,
        "judge_model": settings.judge_model,
        "embedder": settings.embedder,
        "rerank_model": settings.rerank_model,
        "retrieval_embedding_provider": settings.retrieval_embedding_provider,
        "retrieval_rerank_provider": settings.retrieval_rerank_provider,
        "graph_rag_lite_enabled": settings.graph_rag_lite_enabled,
    }


def workflow_config_hash(job_input: dict[str, Any] | None = None) -> str:
    return hash_text(
        stable_json({"job_input": job_input or {}, "runtime": workflow_config_payload()})
    )


def current_code_commit() -> str:
    return os.getenv("APP_COMMIT_SHA") or os.getenv("GIT_COMMIT_SHA") or "local"


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def redact_text(value: str) -> str:
    redacted = SECRET_VALUE_PATTERN.sub("[redacted]", value or "")
    return redacted[:4000] + "...[truncated]" if len(redacted) > 4000 else redacted
