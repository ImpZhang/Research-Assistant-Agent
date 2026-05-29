from numbers import Number

from sqlalchemy.orm import Session

from backend.research.models import (
    ExperimentAnalysis,
    ExperimentRun,
    Idea,
    ResearchTask,
    ResearchTaskEvent,
)
from backend.research.services.artifact_graph_service import ArtifactGraphService
from backend.research.services.graph_service import GraphService


class ExperimentAnalysisService:
    def __init__(self, session: Session):
        self.session = session

    def create_analysis(
        self,
        experiment_run_id: str,
        *,
        created_by: str = "system",
    ) -> ExperimentAnalysis:
        run = self.session.get(ExperimentRun, experiment_run_id)
        if run is None:
            raise ValueError("Experiment run not found")
        metric_interpretation = self._interpret_metrics(run.metric_results_json or {})
        concerns = self._concerns(run, metric_interpretation)
        decision, confidence = self._decision(run, metric_interpretation, concerns)
        analysis = ExperimentAnalysis(
            experiment_run_id=run.id,
            experiment_plan_id=run.experiment_plan_id,
            idea_id=run.idea_id,
            task_id=run.task_id,
            decision=decision,
            confidence=confidence,
            metric_interpretation_json=metric_interpretation,
            key_findings_json=self._key_findings(run, metric_interpretation),
            concerns_json=concerns,
            next_actions_json=self._next_actions(decision),
            created_by=created_by or "system",
        )
        self.session.add(analysis)
        self.session.flush()
        analysis.markdown_export = self.render_markdown(analysis)
        self._mark_idea_status(analysis.idea_id, decision)
        task = self.session.get(ResearchTask, run.task_id) if run.task_id else None
        if task is not None:
            self.session.add(
                ResearchTaskEvent(
                    task_id=task.id,
                    idea_id=task.idea_id,
                    event_type="experiment_analysis_created",
                    status_from=task.status,
                    status_to=task.status,
                    priority_from=task.priority,
                    priority_to=task.priority,
                    note=f"Experiment analysis decision: {decision}.",
                    metadata_json={
                        "experiment_analysis_id": analysis.id,
                        "experiment_run_id": run.id,
                        "confidence": confidence,
                    },
                    created_by=created_by or "system",
                )
            )
        self.session.commit()
        self.session.refresh(analysis)
        ArtifactGraphService(GraphService(self.session)).link_experiment_analysis(
            run,
            analysis,
            task,
        )
        self.session.commit()
        return analysis

    def list_for_run(self, experiment_run_id: str, limit: int = 50) -> list[ExperimentAnalysis]:
        if self.session.get(ExperimentRun, experiment_run_id) is None:
            raise ValueError("Experiment run not found")
        limit = max(1, min(limit, 200))
        return (
            self.session.query(ExperimentAnalysis)
            .filter(ExperimentAnalysis.experiment_run_id == experiment_run_id)
            .order_by(ExperimentAnalysis.created_at.desc())
            .limit(limit)
            .all()
        )

    def list_for_idea(self, idea_id: str, limit: int = 50) -> list[ExperimentAnalysis]:
        if self.session.get(Idea, idea_id) is None:
            raise ValueError("Idea not found")
        limit = max(1, min(limit, 200))
        return (
            self.session.query(ExperimentAnalysis)
            .filter(ExperimentAnalysis.idea_id == idea_id)
            .order_by(ExperimentAnalysis.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_analysis(self, analysis_id: str) -> ExperimentAnalysis | None:
        return self.session.get(ExperimentAnalysis, analysis_id)

    def render_markdown(self, analysis: ExperimentAnalysis) -> str:
        lines = [
            f"# Experiment Analysis: {analysis.decision}",
            "",
            f"- Analysis ID: `{analysis.id}`",
            f"- Experiment Run ID: `{analysis.experiment_run_id}`",
            f"- Experiment Plan ID: `{analysis.experiment_plan_id}`",
            f"- Idea ID: `{analysis.idea_id}`",
            f"- Task ID: `{analysis.task_id}`" if analysis.task_id else "- Task ID: none",
            f"- Confidence: {analysis.confidence:.2f}",
            f"- Created By: {analysis.created_by}",
            "",
            "## Metric Interpretation",
            "",
        ]
        metric_interpretation = analysis.metric_interpretation_json or {}
        if metric_interpretation:
            for key, value in metric_interpretation.items():
                lines.append(f"- {key}: {value}")
        else:
            lines.append("- No metric interpretation recorded.")

        lines.extend(["", "## Key Findings", ""])
        lines.extend(self._list_lines(analysis.key_findings_json or []))
        lines.extend(["", "## Concerns", ""])
        lines.extend(self._list_lines(analysis.concerns_json or []))
        lines.extend(["", "## Next Actions", ""])
        lines.extend(self._list_lines(analysis.next_actions_json or []))
        return "\n".join(lines).strip() + "\n"

    def _interpret_metrics(self, metrics: dict) -> dict:
        keys = list(metrics.keys())
        numeric_values = self._numeric_values(metrics)
        return {
            "metric_count": len(keys),
            "numeric_metric_count": len(numeric_values),
            "reported_metrics": keys,
            "best_numeric_value": max(numeric_values) if numeric_values else None,
            "has_cost_signal": any("cost" in key.lower() for key in keys),
        }

    def _numeric_values(self, metrics: dict) -> list[float]:
        values: list[float] = []
        for value in metrics.values():
            candidate = value.get("value") if isinstance(value, dict) else value
            if isinstance(candidate, Number) and not isinstance(candidate, bool):
                values.append(float(candidate))
        return values

    def _concerns(self, run: ExperimentRun, metric_interpretation: dict) -> list[str]:
        concerns: list[str] = []
        if run.status != "completed":
            concerns.append(f"Run status is {run.status}; analysis should remain provisional.")
        if metric_interpretation.get("metric_count", 0) == 0:
            concerns.append("No metric results were recorded.")
        if not run.artifact_links_json:
            concerns.append("No artifact links were attached for reproducibility.")
        if not run.baseline_snapshot_json:
            concerns.append("No baseline snapshot was available for comparison.")
        if not run.conclusion:
            concerns.append("No run-level conclusion was recorded.")
        return concerns

    def _decision(
        self,
        run: ExperimentRun,
        metric_interpretation: dict,
        concerns: list[str],
    ) -> tuple[str, float]:
        metric_count = metric_interpretation.get("metric_count", 0)
        numeric_count = metric_interpretation.get("numeric_metric_count", 0)
        if run.status == "failed":
            return "revise_method", 0.35
        if run.status == "inconclusive":
            return "needs_more_evidence", 0.45
        if run.status == "completed" and metric_count and run.conclusion:
            penalty = min(len(concerns) * 0.08, 0.32)
            return "supports_hypothesis", round(max(0.55, 0.86 - penalty), 2)
        if metric_count or numeric_count:
            return "continue_experimentation", 0.58
        return "needs_more_evidence", 0.4

    def _key_findings(self, run: ExperimentRun, metric_interpretation: dict) -> list[str]:
        findings = [
            f"Run status is {run.status}.",
            f"Recorded {metric_interpretation.get('metric_count', 0)} metric result(s).",
        ]
        if metric_interpretation.get("numeric_metric_count", 0):
            findings.append(
                f"Numeric metric count: {metric_interpretation['numeric_metric_count']}."
            )
        if run.conclusion:
            findings.append(f"Run conclusion: {run.conclusion}")
        return findings

    def _next_actions(self, decision: str) -> list[str]:
        if decision == "supports_hypothesis":
            return [
                "Replicate the run with another seed or split.",
                "Run the planned ablations and robustness checks.",
                "Update the proposal evidence section with the run summary.",
            ]
        if decision == "revise_method":
            return [
                "Inspect logs and artifacts to isolate the failure mode.",
                "Compare the implementation against the baseline harness.",
                "Design a smaller diagnostic run before retrying the full experiment.",
            ]
        if decision == "continue_experimentation":
            return [
                "Add a stronger baseline comparison.",
                "Record missing artifact links and run-level conclusion.",
                "Repeat with the primary metric and cost metric together.",
            ]
        return [
            "Record primary metric results for the experiment run.",
            "Attach reproducibility artifacts such as logs, config, or result tables.",
            "Rerun with the baseline snapshot and success criterion made explicit.",
        ]

    def _mark_idea_status(self, idea_id: str, decision: str) -> None:
        idea = self.session.get(Idea, idea_id)
        if idea is None:
            return
        if decision == "supports_hypothesis":
            idea.status = "experiment_supported"
        elif decision in {"revise_method", "needs_more_evidence"}:
            idea.status = "experiment_needs_revision"
        else:
            idea.status = "experiment_evaluated"

    def _list_lines(self, items: list[str]) -> list[str]:
        if not items:
            return ["- None."]
        return [f"- {item}" for item in items]
