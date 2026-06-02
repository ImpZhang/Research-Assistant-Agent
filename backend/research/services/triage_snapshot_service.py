from collections import Counter

from sqlalchemy.orm import Session

from backend.research.models import ProjectTriageSnapshot, ResearchTask
from backend.research.schemas import ProjectTriageBriefResponse


ACTIVE_TASK_STATUSES = ("todo", "doing", "blocked")
TRIAGE_OWNER_TYPES = (
    "project_triage",
    "idea_quality_gate",
    "opportunity_radar",
    "idea_readiness",
)


class ProjectTriageSnapshotService:
    def __init__(self, session: Session):
        self.session = session

    def create_snapshot(
        self,
        *,
        triage: ProjectTriageBriefResponse,
        title: str = "Project Triage Snapshot",
        idea_limit: int = 50,
        opportunity_limit: int = 8,
        created_by: str = "researcher",
    ) -> ProjectTriageSnapshot:
        tasks = self._load_source_tasks()
        summary = self._build_summary(triage, tasks)
        source_ids = self._build_source_ids(
            tasks,
            idea_limit=idea_limit,
            opportunity_limit=opportunity_limit,
        )
        snapshot = ProjectTriageSnapshot(
            title=title or "Project Triage Snapshot",
            summary_json=summary,
            recommended_focus_json=triage.recommended_focus,
            risk_focus_json=triage.risk_focus,
            next_actions_json=triage.next_actions,
            source_ids_json=source_ids,
            created_by=created_by or "researcher",
        )
        self.session.add(snapshot)
        self.session.flush()
        snapshot.markdown_export = render_project_triage_snapshot_markdown(snapshot)
        self.session.commit()
        self.session.refresh(snapshot)
        return snapshot

    def list_snapshots(self, limit: int = 50) -> list[ProjectTriageSnapshot]:
        limit = max(1, min(limit, 200))
        return (
            self.session.query(ProjectTriageSnapshot)
            .order_by(ProjectTriageSnapshot.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_snapshot(self, snapshot_id: str) -> ProjectTriageSnapshot | None:
        return self.session.get(ProjectTriageSnapshot, snapshot_id)

    def compare_snapshots(
        self,
        baseline_snapshot_id: str,
        candidate_snapshot_id: str,
    ) -> dict:
        baseline = self.get_snapshot(baseline_snapshot_id)
        candidate = self.get_snapshot(candidate_snapshot_id)
        if baseline is None:
            raise ValueError("Baseline project triage snapshot not found")
        if candidate is None:
            raise ValueError("Candidate project triage snapshot not found")

        comparison = {
            "baseline_snapshot_id": baseline.id,
            "candidate_snapshot_id": candidate.id,
            "baseline_title": baseline.title,
            "candidate_title": candidate.title,
            "metric_delta": _metric_delta(
                baseline.summary_json or {}, candidate.summary_json or {}
            ),
            **_list_delta(
                "focus", baseline.recommended_focus_json, candidate.recommended_focus_json
            ),
            **_list_delta("risks", baseline.risk_focus_json, candidate.risk_focus_json),
            **_list_delta("next_actions", baseline.next_actions_json, candidate.next_actions_json),
        }
        comparison["summary"] = (
            "Compared project triage snapshots: "
            f"{len(comparison['added_focus'])} focus items added, "
            f"{len(comparison['added_risks'])} risks added, "
            f"{len(comparison['added_next_actions'])} next actions added."
        )
        comparison["markdown_export"] = render_project_triage_snapshot_comparison_markdown(
            comparison
        )
        return comparison

    def _load_source_tasks(self) -> list[ResearchTask]:
        return (
            self.session.query(ResearchTask)
            .filter(ResearchTask.status.in_(ACTIVE_TASK_STATUSES))
            .order_by(ResearchTask.created_at.desc())
            .limit(120)
            .all()
        )

    def _build_summary(
        self,
        triage: ProjectTriageBriefResponse,
        tasks: list[ResearchTask],
    ) -> dict:
        by_status = Counter(task.status for task in tasks)
        by_owner_type = Counter(task.owner_type for task in tasks)
        return {
            "source_brief_generated_at": triage.generated_at.isoformat(),
            "idea_count": triage.idea_count,
            "open_task_count": triage.open_task_count,
            "blocked_task_count": triage.blocked_task_count,
            "average_readiness": triage.average_readiness,
            "average_quality_gate_score": triage.average_quality_gate_score,
            "opportunity_count": triage.opportunity_count,
            "recommended_focus_count": len(triage.recommended_focus),
            "risk_focus_count": len(triage.risk_focus),
            "next_action_count": len(triage.next_actions),
            "tracked_task_count": len(tasks),
            "tracked_task_counts_by_status": dict(by_status),
            "tracked_task_counts_by_owner_type": dict(by_owner_type),
        }

    def _build_source_ids(
        self,
        tasks: list[ResearchTask],
        *,
        idea_limit: int,
        opportunity_limit: int,
    ) -> dict:
        source_ids: dict[str, object] = {
            "source": "project_triage_brief",
            "idea_limit": idea_limit,
            "opportunity_limit": opportunity_limit,
            "tracked_task_ids": [task.id for task in tasks],
            "blocked_task_ids": [task.id for task in tasks if task.status == "blocked"],
        }
        for owner_type in TRIAGE_OWNER_TYPES:
            source_ids[f"{owner_type}_task_ids"] = [
                task.id for task in tasks if task.owner_type == owner_type
            ]
        return source_ids


def render_project_triage_snapshot_markdown(snapshot: ProjectTriageSnapshot) -> str:
    summary = snapshot.summary_json or {}
    source_ids = snapshot.source_ids_json or {}
    lines = [
        f"# Project Triage Snapshot: {_clean(snapshot.title)}",
        "",
        f"- Snapshot ID: `{snapshot.id}`",
        f"- Created By: {_clean(snapshot.created_by)}",
        f"- Source Brief Generated At: `{summary.get('source_brief_generated_at', '')}`",
        f"- Idea Count: {summary.get('idea_count', 0)}",
        f"- Open Tasks: {summary.get('open_task_count', 0)}",
        f"- Blocked Tasks: {summary.get('blocked_task_count', 0)}",
        f"- Average Readiness: {summary.get('average_readiness', 0.0)}",
        f"- Average Quality Gate Score: {summary.get('average_quality_gate_score', 0.0)}",
        f"- Opportunity Count: {summary.get('opportunity_count', 0)}",
        "",
        "## Recommended Focus",
        "",
    ]
    _append_items(lines, snapshot.recommended_focus_json or [], "No recommended focus recorded.")
    lines.extend(["", "## Risk Focus", ""])
    _append_items(lines, snapshot.risk_focus_json or [], "No risk focus recorded.")
    lines.extend(["", "## Next Actions", ""])
    _append_items(lines, snapshot.next_actions_json or [], "No next actions recorded.")

    lines.extend(["", "## Tracked Task Summary", ""])
    for status, count in (summary.get("tracked_task_counts_by_status") or {}).items():
        lines.append(f"- `{status}`: {count}")
    owner_counts = summary.get("tracked_task_counts_by_owner_type") or {}
    if owner_counts:
        lines.extend(["", "Owner types:"])
        for owner_type, count in owner_counts.items():
            lines.append(f"- `{owner_type}`: {count}")
    else:
        lines.append("- No tracked active tasks.")

    lines.extend(["", "## Source IDs", ""])
    for key, value in source_ids.items():
        lines.append(f"- {key}: {_inline_value(value)}")
    return "\n".join(lines).strip() + "\n"


def render_project_triage_snapshot_comparison_markdown(comparison: dict) -> str:
    lines = [
        "# Project Triage Snapshot Comparison",
        "",
        f"- Baseline: `{comparison['baseline_snapshot_id']}` {_clean(comparison['baseline_title'])}",
        f"- Candidate: `{comparison['candidate_snapshot_id']}` {_clean(comparison['candidate_title'])}",
        f"- Summary: {_clean(comparison['summary'])}",
        "",
        "## Metric Delta",
        "",
    ]
    for key, value in (comparison.get("metric_delta") or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Recommended Focus Changes", ""])
    _append_change_group(lines, "Added", comparison.get("added_focus") or [])
    _append_change_group(lines, "Removed", comparison.get("removed_focus") or [])
    _append_change_group(lines, "Kept", comparison.get("kept_focus") or [])
    lines.extend(["", "## Risk Focus Changes", ""])
    _append_change_group(lines, "Added", comparison.get("added_risks") or [])
    _append_change_group(lines, "Removed", comparison.get("removed_risks") or [])
    _append_change_group(lines, "Kept", comparison.get("kept_risks") or [])
    lines.extend(["", "## Next Action Changes", ""])
    _append_change_group(lines, "Added", comparison.get("added_next_actions") or [])
    _append_change_group(lines, "Removed", comparison.get("removed_next_actions") or [])
    _append_change_group(lines, "Kept", comparison.get("kept_next_actions") or [])
    return "\n".join(lines).strip() + "\n"


def _append_items(lines: list[str], items: list[str], empty: str) -> None:
    if not items:
        lines.append(f"- {empty}")
        return
    lines.extend(f"- {_clean(item)}" for item in items)


def _append_change_group(lines: list[str], label: str, items: list[str]) -> None:
    lines.append(f"### {label}")
    if not items:
        lines.append("- none")
        return
    lines.extend(f"- {_clean(item)}" for item in items)


def _metric_delta(baseline: dict, candidate: dict) -> dict:
    keys = [
        "idea_count",
        "open_task_count",
        "blocked_task_count",
        "average_readiness",
        "average_quality_gate_score",
        "opportunity_count",
        "tracked_task_count",
        "next_action_count",
        "risk_focus_count",
    ]
    delta = {}
    for key in keys:
        delta[key] = round(float(candidate.get(key, 0)) - float(baseline.get(key, 0)), 4)
    return delta


def _list_delta(prefix: str, baseline: list[str] | None, candidate: list[str] | None) -> dict:
    baseline_items = _unique_by_normalized_text(baseline or [])
    candidate_items = _unique_by_normalized_text(candidate or [])
    baseline_keys = {_normalize(item) for item in baseline_items}
    candidate_keys = {_normalize(item) for item in candidate_items}
    return {
        f"added_{prefix}": [
            item for item in candidate_items if _normalize(item) not in baseline_keys
        ],
        f"removed_{prefix}": [
            item for item in baseline_items if _normalize(item) not in candidate_keys
        ],
        f"kept_{prefix}": [item for item in candidate_items if _normalize(item) in baseline_keys],
    }


def _unique_by_normalized_text(items: list[str]) -> list[str]:
    unique = []
    seen = set()
    for item in items:
        key = _normalize(item)
        if not key or key in seen:
            continue
        unique.append(_clean(item))
        seen.add(key)
    return unique


def _normalize(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _inline_value(value: object) -> str:
    if isinstance(value, list):
        if not value:
            return "`none`"
        return ", ".join(f"`{item}`" for item in value[:40])
    if isinstance(value, dict):
        return str(value)
    return f"`{value}`"


def _clean(value: object) -> str:
    return str(value or "").replace("\n", " ").strip()
