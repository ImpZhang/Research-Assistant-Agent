from collections import Counter

from sqlalchemy.orm import Session

from backend.research.models import ExperimentAnalysis, Idea, ResearchBrief, ResearchTask


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
        tasks = self._load_tasks([idea.id for idea in ideas])
        analyses = self._load_analyses([idea.id for idea in ideas])
        summary = self._summary(ideas, tasks, analyses)
        brief = ResearchBrief(
            title=title or "Advisor Research Brief",
            scope=scope or "project",
            idea_ids_json=[idea.id for idea in ideas],
            summary_json=summary,
            created_by=created_by or "researcher",
        )
        self.session.add(brief)
        self.session.flush()
        brief.markdown_export = self._render_markdown(brief, ideas, tasks, analyses)
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

    def _summary(
        self,
        ideas: list[Idea],
        tasks: list[ResearchTask],
        analyses: list[ExperimentAnalysis],
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
        }

    def _render_markdown(
        self,
        brief: ResearchBrief,
        ideas: list[Idea],
        tasks: list[ResearchTask],
        analyses: list[ExperimentAnalysis],
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
            "",
            "## Ideas",
            "",
        ]
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
