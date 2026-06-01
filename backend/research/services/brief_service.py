from collections import Counter

from sqlalchemy.orm import Session

from backend.research.models import (
    ExperimentAnalysis,
    Idea,
    IdeaDecisionMemo,
    ProposalReview,
    ResearchBrief,
    ResearchPlanSnapshot,
    ResearchProfile,
    ResearchTask,
)


class ResearchBriefService:
    def __init__(self, session: Session):
        self.session = session

    def create_brief(
        self,
        *,
        title: str = "Advisor Research Brief",
        scope: str = "project",
        idea_ids: list[str] | None = None,
        created_by: str = "researcher",
    ) -> ResearchBrief:
        ideas = self._load_ideas(idea_ids or [])
        if idea_ids and len(ideas) != len(set(idea_ids)):
            raise ValueError("One or more ideas were not found")
        profile = self.session.get(ResearchProfile, "default")
        tasks = self._load_tasks([idea.id for idea in ideas])
        analyses = self._load_analyses([idea.id for idea in ideas])
        plan_summaries = self._load_plan_summaries([idea.id for idea in ideas])
        readiness_signals = self._load_readiness_signals([idea.id for idea in ideas])
        summary = self._summary(ideas, tasks, analyses, profile, plan_summaries, readiness_signals)
        brief = ResearchBrief(
            title=title or "Advisor Research Brief",
            scope=scope or "project",
            idea_ids_json=[idea.id for idea in ideas],
            summary_json=summary,
            created_by=created_by or "researcher",
        )
        self.session.add(brief)
        self.session.flush()
        brief.markdown_export = self._render_markdown(
            brief,
            ideas,
            tasks,
            analyses,
            profile,
            plan_summaries,
            readiness_signals,
        )
        self.session.commit()
        self.session.refresh(brief)
        return brief

    def list_briefs(self, limit: int = 50) -> list[ResearchBrief]:
        limit = max(1, min(limit, 200))
        return (
            self.session.query(ResearchBrief)
            .order_by(ResearchBrief.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_brief(self, brief_id: str) -> ResearchBrief | None:
        return self.session.get(ResearchBrief, brief_id)

    def _load_ideas(self, idea_ids: list[str]) -> list[Idea]:
        if idea_ids:
            records = self.session.query(Idea).filter(Idea.id.in_(idea_ids)).all()
            by_id = {idea.id: idea for idea in records}
            return [by_id[idea_id] for idea_id in idea_ids if idea_id in by_id]
        return self.session.query(Idea).order_by(Idea.updated_at.desc()).limit(8).all()

    def _load_tasks(self, idea_ids: list[str]) -> list[ResearchTask]:
        if not idea_ids:
            return []
        return (
            self.session.query(ResearchTask)
            .filter(ResearchTask.idea_id.in_(idea_ids))
            .order_by(ResearchTask.created_at.desc())
            .limit(300)
            .all()
        )

    def _load_analyses(self, idea_ids: list[str]) -> list[ExperimentAnalysis]:
        if not idea_ids:
            return []
        return (
            self.session.query(ExperimentAnalysis)
            .filter(ExperimentAnalysis.idea_id.in_(idea_ids))
            .order_by(ExperimentAnalysis.created_at.desc())
            .limit(50)
            .all()
        )

    def _load_plan_summaries(self, idea_ids: list[str]) -> list[dict]:
        if not idea_ids:
            return []
        plans = (
            self.session.query(ResearchPlanSnapshot)
            .order_by(ResearchPlanSnapshot.created_at.desc())
            .limit(50)
            .all()
        )
        relevant_plans = [
            plan for plan in plans if set(plan.idea_ids_json or []).intersection(idea_ids)
        ][:8]
        if not relevant_plans:
            return []

        plan_ids = [plan.id for plan in relevant_plans]
        plan_tasks = (
            self.session.query(ResearchTask)
            .filter(
                ResearchTask.owner_type == "research_plan",
                ResearchTask.owner_id.in_(plan_ids),
            )
            .order_by(ResearchTask.created_at.desc())
            .limit(300)
            .all()
        )
        tasks_by_plan: dict[str, list[ResearchTask]] = {plan_id: [] for plan_id in plan_ids}
        for task in plan_tasks:
            tasks_by_plan.setdefault(task.owner_id, []).append(task)

        summaries = []
        for plan in relevant_plans:
            tasks = tasks_by_plan.get(plan.id, [])
            done_count = len([task for task in tasks if task.status in {"done", "archived"}])
            open_tasks = [task for task in tasks if task.status in {"todo", "doing", "blocked"}]
            summaries.append(
                {
                    "id": plan.id,
                    "title": plan.title,
                    "horizon_days": plan.horizon_days,
                    "plan_item_count": len(plan.plan_items_json or []),
                    "task_count": len(tasks),
                    "open_task_count": len(open_tasks),
                    "blocked_task_count": len([task for task in tasks if task.status == "blocked"]),
                    "completion_ratio": round(done_count / len(tasks), 4) if tasks else 0.0,
                }
            )
        return summaries

    def _load_readiness_signals(self, idea_ids: list[str]) -> list[dict]:
        if not idea_ids:
            return []
        reviews = (
            self.session.query(ProposalReview)
            .filter(ProposalReview.idea_id.in_(idea_ids))
            .order_by(ProposalReview.created_at.desc())
            .limit(200)
            .all()
        )
        memos = (
            self.session.query(IdeaDecisionMemo)
            .filter(IdeaDecisionMemo.idea_id.in_(idea_ids))
            .order_by(IdeaDecisionMemo.created_at.desc())
            .limit(200)
            .all()
        )
        latest_review_by_idea = _first_by_idea(reviews)
        latest_memo_by_idea = _first_by_idea(memos)
        signals = []
        for idea_id in idea_ids:
            review = latest_review_by_idea.get(idea_id)
            memo = latest_memo_by_idea.get(idea_id)
            signals.append(
                {
                    "idea_id": idea_id,
                    "proposal_review_decision": review.decision if review else "",
                    "proposal_readiness_score": review.readiness_score if review else 0.0,
                    "decision_memo": memo.decision if memo else "",
                    "next_commitment_count": len(memo.next_commitments_json or []) if memo else 0,
                }
            )
        return signals

    def _summary(
        self,
        ideas: list[Idea],
        tasks: list[ResearchTask],
        analyses: list[ExperimentAnalysis],
        profile: ResearchProfile | None,
        plan_summaries: list[dict],
        readiness_signals: list[dict],
    ) -> dict:
        open_tasks = [task for task in tasks if task.status in {"todo", "doing", "blocked"}]
        blocked_tasks = [task for task in tasks if task.status == "blocked"]
        return {
            "idea_count": len(ideas),
            "idea_status_counts": dict(Counter(idea.status for idea in ideas)),
            "task_count": len(tasks),
            "open_task_count": len(open_tasks),
            "blocked_task_count": len(blocked_tasks),
            "experiment_analysis_count": len(analyses),
            "latest_decisions": [analysis.decision for analysis in analyses[:5]],
            "profile_name": profile.name if profile else "",
            "profile_domains": profile.primary_domains_json if profile else [],
            "profile_constraints": profile.resource_constraints_json if profile else [],
            "research_plan_count": len(plan_summaries),
            "research_plan_open_task_count": sum(
                item.get("open_task_count", 0) for item in plan_summaries
            ),
            "research_plan_blocked_task_count": sum(
                item.get("blocked_task_count", 0) for item in plan_summaries
            ),
            "readiness_signals": readiness_signals,
        }

    def _render_markdown(
        self,
        brief: ResearchBrief,
        ideas: list[Idea],
        tasks: list[ResearchTask],
        analyses: list[ExperimentAnalysis],
        profile: ResearchProfile | None,
        plan_summaries: list[dict],
        readiness_signals: list[dict],
    ) -> str:
        summary = brief.summary_json or {}
        lines = [
            f"# {brief.title}",
            "",
            f"- Brief ID: `{brief.id}`",
            f"- Scope: {brief.scope}",
            f"- Created By: {brief.created_by}",
            f"- Idea Count: {summary.get('idea_count', 0)}",
            f"- Open Tasks: {summary.get('open_task_count', 0)}",
            f"- Blocked Tasks: {summary.get('blocked_task_count', 0)}",
            f"- Research Plans: {summary.get('research_plan_count', 0)}",
            f"- Research Plan Open Tasks: {summary.get('research_plan_open_task_count', 0)}",
            "",
            "## Research Profile",
            "",
        ]
        if profile:
            lines.extend(
                [
                    f"- Name: {profile.name}",
                    f"- Domains: {_join_profile_items(profile.primary_domains_json)}",
                    f"- Target Venues: {_join_profile_items(profile.target_venues_json)}",
                    f"- Risk Tolerance: {profile.risk_tolerance}",
                    f"- Resource Constraints: {_join_profile_items(profile.resource_constraints_json)}",
                    "",
                ]
            )
        else:
            lines.extend(["- No research profile saved.", ""])
        lines.extend(
            [
                "## Ideas",
                "",
            ]
        )
        if ideas:
            for idea in ideas:
                lines.append(f"- `{idea.id}` `{idea.status}` {idea.title}")
        else:
            lines.append("- No ideas selected.")

        lines.extend(["", "## Recent Experiment Decisions", ""])
        if analyses:
            for analysis in analyses[:8]:
                lines.append(
                    f"- `{analysis.id}` idea=`{analysis.idea_id}` "
                    f"{analysis.decision} confidence={analysis.confidence:.2f}"
                )
        else:
            lines.append("- No experiment analyses recorded.")

        lines.extend(["", "## Execution Plans", ""])
        if plan_summaries:
            for plan in plan_summaries[:6]:
                lines.append(
                    f"- `{plan['id']}` {plan['title']} "
                    f"horizon={plan['horizon_days']}d tasks={plan['task_count']} "
                    f"open={plan['open_task_count']} blocked={plan['blocked_task_count']} "
                    f"completion={plan['completion_ratio']}"
                )
        else:
            lines.append("- No research execution plans include these ideas.")

        lines.extend(["", "## Readiness Signals", ""])
        if readiness_signals:
            for signal in readiness_signals:
                lines.append(
                    f"- idea=`{signal['idea_id']}` review=`{signal['proposal_review_decision'] or 'none'}` "
                    f"score={signal['proposal_readiness_score']:.2f} "
                    f"decision=`{signal['decision_memo'] or 'none'}` "
                    f"commitments={signal['next_commitment_count']}"
                )
        else:
            lines.append("- No readiness signals recorded.")

        lines.extend(["", "## Highest Priority Open Tasks", ""])
        open_tasks = sorted(
            [task for task in tasks if task.status in {"todo", "doing", "blocked"}],
            key=self._task_order,
        )[:12]
        if open_tasks:
            for task in open_tasks:
                lines.append(
                    f"- `{task.id}` `{task.priority}` `{task.status}` "
                    f"idea=`{task.idea_id}` {task.title}"
                )
        else:
            lines.append("- No open tasks.")

        lines.extend(["", "## Discussion Prompts", ""])
        lines.extend(self._discussion_prompts(summary, analyses))
        return "\n".join(lines).strip() + "\n"

    def _task_order(self, task: ResearchTask) -> tuple[int, int, str]:
        priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        status_rank = {"blocked": 0, "doing": 1, "todo": 2, "done": 3, "archived": 4}
        return (
            priority_rank.get(task.priority, 9),
            status_rank.get(task.status, 9),
            task.created_at.isoformat(),
        )

    def _discussion_prompts(self, summary: dict, analyses: list[ExperimentAnalysis]) -> list[str]:
        prompts = []
        if summary.get("blocked_task_count", 0):
            prompts.append("- Which blocked task has the highest publication risk?")
        if analyses:
            prompts.append("- Which experiment decision should change the proposal narrative?")
        if summary.get("open_task_count", 0):
            prompts.append("- Which open task is the smallest publishability bottleneck?")
        if not prompts:
            prompts.append(
                "- What new literature should be ingested before the next ideation round?"
            )
        return prompts


def _join_profile_items(items: list | None) -> str:
    return ", ".join(str(item) for item in (items or [])) or "none"


def _first_by_idea(records: list) -> dict[str, object]:
    by_idea = {}
    for record in records:
        if record.idea_id not in by_idea:
            by_idea[record.idea_id] = record
    return by_idea
