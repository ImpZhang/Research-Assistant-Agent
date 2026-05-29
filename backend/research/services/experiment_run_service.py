from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.research.models import (
    ExperimentPlan,
    ExperimentRun,
    Idea,
    ResearchTask,
    ResearchTaskEvent,
)
from backend.research.services.artifact_graph_service import ArtifactGraphService
from backend.research.services.graph_service import GraphService


FINAL_STATUSES = {"completed", "failed", "inconclusive"}


class ExperimentRunService:
    def __init__(self, session: Session):
        self.session = session

    def create_run(
        self,
        experiment_plan_id: str,
        *,
        title: str = "",
        task_id: str | None = None,
        status: str = "running",
        dataset_snapshot: str = "",
        parameters: dict | None = None,
        metric_results: dict | None = None,
        artifact_links: list[dict] | None = None,
        conclusion: str = "",
        notes: str = "",
        created_by: str = "system",
    ) -> ExperimentRun:
        plan = self.session.get(ExperimentPlan, experiment_plan_id)
        if plan is None:
            raise ValueError("Experiment plan not found")
        task = self._load_task(task_id, plan.idea_id)
        normalized_status = status or "running"
        now = datetime.now(UTC)
        run = ExperimentRun(
            experiment_plan_id=plan.id,
            idea_id=plan.idea_id,
            task_id=task.id if task else None,
            title=title or self._default_title(plan),
            status=normalized_status,
            objective_snapshot=plan.objective,
            hypothesis_snapshot=plan.hypothesis,
            dataset_snapshot=dataset_snapshot or self._default_dataset_snapshot(plan),
            baseline_snapshot_json=plan.baselines_json or [],
            parameters_json=parameters or {},
            metric_results_json=metric_results or {},
            artifact_links_json=artifact_links or [],
            conclusion=conclusion,
            notes=notes,
            created_by=created_by or "system",
            started_at=now if normalized_status != "planned" else None,
            completed_at=now if normalized_status in FINAL_STATUSES else None,
        )
        self.session.add(run)
        self.session.flush()
        run.markdown_export = self.render_markdown(run)
        self._mark_idea_status(plan.idea_id, normalized_status)
        if task is not None:
            self.session.add(
                self._task_event(
                    task,
                    event_type="experiment_run_created",
                    note=notes or f"Registered experiment run: {run.title}.",
                    run=run,
                    created_by=created_by,
                )
            )
        self.session.commit()
        self.session.refresh(run)
        ArtifactGraphService(GraphService(self.session)).link_experiment_run(plan, run, task)
        self.session.commit()
        return run

    def update_run(
        self,
        run_id: str,
        *,
        status: str | None = None,
        dataset_snapshot: str | None = None,
        parameters: dict | None = None,
        metric_results: dict | None = None,
        artifact_links: list[dict] | None = None,
        conclusion: str | None = None,
        notes: str | None = None,
        created_by: str = "system",
    ) -> ExperimentRun:
        run = self.session.get(ExperimentRun, run_id)
        if run is None:
            raise ValueError("Experiment run not found")
        plan = self.session.get(ExperimentPlan, run.experiment_plan_id)
        task = self.session.get(ResearchTask, run.task_id) if run.task_id else None
        old_status = run.status
        if status is not None:
            run.status = status
            if status != "planned" and run.started_at is None:
                run.started_at = datetime.now(UTC)
            if status in FINAL_STATUSES and run.completed_at is None:
                run.completed_at = datetime.now(UTC)
        if dataset_snapshot is not None:
            run.dataset_snapshot = dataset_snapshot
        if parameters is not None:
            run.parameters_json = parameters
        if metric_results is not None:
            run.metric_results_json = metric_results
        if artifact_links is not None:
            run.artifact_links_json = artifact_links
        if conclusion is not None:
            run.conclusion = conclusion
        if notes is not None:
            run.notes = notes
        run.markdown_export = self.render_markdown(run)
        self._mark_idea_status(run.idea_id, run.status)
        if task is not None:
            self.session.add(
                self._task_event(
                    task,
                    event_type="experiment_run_updated",
                    note=notes
                    or f"Experiment run status changed from {old_status} to {run.status}.",
                    run=run,
                    created_by=created_by,
                )
            )
        self.session.commit()
        self.session.refresh(run)
        if plan is not None:
            ArtifactGraphService(GraphService(self.session)).link_experiment_run(plan, run, task)
            self.session.commit()
        return run

    def list_for_plan(self, experiment_plan_id: str, limit: int = 50) -> list[ExperimentRun]:
        if self.session.get(ExperimentPlan, experiment_plan_id) is None:
            raise ValueError("Experiment plan not found")
        limit = max(1, min(limit, 200))
        return (
            self.session.query(ExperimentRun)
            .filter(ExperimentRun.experiment_plan_id == experiment_plan_id)
            .order_by(ExperimentRun.created_at.desc())
            .limit(limit)
            .all()
        )

    def list_for_idea(self, idea_id: str, limit: int = 50) -> list[ExperimentRun]:
        if self.session.get(Idea, idea_id) is None:
            raise ValueError("Idea not found")
        limit = max(1, min(limit, 200))
        return (
            self.session.query(ExperimentRun)
            .filter(ExperimentRun.idea_id == idea_id)
            .order_by(ExperimentRun.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_run(self, run_id: str) -> ExperimentRun | None:
        return self.session.get(ExperimentRun, run_id)

    def render_markdown(self, run: ExperimentRun) -> str:
        lines = [
            f"# Experiment Run: {run.title}",
            "",
            f"- Run ID: `{run.id or 'pending'}`",
            f"- Experiment Plan ID: `{run.experiment_plan_id}`",
            f"- Idea ID: `{run.idea_id}`",
            f"- Task ID: `{run.task_id}`" if run.task_id else "- Task ID: none",
            f"- Status: {run.status}",
            f"- Created By: {run.created_by}",
            "",
            "## Objective",
            "",
            run.objective_snapshot or "No objective snapshot recorded.",
            "",
            "## Hypothesis",
            "",
            run.hypothesis_snapshot or "No hypothesis snapshot recorded.",
            "",
            "## Dataset Snapshot",
            "",
            run.dataset_snapshot or "No dataset snapshot recorded.",
            "",
            "## Metrics",
            "",
        ]
        metric_results = run.metric_results_json or {}
        if metric_results:
            for key, value in metric_results.items():
                lines.append(f"- {key}: {value}")
        else:
            lines.append("- No metric results recorded yet.")

        lines.extend(["", "## Artifacts", ""])
        artifact_links = run.artifact_links_json or []
        if artifact_links:
            for artifact in artifact_links:
                label = (
                    artifact.get("label")
                    or artifact.get("path")
                    or artifact.get("url")
                    or "artifact"
                )
                target = artifact.get("url") or artifact.get("path") or ""
                lines.append(f"- {label}: {target}")
        else:
            lines.append("- No artifact links recorded.")

        lines.extend(
            [
                "",
                "## Conclusion",
                "",
                run.conclusion or "No conclusion recorded yet.",
                "",
                "## Notes",
                "",
                run.notes or "No notes recorded.",
            ]
        )
        return "\n".join(lines).strip() + "\n"

    def _load_task(self, task_id: str | None, idea_id: str) -> ResearchTask | None:
        if not task_id:
            return None
        task = self.session.get(ResearchTask, task_id)
        if task is None:
            raise ValueError("Research task not found")
        if task.idea_id and task.idea_id != idea_id:
            raise ValueError("Research task belongs to a different idea")
        return task

    def _mark_idea_status(self, idea_id: str, run_status: str) -> None:
        idea = self.session.get(Idea, idea_id)
        if idea is None:
            return
        if run_status == "running":
            idea.status = "experiment_running"
        elif run_status in FINAL_STATUSES:
            idea.status = "experiment_evaluated"

    def _task_event(
        self,
        task: ResearchTask,
        *,
        event_type: str,
        note: str,
        run: ExperimentRun,
        created_by: str,
    ) -> ResearchTaskEvent:
        return ResearchTaskEvent(
            task_id=task.id,
            idea_id=task.idea_id,
            event_type=event_type,
            status_from=task.status,
            status_to=task.status,
            priority_from=task.priority,
            priority_to=task.priority,
            note=note,
            metadata_json={
                "experiment_run_id": run.id,
                "experiment_plan_id": run.experiment_plan_id,
                "experiment_run_status": run.status,
            },
            created_by=created_by or "system",
        )

    def _default_title(self, plan: ExperimentPlan) -> str:
        objective = " ".join((plan.objective or "").split())
        if not objective:
            return "Experiment run"
        return objective[:96]

    def _default_dataset_snapshot(self, plan: ExperimentPlan) -> str:
        datasets = plan.datasets_json or []
        if not datasets:
            return "Dataset not specified in the experiment plan."
        return ", ".join(str(dataset) for dataset in datasets)
