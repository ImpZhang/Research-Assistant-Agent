from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.research.models import ExperimentRun, ResearchBrief


class BenchmarkRunComparisonService:
    def __init__(self, session: Session):
        self.session = session

    def compare_runs(
        self,
        *,
        baseline_run_id: str,
        candidate_run_id: str,
        primary_metric: str = "",
        created_by: str = "system",
    ) -> dict[str, Any]:
        if baseline_run_id == candidate_run_id:
            raise ValueError("Baseline and candidate benchmark runs must be different.")
        baseline = self.session.get(ExperimentRun, baseline_run_id)
        candidate = self.session.get(ExperimentRun, candidate_run_id)
        if baseline is None:
            raise ValueError("Baseline experiment run not found")
        if candidate is None:
            raise ValueError("Candidate experiment run not found")
        if baseline.idea_id != candidate.idea_id:
            raise ValueError("Benchmark runs must belong to the same idea.")

        metric_name = _primary_metric(primary_metric, baseline, candidate)
        metric_deltas = _metric_deltas(baseline, candidate, metric_name)
        primary_delta = next(
            (item for item in metric_deltas if item["metric"] == metric_name),
            metric_deltas[0] if metric_deltas else {},
        )
        status = _comparison_status(primary_delta)
        summary = {
            "comparison_status": status,
            "primary_metric": metric_name,
            "baseline_run_id": baseline.id,
            "candidate_run_id": candidate.id,
            "baseline_title": baseline.title,
            "candidate_title": candidate.title,
            "baseline_status": baseline.status,
            "candidate_status": candidate.status,
            "baseline_execution_kind": (baseline.parameters_json or {}).get("execution_kind", ""),
            "candidate_execution_kind": (candidate.parameters_json or {}).get("execution_kind", ""),
            "baseline_value": primary_delta.get("baseline_value"),
            "candidate_value": primary_delta.get("candidate_value"),
            "delta": primary_delta.get("delta"),
            "improved": primary_delta.get("improved"),
            "metric_direction": primary_delta.get("direction", "higher_is_better"),
            "metric_deltas": metric_deltas,
            "compared_at": datetime.now(UTC).isoformat(),
        }
        brief = ResearchBrief(
            title=f"Benchmark comparison - {candidate.title}",
            scope="benchmark_run_comparison",
            idea_ids_json=[candidate.idea_id],
            summary_json=summary,
            created_by=created_by or "system",
        )
        self.session.add(brief)
        self.session.flush()
        brief.markdown_export = render_benchmark_comparison_markdown(
            brief_id=brief.id,
            baseline=baseline,
            candidate=candidate,
            summary=summary,
        )
        self.session.commit()
        self.session.refresh(brief)
        return {
            "brief_id": brief.id,
            "baseline_run_id": baseline.id,
            "candidate_run_id": candidate.id,
            "idea_id": candidate.idea_id,
            "experiment_plan_ids": sorted(
                {baseline.experiment_plan_id, candidate.experiment_plan_id}
            ),
            "primary_metric": metric_name,
            "status": status,
            "summary": summary,
            "metric_deltas": metric_deltas,
            "markdown_export": brief.markdown_export,
            "created_by": brief.created_by,
            "created_at": brief.created_at,
        }


