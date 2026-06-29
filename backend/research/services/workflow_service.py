from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.research.models import (
    ExperimentPlan,
    Idea,
    Job,
    NoveltyCheck,
    Paper,
    PaperCard,
    ResearchGap,
    Review,
    utc_now,
)
from backend.research.services.experiment_service import ExperimentService
from backend.research.services.export_service import ExportService
from backend.research.services.gap_service import GapService
from backend.research.services.novelty_service import NoveltyService
from backend.research.services.review_service import ReviewService
from backend.research.services.structured_idea_service import StructuredIdeaService
from backend.research.services.structured_extraction_service import StructuredExtractionService
from backend.research.services.workflow_lineage_service import (
    WorkflowLineageService,
    classify_failure,
)


@dataclass
class LiteratureToIdeasResult:
    paper: Paper
    card: PaperCard
    gaps: list[ResearchGap]
    ideas: list[Idea]
    novelty_checks: list[NoveltyCheck]
    reviews: list[Review]
    experiment_plans: list[ExperimentPlan]
    markdown_export: str
    job: Job


class JobCanceledError(RuntimeError):
    pass


class WorkflowService:
    def __init__(self, session: Session):
        self.session = session

    def queue_literature_to_ideas(
        self,
        paper_id: str,
        max_gaps: int = 4,
        max_ideas_per_gap: int = 2,
        run_review: bool = True,
        run_novelty_check: bool = True,
        run_experiment_plan: bool = True,
        include_markdown_export: bool = True,
    ) -> Job:
        job = Job(
            job_type="literature_to_ideas_workflow",
            status="pending",
            input_json=self._input_payload(
                paper_id=paper_id,
                max_gaps=max_gaps,
                max_ideas_per_gap=max_ideas_per_gap,
                run_novelty_check=run_novelty_check,
                run_review=run_review,
                run_experiment_plan=run_experiment_plan,
                include_markdown_export=include_markdown_export,
            ),
            output_json={
                "stage": "queued",
                "stage_message": "Queued literature-to-ideas workflow.",
            },
            progress=0.0,
        )
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def run_literature_to_ideas(
        self,
        paper_id: str,
        max_gaps: int = 4,
        max_ideas_per_gap: int = 2,
        run_review: bool = True,
        run_novelty_check: bool = True,
        run_experiment_plan: bool = True,
        include_markdown_export: bool = True,
    ) -> LiteratureToIdeasResult:
        job = self.queue_literature_to_ideas(
            paper_id=paper_id,
            max_gaps=max_gaps,
            max_ideas_per_gap=max_ideas_per_gap,
            run_review=run_review,
            run_novelty_check=run_novelty_check,
            run_experiment_plan=run_experiment_plan,
            include_markdown_export=include_markdown_export,
        )
        return self.run_literature_to_ideas_job(job.id)

    def run_literature_to_ideas_job(self, job_id: str) -> LiteratureToIdeasResult:
        job = self.session.get(Job, job_id)
        if job is None:
            raise ValueError("Job not found")
        if job.job_type != "literature_to_ideas_workflow":
            raise ValueError("Job is not a literature-to-ideas workflow")
        payload = job.input_json or {}
        self._mark_job_running(job.id)
        self.session.refresh(job)
        try:
            return self._run_literature_to_ideas(
                job=job,
                paper_id=payload.get("paper_id", ""),
                max_gaps=payload.get("max_gaps", 4),
                max_ideas_per_gap=payload.get("max_ideas_per_gap", 2),
                run_review=payload.get("run_review", True),
                run_novelty_check=payload.get("run_novelty_check", True),
                run_experiment_plan=payload.get("run_experiment_plan", True),
                include_markdown_export=payload.get("include_markdown_export", True),
            )
        except JobCanceledError:
            self._mark_job_canceled(job.id, "Job canceled during execution")
            raise
        except Exception as exc:
            self._fail_job(job.id, str(exc))
            raise

    def cancel_job(self, job_id: str) -> Job:
        job = self.session.get(Job, job_id)
        if job is None:
            raise ValueError("Job not found")
        if job.status in {"completed", "failed"}:
            raise ValueError(f"Cannot cancel a {job.status} job")
        if job.status != "canceled":
            job.status = "canceled"
            job.error = "Job canceled by user"
            job.finished_at = utc_now()
            self.session.commit()
            self.session.refresh(job)
        return job

    def retry_job(self, job_id: str) -> Job:
        source = self.session.get(Job, job_id)
        if source is None:
            raise ValueError("Job not found")
        if source.status not in {"failed", "canceled"}:
            raise ValueError("Only failed or canceled jobs can be retried")
        retry = Job(
            job_type=source.job_type,
            status="pending",
            input_json=dict(source.input_json or {}),
            output_json={
                "retry_of_job_id": source.id,
                "stage": "queued",
                "stage_message": "Queued retry for literature-to-ideas workflow.",
            },
            progress=0.0,
        )
        self.session.add(retry)
        self.session.commit()
        self.session.refresh(retry)
        return retry

    def _run_literature_to_ideas(
        self,
        *,
        job: Job,
        paper_id: str,
        max_gaps: int,
        max_ideas_per_gap: int,
        run_review: bool,
        run_novelty_check: bool,
        run_experiment_plan: bool,
        include_markdown_export: bool,
    ) -> LiteratureToIdeasResult:
        paper = self.session.get(Paper, paper_id)
        if paper is None:
            raise ValueError("Paper not found")

        max_gaps = max(1, min(max_gaps, 20))
        max_ideas_per_gap = max(1, min(max_ideas_per_gap, 5))
        lineage = WorkflowLineageService(self.session)

        self._raise_if_canceled(job.id)
        self._update_job(
            job.id,
            progress=0.1,
            output={"paper_id": paper.id},
            stage="extracting_card",
            stage_message="Extracting structured paper card.",
        )
        card_stage = lineage.begin_stage(
            job=self._lineage_job(job.id),
            stage_name="extract_paper_card",
            paper_id=paper.id,
            metadata={"checkpoint_key": "card_id"},
        )
        try:
            existing_card_id = self._job_output(job.id).get("card_id", "")
            card = self.session.get(PaperCard, existing_card_id) if existing_card_id else None
            card_status = "skipped" if card is not None else "succeeded"
            if card is None:
                card = StructuredExtractionService(self.session).extract_paper_card(paper.id)
            card_artifact = lineage.record_artifact(
                artifact_type="paper_card",
                job=self._lineage_job(job.id),
                paper_id=paper.id,
                stage_name="extract_paper_card",
                entity_type="paper_card",
                entity_id=card.id,
                metadata={"checkpoint_key": "card_id", "resume_status": card_status},
            )
            lineage.finish_stage(
                card_stage.id,
                status=card_status,
                output_artifact_ids=[card_artifact.id],
                metadata={"card_id": card.id},
            )
        except Exception as exc:
            self._record_stage_failure(card_stage.id, "extract_paper_card", exc)
            raise
        self._update_job(
            job.id,
            progress=0.2,
            output={"paper_id": paper.id, "card_id": card.id},
            stage="card_extracted",
            stage_message="Structured paper card extracted.",
        )
        self._raise_if_canceled(job.id)
        self._update_job(
            job.id,
            progress=0.3,
            output={},
            stage="mining_gaps",
            stage_message="Mining research gaps from paper evidence.",
        )
        gap_stage = lineage.begin_stage(
            job=self._lineage_job(job.id),
            stage_name="mine_research_gaps",
            paper_id=paper.id,
            input_artifact_ids=[card_artifact.id],
            metadata={"checkpoint_key": "gap_ids", "max_gaps": max_gaps},
        )
        try:
            existing_gap_ids = self._job_output(job.id).get("gap_ids") or []
            gaps = _load_existing_records(self.session, ResearchGap, existing_gap_ids)
            gap_status = "skipped" if gaps else "succeeded"
            if not gaps:
                gaps = GapService(self.session).mine_gaps([paper.id], max_gaps)
            gap_artifacts = [
                lineage.record_artifact(
                    artifact_type="research_gap",
                    job=self._lineage_job(job.id),
                    paper_id=paper.id,
                    stage_name="mine_research_gaps",
                    entity_type="research_gap",
                    entity_id=gap.id,
                    metadata={"checkpoint_key": "gap_ids", "resume_status": gap_status},
                )
                for gap in gaps
            ]
            lineage.finish_stage(
                gap_stage.id,
                status=gap_status,
                output_artifact_ids=[artifact.id for artifact in gap_artifacts],
                metadata={"gap_count": len(gaps)},
            )
        except Exception as exc:
            self._record_stage_failure(gap_stage.id, "mine_research_gaps", exc)
            raise
        self._update_job(
            job.id,
            progress=0.4,
            output={"gap_ids": [gap.id for gap in gaps]},
            stage="gaps_mined",
            stage_message=f"Generated {len(gaps)} research gaps.",
        )
        self._raise_if_canceled(job.id)
        self._update_job(
            job.id,
            progress=0.48,
            output={},
            stage="generating_ideas",
            stage_message="Generating structured research ideas.",
        )
        idea_stage = lineage.begin_stage(
            job=self._lineage_job(job.id),
            stage_name="generate_structured_ideas",
            paper_id=paper.id,
            input_artifact_ids=[artifact.id for artifact in gap_artifacts],
            metadata={
                "checkpoint_key": "idea_ids",
                "max_ideas_per_gap": max_ideas_per_gap,
            },
        )
        try:
            existing_idea_ids = self._job_output(job.id).get("idea_ids") or []
            ideas = _load_existing_records(self.session, Idea, existing_idea_ids)
            idea_status = "skipped" if ideas else "succeeded"
            if not ideas:
                ideas = StructuredIdeaService(self.session).generate_from_gaps(
                    [gap.id for gap in gaps],
                    max_ideas_per_gap,
                )
            idea_artifacts = [
                lineage.record_artifact(
                    artifact_type="research_idea",
                    job=self._lineage_job(job.id),
                    paper_id=paper.id,
                    stage_name="generate_structured_ideas",
                    entity_type="idea",
                    entity_id=idea.id,
                    metadata={"checkpoint_key": "idea_ids", "resume_status": idea_status},
                )
                for idea in ideas
            ]
            lineage.finish_stage(
                idea_stage.id,
                status=idea_status,
                output_artifact_ids=[artifact.id for artifact in idea_artifacts],
                metadata={"idea_count": len(ideas)},
            )
        except Exception as exc:
            self._record_stage_failure(idea_stage.id, "generate_structured_ideas", exc)
            raise
        self._update_job(
            job.id,
            progress=0.55,
            output={"idea_ids": [idea.id for idea in ideas]},
            stage="ideas_generated",
            stage_message=f"Generated {len(ideas)} research ideas.",
        )

        novelty_checks: list[NoveltyCheck] = []
        reviews: list[Review] = []
        experiment_plans: list[ExperimentPlan] = []
        novelty_service = NoveltyService(self.session)
        review_service = ReviewService(self.session)
        experiment_service = ExperimentService(self.session)
        self._raise_if_canceled(job.id)
        self._update_job(
            job.id,
            progress=0.65,
            output={},
            stage="building_quality_artifacts",
            stage_message="Creating novelty checks, reviews, and experiment plans.",
        )
        quality_stage = lineage.begin_stage(
            job=self._lineage_job(job.id),
            stage_name="build_quality_artifacts",
            paper_id=paper.id,
            input_artifact_ids=[artifact.id for artifact in idea_artifacts],
            metadata={
                "checkpoint_keys": [
                    "novelty_check_ids",
                    "review_ids",
                    "experiment_plan_ids",
                ],
                "run_novelty_check": run_novelty_check,
                "run_review": run_review,
                "run_experiment_plan": run_experiment_plan,
            },
        )
        try:
            output = self._job_output(job.id)
            novelty_checks = _load_existing_records(
                self.session,
                NoveltyCheck,
                output.get("novelty_check_ids") or [],
            )
            reviews = _load_existing_records(self.session, Review, output.get("review_ids") or [])
            experiment_plans = _load_existing_records(
                self.session,
                ExperimentPlan,
                output.get("experiment_plan_ids") or [],
            )
            quality_status = (
                "skipped"
                if (
                    (not run_novelty_check or novelty_checks)
                    and (not run_review or reviews)
                    and (not run_experiment_plan or experiment_plans)
                )
                else "succeeded"
            )
            if quality_status != "skipped":
                novelty_checks = []
                reviews = []
                experiment_plans = []
                for idea in ideas:
                    self._raise_if_canceled(job.id)
                    if run_novelty_check:
                        novelty_checks.append(novelty_service.create_check(idea.id))
                    if run_review:
                        reviews.append(review_service.create_review(idea.id))
                    if run_experiment_plan:
                        experiment_plans.append(experiment_service.create_plan(idea.id))
            quality_artifacts = []
            for check in novelty_checks:
                quality_artifacts.append(
                    lineage.record_artifact(
                        artifact_type="novelty_check",
                        job=self._lineage_job(job.id),
                        paper_id=paper.id,
                        stage_name="build_quality_artifacts",
                        entity_type="novelty_check",
                        entity_id=check.id,
                        metadata={"checkpoint_key": "novelty_check_ids"},
                    )
                )
            for review in reviews:
                quality_artifacts.append(
                    lineage.record_artifact(
                        artifact_type="review",
                        job=self._lineage_job(job.id),
                        paper_id=paper.id,
                        stage_name="build_quality_artifacts",
                        entity_type="review",
                        entity_id=review.id,
                        metadata={"checkpoint_key": "review_ids"},
                    )
                )
            for plan in experiment_plans:
                quality_artifacts.append(
                    lineage.record_artifact(
                        artifact_type="experiment_plan",
                        job=self._lineage_job(job.id),
                        paper_id=paper.id,
                        stage_name="build_quality_artifacts",
                        entity_type="experiment_plan",
                        entity_id=plan.id,
                        metadata={"checkpoint_key": "experiment_plan_ids"},
                    )
                )
            lineage.finish_stage(
                quality_stage.id,
                status=quality_status,
                output_artifact_ids=[artifact.id for artifact in quality_artifacts],
                metadata={
                    "novelty_check_count": len(novelty_checks),
                    "review_count": len(reviews),
                    "experiment_plan_count": len(experiment_plans),
                },
            )
        except Exception as exc:
            self._record_stage_failure(quality_stage.id, "build_quality_artifacts", exc)
            raise
        self._update_job(
            job.id,
            progress=0.85,
            output={
                "novelty_check_ids": [check.id for check in novelty_checks],
                "review_ids": [review.id for review in reviews],
                "experiment_plan_ids": [plan.id for plan in experiment_plans],
            },
            stage="quality_artifacts_completed",
            stage_message=(
                f"Created {len(novelty_checks)} novelty checks, {len(reviews)} reviews, "
                f"and {len(experiment_plans)} experiment plans."
            ),
        )

        markdown_export = ""
        if include_markdown_export:
            self._raise_if_canceled(job.id)
            self._update_job(
                job.id,
                progress=0.92,
                output={},
                stage="rendering_markdown",
                stage_message="Rendering Markdown dossier bundle.",
            )
            markdown_stage = lineage.begin_stage(
                job=self._lineage_job(job.id),
                stage_name="render_markdown_dossier",
                paper_id=paper.id,
                input_artifact_ids=[
                    *[artifact.id for artifact in idea_artifacts],
                    *[artifact.id for artifact in quality_artifacts],
                ],
                metadata={"checkpoint_key": "markdown_export_chars"},
            )
            try:
                markdown_export = self._render_markdown_bundle(ideas)
                markdown_artifact = lineage.record_artifact(
                    artifact_type="markdown_dossier",
                    job=self._lineage_job(job.id),
                    paper_id=paper.id,
                    stage_name="render_markdown_dossier",
                    entity_type="job",
                    entity_id=job.id,
                    path=f"artifacts/workflows/literature-to-ideas-{job.id}.md",
                    content=markdown_export,
                    metadata={"markdown_export_chars": len(markdown_export)},
                )
                lineage.finish_stage(
                    markdown_stage.id,
                    status="succeeded",
                    output_artifact_ids=[markdown_artifact.id],
                    metadata={"markdown_export_chars": len(markdown_export)},
                )
            except Exception as exc:
                self._record_stage_failure(markdown_stage.id, "render_markdown_dossier", exc)
                raise

        self._complete_job(
            job.id,
            {
                "paper_id": paper.id,
                "card_id": card.id,
                "gap_ids": [gap.id for gap in gaps],
                "idea_ids": [idea.id for idea in ideas],
                "novelty_check_ids": [check.id for check in novelty_checks],
                "review_ids": [review.id for review in reviews],
                "experiment_plan_ids": [plan.id for plan in experiment_plans],
                "markdown_export_chars": len(markdown_export),
                "stage": "completed",
                "stage_message": "Completed literature-to-ideas workflow.",
            },
        )
        job = self.session.get(Job, job.id) or job
        self.session.refresh(paper)
        self.session.refresh(card)
        return LiteratureToIdeasResult(
            paper=paper,
            card=card,
            gaps=gaps,
            ideas=ideas,
            novelty_checks=novelty_checks,
            reviews=reviews,
            experiment_plans=experiment_plans,
            markdown_export=markdown_export,
            job=job,
        )

    def _input_payload(
        self,
        *,
        paper_id: str,
        max_gaps: int,
        max_ideas_per_gap: int,
        run_novelty_check: bool,
        run_review: bool,
        run_experiment_plan: bool,
        include_markdown_export: bool,
    ) -> dict:
        return {
            "paper_id": paper_id,
            "max_gaps": max_gaps,
            "max_ideas_per_gap": max_ideas_per_gap,
            "run_novelty_check": run_novelty_check,
            "run_review": run_review,
            "run_experiment_plan": run_experiment_plan,
            "include_markdown_export": include_markdown_export,
        }

    def _mark_job_running(self, job_id: str) -> None:
        job = self.session.get(Job, job_id)
        if job is None:
            return
        self.session.refresh(job)
        if job.status == "canceled":
            raise JobCanceledError("Job canceled before execution")
        job.status = "running"
        job.progress = 0.05
        existing_output = job.output_json or {}
        lease = self._refreshed_lease(existing_output)
        lineage = WorkflowLineageService(self.session)
        job.output_json = {
            **existing_output,
            "stage": "starting",
            "stage_message": "Starting literature-to-ideas workflow.",
            "workflow_run_metadata": lineage.run_metadata(job),
            **({"lease": lease} if lease else {}),
        }
        job.started_at = utc_now()
        self.session.commit()

    def _update_job(
        self,
        job_id: str,
        *,
        progress: float,
        output: dict,
        stage: str = "",
        stage_message: str = "",
    ) -> None:
        job = self.session.get(Job, job_id)
        if job is None:
            return
        self.session.refresh(job)
        if job.status == "canceled":
            raise JobCanceledError("Job canceled during execution")
        job.progress = progress
        stage_output = {}
        if stage:
            stage_output["stage"] = stage
        if stage_message:
            stage_output["stage_message"] = stage_message
        existing_output = job.output_json or {}
        lease = self._refreshed_lease(existing_output)
        if lease:
            stage_output["lease"] = lease
        job.output_json = {**existing_output, **output, **stage_output}
        self.session.commit()

    def _complete_job(self, job_id: str, output: dict) -> None:
        job = self.session.get(Job, job_id)
        if job is None:
            return
        self.session.refresh(job)
        if job.status == "canceled":
            raise JobCanceledError("Job canceled before completion")
        existing_output = job.output_json or {}
        lease = self._refreshed_lease(existing_output)
        if lease:
            lease["completed_at"] = utc_now().isoformat()
            output = {**output, "lease": lease}
        job.status = "completed"
        job.progress = 1.0
        job.output_json = {**existing_output, **output}
        job.finished_at = utc_now()
        self.session.commit()

    def _refreshed_lease(self, output: dict) -> dict:
        lease = dict(output.get("lease") or {})
        if not lease:
            return {}
        lease["heartbeat_at"] = utc_now().isoformat()
        return lease

    def _raise_if_canceled(self, job_id: str) -> None:
        job = self.session.get(Job, job_id)
        if job is None:
            return
        self.session.refresh(job)
        if job.status == "canceled":
            raise JobCanceledError("Job canceled during execution")

    def _mark_job_canceled(self, job_id: str, error: str) -> None:
        self.session.rollback()
        job = self.session.get(Job, job_id)
        if job is None:
            return
        job.status = "canceled"
        job.error = job.error or error
        job.finished_at = job.finished_at or utc_now()
        self.session.commit()

    def _fail_job(self, job_id: str, error: str) -> None:
        self.session.rollback()
        job = self.session.get(Job, job_id)
        if job is None:
            return
        classification = classify_failure(error, (job.output_json or {}).get("stage", ""))
        output = dict(job.output_json or {})
        output["failure_taxonomy"] = classification.as_dict()
        output["stage_message"] = output.get("stage_message") or "Workflow failed."
        job.status = "failed"
        job.error = error
        job.output_json = output
        job.finished_at = utc_now()
        self.session.commit()

    def _render_markdown_bundle(self, ideas: list[Idea]) -> str:
        if not ideas:
            return ""

        export_service = ExportService(self.session)
        sections = [export_service.render_idea_markdown(idea.id) for idea in ideas]
        return "\n---\n\n".join(section.strip() for section in sections) + "\n"

    def _lineage_job(self, job_id: str) -> Job:
        job = self.session.get(Job, job_id)
        if job is None:
            raise ValueError("Job not found")
        return job

    def _job_output(self, job_id: str) -> dict:
        job = self.session.get(Job, job_id)
        if job is None:
            return {}
        return dict(job.output_json or {})

    def _record_stage_failure(self, stage_run_id: str, stage_name: str, exc: Exception) -> None:
        self.session.rollback()
        WorkflowLineageService(self.session).fail_stage(
            stage_run_id,
            error=str(exc),
            stage_name=stage_name,
        )


def _load_existing_records(session: Session, model, ids: list[str]) -> list:
    if not ids:
        return []
    records = session.query(model).filter(model.id.in_(ids)).all()
    by_id = {record.id: record for record in records}
    return [by_id[record_id] for record_id in ids if record_id in by_id]


def run_literature_to_ideas_job_background(job_id: str) -> None:
    from backend.research.db import SessionLocal

    session = SessionLocal()
    try:
        WorkflowService(session).run_literature_to_ideas_job(job_id)
    except JobCanceledError:
        return
    finally:
        session.close()
