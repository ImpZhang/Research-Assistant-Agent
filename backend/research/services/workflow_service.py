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
            output_json={},
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
            output_json={"retry_of_job_id": source.id},
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

        self._raise_if_canceled(job.id)
        card = StructuredExtractionService(self.session).extract_paper_card(paper.id)
        self._update_job(job.id, progress=0.2, output={"paper_id": paper.id, "card_id": card.id})
        self._raise_if_canceled(job.id)
        gaps = GapService(self.session).mine_gaps([paper.id], max_gaps)
        self._update_job(job.id, progress=0.4, output={"gap_ids": [gap.id for gap in gaps]})
        self._raise_if_canceled(job.id)
        ideas = StructuredIdeaService(self.session).generate_from_gaps(
            [gap.id for gap in gaps],
            max_ideas_per_gap,
        )
        self._update_job(job.id, progress=0.55, output={"idea_ids": [idea.id for idea in ideas]})

        novelty_checks: list[NoveltyCheck] = []
        reviews: list[Review] = []
        experiment_plans: list[ExperimentPlan] = []
        novelty_service = NoveltyService(self.session)
        review_service = ReviewService(self.session)
        experiment_service = ExperimentService(self.session)
        for idea in ideas:
            self._raise_if_canceled(job.id)
            if run_novelty_check:
                novelty_checks.append(novelty_service.create_check(idea.id))
            if run_review:
                reviews.append(review_service.create_review(idea.id))
            if run_experiment_plan:
                experiment_plans.append(experiment_service.create_plan(idea.id))
        self._update_job(
            job.id,
            progress=0.85,
            output={
                "novelty_check_ids": [check.id for check in novelty_checks],
                "review_ids": [review.id for review in reviews],
                "experiment_plan_ids": [plan.id for plan in experiment_plans],
            },
        )

        markdown_export = ""
        if include_markdown_export:
            self._raise_if_canceled(job.id)
            markdown_export = self._render_markdown_bundle(ideas)

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
        job.started_at = utc_now()
        self.session.commit()

    def _update_job(self, job_id: str, *, progress: float, output: dict) -> None:
        job = self.session.get(Job, job_id)
        if job is None:
            return
        self.session.refresh(job)
        if job.status == "canceled":
            raise JobCanceledError("Job canceled during execution")
        job.progress = progress
        job.output_json = {**(job.output_json or {}), **output}
        self.session.commit()

    def _complete_job(self, job_id: str, output: dict) -> None:
        job = self.session.get(Job, job_id)
        if job is None:
            return
        self.session.refresh(job)
        if job.status == "canceled":
            raise JobCanceledError("Job canceled before completion")
        job.status = "completed"
        job.progress = 1.0
        job.output_json = output
        job.finished_at = utc_now()
        self.session.commit()

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
        job.status = "failed"
        job.error = error
        job.finished_at = utc_now()
        self.session.commit()

    def _render_markdown_bundle(self, ideas: list[Idea]) -> str:
        if not ideas:
            return ""

        export_service = ExportService(self.session)
        sections = [export_service.render_idea_markdown(idea.id) for idea in ideas]
        return "\n---\n\n".join(section.strip() for section in sections) + "\n"


def run_literature_to_ideas_job_background(job_id: str) -> None:
    from backend.research.db import SessionLocal

    session = SessionLocal()
    try:
        WorkflowService(session).run_literature_to_ideas_job(job_id)
    except JobCanceledError:
        return
    finally:
        session.close()
