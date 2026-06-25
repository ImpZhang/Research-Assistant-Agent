from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from backend.research.models import ExperimentRun, Idea, ResearchBrief


BENCHMARK_EXECUTION_KINDS = {"benchmark", "benchmark_command"}


class BenchmarkEvidenceService:
    def __init__(self, session: Session):
        self.session = session

    def readiness_for_idea(self, idea_id: str) -> dict[str, Any]:
        idea = self.session.get(Idea, idea_id)
        if idea is None:
            raise ValueError("Idea not found")
        runs = self._benchmark_runs(idea_id)
        completed_runs = [run for run in runs if run.status == "completed"]
        comparisons = self._benchmark_comparisons(idea_id)
        latest_run = runs[0] if runs else None
        latest_completed_run = completed_runs[0] if completed_runs else None
        latest_comparison = comparisons[0] if comparisons else None
        latest_comparison_status = (
            (latest_comparison.summary_json or {}).get("comparison_status", "")
            if latest_comparison
            else ""
        )
        missing_items = []
        warnings = []
        if not completed_runs:
            missing_items.append("No completed benchmark run is recorded for this idea.")
        if not comparisons:
            missing_items.append("No benchmark run comparison brief is recorded for this idea.")
        if latest_completed_run and not (latest_completed_run.artifact_links_json or []):
            warnings.append("Latest completed benchmark run has no artifact links.")
        if latest_comparison_status == "regressed":
            warnings.append("Latest benchmark comparison is regressed.")
        if latest_comparison_status == "incomplete":
            warnings.append("Latest benchmark comparison is incomplete.")

        ready_for_sota_review = bool(completed_runs and comparisons)
        readiness_status = (
            "ready_for_sota_review" if ready_for_sota_review else "needs_benchmark_evidence"
        )
        recommended_actions = _recommended_actions(missing_items, warnings)
        markdown_export = render_benchmark_evidence_readiness_markdown(
            idea=idea,
            readiness_status=readiness_status,
            ready_for_sota_review=ready_for_sota_review,
            runs=runs,
            comparisons=comparisons,
            missing_items=missing_items,
            warnings=warnings,
            recommended_actions=recommended_actions,
        )
        return {
            "idea_id": idea.id,
            "readiness_status": readiness_status,
            "ready_for_sota_review": ready_for_sota_review,
            "benchmark_run_count": len(runs),
            "completed_benchmark_run_count": len(completed_runs),
            "benchmark_comparison_count": len(comparisons),
            "latest_run_id": latest_run.id if latest_run else "",
            "latest_completed_run_id": latest_completed_run.id if latest_completed_run else "",
            "latest_comparison_brief_id": latest_comparison.id if latest_comparison else "",
            "latest_comparison_status": latest_comparison_status,
            "missing_items": missing_items,
            "warnings": warnings,
            "recommended_actions": recommended_actions,
            "markdown_export": markdown_export,
        }

    def _benchmark_runs(self, idea_id: str) -> list[ExperimentRun]:
        runs = (
            self.session.query(ExperimentRun)
            .filter(ExperimentRun.idea_id == idea_id)
            .order_by(ExperimentRun.created_at.desc())
            .limit(100)
            .all()
        )
        return [
            run
            for run in runs
            if (run.parameters_json or {}).get("execution_kind") in BENCHMARK_EXECUTION_KINDS
        ]

    def _benchmark_comparisons(self, idea_id: str) -> list[ResearchBrief]:
        records = (
            self.session.query(ResearchBrief)
            .filter(ResearchBrief.scope == "benchmark_run_comparison")
            .order_by(ResearchBrief.created_at.desc())
            .limit(200)
            .all()
        )
        return [record for record in records if idea_id in (record.idea_ids_json or [])]


def render_benchmark_evidence_readiness_markdown(
    *,
    idea: Idea,
    readiness_status: str,
    ready_for_sota_review: bool,
    runs: list[ExperimentRun],
    comparisons: list[ResearchBrief],
    missing_items: list[str],
    warnings: list[str],
    recommended_actions: list[str],
) -> str:
    lines = [
        f"# Benchmark Evidence Readiness: {idea.title}",
        "",
        f"- Idea ID: `{idea.id}`",
        f"- Status: {readiness_status}",
        f"- Ready for SOTA Review: {ready_for_sota_review}",
        f"- Benchmark Runs: {len(runs)}",
        f"- Benchmark Comparisons: {len(comparisons)}",
        "",
        "## Missing Items",
        "",
    ]
    lines.extend(_markdown_bullets(missing_items))
    lines.extend(["", "## Warnings", ""])
    lines.extend(_markdown_bullets(warnings))
    lines.extend(["", "## Recommended Actions", ""])
    lines.extend(_markdown_bullets(recommended_actions))
    lines.extend(["", "## Latest Benchmark Runs", ""])
    if runs:
        for run in runs[:5]:
            metric_keys = ", ".join(sorted((run.metric_results_json or {}).keys())) or "no metrics"
            lines.append(f"- `{run.id}` {run.title}: {run.status}, metrics={metric_keys}")
    else:
        lines.append("- No benchmark runs recorded.")
    lines.extend(["", "## Latest Comparison Briefs", ""])
    if comparisons:
        for brief in comparisons[:5]:
            status = (brief.summary_json or {}).get("comparison_status", "unknown")
            primary = (brief.summary_json or {}).get("primary_metric", "metric")
            lines.append(f"- `{brief.id}` {brief.title}: {status}, primary={primary}")
    else:
        lines.append("- No benchmark comparison briefs recorded.")
    return "\n".join(lines).strip() + "\n"


def _recommended_actions(missing_items: list[str], warnings: list[str]) -> list[str]:
    actions = []
    if any("benchmark run" in item for item in missing_items):
        actions.append("Run or record at least one completed benchmark for the idea.")
    if any("comparison" in item for item in missing_items):
        actions.append("Compare the latest candidate benchmark run against a baseline run.")
    if any("artifact links" in item for item in warnings):
        actions.append("Attach stdout, metrics, plots, or result files to the benchmark run.")
    if any("regressed" in item for item in warnings):
        actions.append("Investigate the regression before claiming improvement.")
    if any("incomplete" in item for item in warnings):
        actions.append("Re-run the benchmark or fix missing metric values before signoff.")
    if not actions:
        actions.append(
            "Proceed to manual SOTA signoff with benchmark and comparison evidence linked."
        )
    return actions


def _markdown_bullets(items: list[str]) -> list[str]:
    if not items:
        return ["- None."]
    return [f"- {item}" for item in items]
