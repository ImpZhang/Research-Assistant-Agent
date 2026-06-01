from sqlalchemy.orm import Session

from backend.research.models import ResearchPlanSnapshot, ResearchProfile, ResearchTask
from backend.research.services.idea_ranking_service import IdeaRankingService, RankedIdea


class ResearchPlanService:
    def __init__(self, session: Session):
        self.session = session

    def create_plan(
        self,
        *,
        title: str = "Research Execution Plan",
        horizon_days: int = 14,
        idea_ids: list[str] | None = None,
        created_by: str = "researcher",
    ) -> ResearchPlanSnapshot:
        horizon_days = max(7, min(horizon_days, 120))
        ranked = IdeaRankingService(self.session).rank_ideas(
            idea_ids=idea_ids or None,
            limit=5,
            deduplicate_lineage=True,
        )
        selected_idea_ids = [item.idea.id for item in ranked]
        tasks = self._load_tasks(selected_idea_ids)
        profile = self.session.get(ResearchProfile, "default")
        profile_summary = self._profile_summary(profile)
        plan_items = self._build_plan_items(ranked, tasks, horizon_days, profile_summary)
        source_ids = {
            "profile_id": profile.id if profile else "default",
            "idea_ids": selected_idea_ids,
            "task_ids": [task.id for task in tasks],
        }
        snapshot = ResearchPlanSnapshot(
            title=title or "Research Execution Plan",
            horizon_days=horizon_days,
            idea_ids_json=selected_idea_ids,
            profile_summary_json=profile_summary,
            plan_items_json=plan_items,
            source_ids_json=source_ids,
            created_by=created_by or "researcher",
        )
        self.session.add(snapshot)
        self.session.flush()
        snapshot.markdown_export = render_research_plan_markdown(snapshot)
        self.session.commit()
        self.session.refresh(snapshot)
        return snapshot

    def list_plans(self, limit: int = 50) -> list[ResearchPlanSnapshot]:
        limit = max(1, min(limit, 200))
        return (
            self.session.query(ResearchPlanSnapshot)
            .order_by(ResearchPlanSnapshot.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_plan(self, plan_id: str) -> ResearchPlanSnapshot | None:
        return self.session.get(ResearchPlanSnapshot, plan_id)

    def _load_tasks(self, idea_ids: list[str]) -> list[ResearchTask]:
        query = (
            self.session.query(ResearchTask)
            .filter(ResearchTask.status.in_(["todo", "doing", "blocked"]))
            .order_by(ResearchTask.created_at.desc())
        )
        if idea_ids:
            query = query.filter(ResearchTask.idea_id.in_(idea_ids))
        return sorted(query.limit(80).all(), key=_task_order)[:24]

    def _profile_summary(self, profile: ResearchProfile | None) -> dict:
        if profile is None:
            return {
                "name": "Default Research Profile",
                "risk_tolerance": "medium",
                "domains": [],
                "target_venues": [],
                "resource_constraints": [],
            }
        return {
            "name": profile.name,
            "risk_tolerance": profile.risk_tolerance,
            "domains": profile.primary_domains_json or [],
            "target_venues": profile.target_venues_json or [],
            "resource_constraints": profile.resource_constraints_json or [],
            "active_questions": profile.active_questions_json or [],
        }

    def _build_plan_items(
        self,
        ranked: list[RankedIdea],
        tasks: list[ResearchTask],
        horizon_days: int,
        profile_summary: dict,
    ) -> list[dict]:
        items = []
        top = ranked[0] if ranked else None
        blockers = [task for task in tasks if task.status == "blocked"][:4]
        active_tasks = [task for task in tasks if task.status in {"todo", "doing"}][:8]

        items.append(
            {
                "phase": "triage",
                "days": f"1-{min(3, horizon_days)}",
                "title": "Stabilize the next research decision",
                "idea_id": top.idea.id if top else "",
                "task_ids": [task.id for task in blockers[:3]],
                "actions": _task_actions(blockers)
                or [
                    "Review the latest readiness overview and select the highest-leverage idea.",
                    "Confirm whether the current profile constraints still match the project.",
                ],
                "success_check": "No critical blocker is left without an owner or next evidence action.",
                "rationale": _top_rationale(top, profile_summary),
            }
        )

        items.append(
            {
                "phase": "execution",
                "days": f"{min(4, horizon_days)}-{min(7, horizon_days)}",
                "title": "Run the smallest publishability experiment",
                "idea_id": top.idea.id if top else "",
                "task_ids": [task.id for task in active_tasks[:4]],
                "actions": _task_actions(active_tasks[:4])
                or [
                    "Create or update an experiment plan for the top ranked idea.",
                    "Record a first run with metrics, artifacts, and conclusion.",
                ],
                "success_check": "At least one experiment run or decision memo is recorded.",
                "rationale": "Focus effort on evidence that can change the go/no-go decision.",
            }
        )

        if horizon_days > 7:
            items.append(
                {
                    "phase": "synthesis",
                    "days": f"8-{horizon_days}",
                    "title": "Package evidence for advisor review",
                    "idea_id": top.idea.id if top else "",
                    "task_ids": [task.id for task in active_tasks[4:8]],
                    "actions": _task_actions(active_tasks[4:8])
                    or [
                        "Export an idea bundle for the top ranked idea.",
                        "Create an advisor brief and update the portfolio snapshot.",
                    ],
                    "success_check": "Advisor-ready brief, bundle, or portfolio snapshot exists.",
                    "rationale": "Turn execution evidence into a durable research artifact.",
                }
            )

        for item in ranked[1:3]:
            items.append(
                {
                    "phase": "parallel_track",
                    "days": f"1-{horizon_days}",
                    "title": f"Keep backup track warm: {item.idea.title}",
                    "idea_id": item.idea.id,
                    "task_ids": [],
                    "actions": [
                        "Run a quick novelty or related-work check before committing more effort.",
                        "Create a decision memo if this track should be parked or pursued.",
                    ],
                    "success_check": "Backup idea has a clear pursue/revise/park decision.",
                    "rationale": "; ".join(item.rationale[:2]),
                }
            )
        return items


def render_research_plan_markdown(snapshot: ResearchPlanSnapshot) -> str:
    profile = snapshot.profile_summary_json or {}
    lines = [
        f"# {snapshot.title}",
        "",
        f"- Plan ID: `{snapshot.id}`",
        f"- Horizon Days: {snapshot.horizon_days}",
        f"- Created By: {snapshot.created_by}",
        f"- Profile: {profile.get('name', 'Default Research Profile')}",
        f"- Risk Tolerance: {profile.get('risk_tolerance', 'medium')}",
        "",
        "## Profile Constraints",
        "",
    ]
    constraints = profile.get("resource_constraints") or []
    if constraints:
        lines.extend(f"- {item}" for item in constraints)
    else:
        lines.append("- No resource constraints recorded.")

    lines.extend(["", "## Plan Items", ""])
    for item in snapshot.plan_items_json or []:
        lines.extend(
            [
                f"### {item['days']} - {item['title']}",
                "",
                f"- Phase: `{item['phase']}`",
                f"- Idea ID: `{item.get('idea_id') or 'none'}`",
                f"- Task IDs: {_inline_ids(item.get('task_ids') or [])}",
                f"- Success Check: {item['success_check']}",
                f"- Rationale: {item.get('rationale') or 'Not specified.'}",
                "",
                "Actions:",
            ]
        )
        lines.extend(f"- {action}" for action in item.get("actions") or [])
        lines.append("")

    lines.extend(["## Source IDs", ""])
    for key, value in (snapshot.source_ids_json or {}).items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines).strip() + "\n"


def _task_order(task: ResearchTask) -> tuple[int, int, str]:
    priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    status_rank = {"blocked": 0, "doing": 1, "todo": 2, "done": 3, "archived": 4}
    return (
        priority_rank.get(task.priority, 9),
        status_rank.get(task.status, 9),
        task.created_at.isoformat(),
    )


def _task_actions(tasks: list[ResearchTask]) -> list[str]:
    return [f"{task.title} ({task.priority}/{task.status})" for task in tasks]


def _top_rationale(top: RankedIdea | None, profile_summary: dict) -> str:
    if top is None:
        return "No ranked idea exists yet; start from profile and project overview."
    parts = [f"Top ranked idea score is {top.weighted_score}."]
    if profile_summary.get("domains"):
        parts.append("Profile domains: " + ", ".join(profile_summary["domains"][:3]) + ".")
    if top.rationale:
        parts.append(top.rationale[0])
    return " ".join(parts)


def _inline_ids(ids: list[str]) -> str:
    if not ids:
        return "`none`"
    return ", ".join(f"`{item}`" for item in ids)