def render_benchmark_comparison_markdown(
    *,
    brief_id: str,
    baseline: ExperimentRun,
    candidate: ExperimentRun,
    summary: dict[str, Any],
) -> str:
    lines = [
        f"# Benchmark Comparison: {candidate.title}",
        "",
        f"- Brief ID: `{brief_id}`",
        f"- Baseline Run ID: `{baseline.id}`",
        f"- Candidate Run ID: `{candidate.id}`",
        f"- Idea ID: `{candidate.idea_id}`",
        f"- Status: {summary['comparison_status']}",
        f"- Primary Metric: {summary['primary_metric']}",
        "",
        "## Primary Result",
        "",
        f"- Baseline value: {summary.get('baseline_value')}",
        f"- Candidate value: {summary.get('candidate_value')}",
        f"- Delta: {summary.get('delta')}",
        f"- Improved: {summary.get('improved')}",
        f"- Direction: {summary.get('metric_direction')}",
        "",
        "## Metric Deltas",
        "",
    ]
    for item in summary.get("metric_deltas", []):
        lines.append(
            "- "
            f"{item['metric']}: baseline={item.get('baseline_value')}, "
            f"candidate={item.get('candidate_value')}, delta={item.get('delta')}, "
            f"improved={item.get('improved')}"
        )
    if not summary.get("metric_deltas"):
        lines.append("- No comparable metrics were found.")
    lines.extend(
        [
            "",
            "## Baseline",
            "",
            baseline.markdown_export or baseline.conclusion or "No baseline markdown recorded.",
            "",
            "## Candidate",
            "",
            candidate.markdown_export or candidate.conclusion or "No candidate markdown recorded.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _primary_metric(
    requested_metric: str,
    baseline: ExperimentRun,
    candidate: ExperimentRun,
) -> str:
    if requested_metric.strip():
        return requested_metric.strip()
    for run in (candidate, baseline):
        primary = (run.parameters_json or {}).get("primary_metric", "")
        if str(primary).strip():
            return str(primary).strip()
    baseline_metrics = set((baseline.metric_results_json or {}).keys())
    candidate_metrics = set((candidate.metric_results_json or {}).keys())
    shared = sorted(baseline_metrics.intersection(candidate_metrics))
    return shared[0] if shared else "primary_metric"


def _metric_deltas(
    baseline: ExperimentRun,
    candidate: ExperimentRun,
    primary_metric: str,
) -> list[dict[str, Any]]:
    baseline_metrics = baseline.metric_results_json or {}
    candidate_metrics = candidate.metric_results_json or {}
    names = sorted(set(baseline_metrics).union(candidate_metrics))
    if primary_metric not in names:
        names.insert(0, primary_metric)
    deltas = []
    for name in names:
        baseline_metric = baseline_metrics.get(name)
        candidate_metric = candidate_metrics.get(name)
        baseline_value = _metric_value(baseline_metric)
        candidate_value = _metric_value(candidate_metric)
        direction = _metric_direction(candidate_metric, baseline_metric, candidate)
        delta = (
            round(candidate_value - baseline_value, 6)
            if baseline_value is not None and candidate_value is not None
            else None
        )
        improved = None
        if delta is not None:
            improved = delta > 0 if direction == "higher_is_better" else delta < 0
        deltas.append(
            {
                "metric": name,
                "baseline_value": baseline_value,
                "candidate_value": candidate_value,
                "delta": delta,
                "direction": direction,
                "improved": improved,
            }
        )
    return deltas


def _metric_value(metric: Any) -> float | None:
    if isinstance(metric, dict):
        for key in ("value", "candidate", "score"):
            value = metric.get(key)
            if isinstance(value, int | float):
                return float(value)
        return None
    if isinstance(metric, int | float):
        return float(metric)
    return None


def _metric_direction(
    candidate_metric: Any,
    baseline_metric: Any,
    candidate: ExperimentRun,
) -> str:
    for metric in (candidate_metric, baseline_metric):
        if isinstance(metric, dict) and metric.get("direction") in {
            "higher_is_better",
            "lower_is_better",
        }:
            return metric["direction"]
    direction = (candidate.parameters_json or {}).get("metric_direction")
    if direction in {"higher_is_better", "lower_is_better"}:
        return direction
    return "higher_is_better"


def _comparison_status(primary_delta: dict[str, Any]) -> str:
    if not primary_delta or primary_delta.get("delta") is None:
        return "incomplete"
    delta = primary_delta["delta"]
    if delta == 0:
        return "no_change"
    if primary_delta.get("improved") is True:
        return "improved"
    if primary_delta.get("improved") is False:
        return "regressed"
    return "incomplete"
