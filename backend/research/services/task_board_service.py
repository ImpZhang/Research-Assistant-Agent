from collections import Counter

from sqlalchemy.orm import Session

from backend.research.models import ResearchTask, TaskBoardSnapshot


class TaskBoardService:
    def __init__(self, session: Session):
        self.session = session

    def create_snapshot(
        self,
        *,
        title: str = "Research Task Board",
        idea_id: str | None = None,
        owner_type: str = "",
        statuses: list[str] | None = None,
        created_by: str = "system",
    ) -> TaskBoardSnapshot:
        tasks = self._load_tasks(idea_id, owner_type, statuses or [])
        summary = self._summary(tasks)
        snapshot = TaskBoardSnapshot(
            title=title or "Research Task Board",
            idea_id=idea_id,
            owner_type=owner_type or "",
            status_filter_json=statuses or [],
            task_ids_json=[task.id for task in tasks],
            summary_json=summary,
            created_by=created_by or "system",
        )
        snapshot.markdown_export = self._render_markdown(snapshot, tasks)
        self.session.add(snapshot)
        self.session.commit()
        self.session.refresh(snapshot)
        return snapshot

    def list_snapshots(self, limit: int = 50) -> list[TaskBoardSnapshot]:
        limit = max(1, min(limit, 200))
        return (
            self.session.query(TaskBoardSnapshot)
            .order_by(TaskBoardSnapshot.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_snapshot(self, snapshot_id: str) -> TaskBoardSnapshot | None:
        return self.session.get(TaskBoardSnapshot, snapshot_id)

    def _load_tasks(
        self,
        idea_id: str | None,
        owner_type: str,
        statuses: list[str],
    ) -> list[ResearchTask]:
        query = self.session.query(ResearchTask).order_by(ResearchTask.created_at.desc())
        if idea_id:
            query = query.filter(ResearchTask.idea_id == idea_id)
        if owner_type:
            query = query.filter(ResearchTask.owner_type == owner_type)
        if statuses:
            query = query.filter(ResearchTask.status.in_(statuses))
        return query.limit(300).all()

    def _summary(self, tasks: list[ResearchTask]) -> dict:
        by_status = Counter(task.status for task in tasks)
        by_priority = Counter(task.priority for task in tasks)
        blocked = [task.id for task in tasks if task.status == "blocked"]
        next_actions = [
            {
                "id": task.id,
                "title": task.title,
                "priority": task.priority,
                "status": task.status,
                "due_phase": task.due_phase,
            }
            for task in sorted(tasks, key=self._task_order)[:8]
        ]
        return {
            "task_count": len(tasks),
            "by_status": dict(by_status),
            "by_priority": dict(by_priority),
            "blocked_task_ids": blocked,
            "next_actions": next_actions,
        }

    def _task_order(self, task: ResearchTask) -> tuple[int, int, str]:
        priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        status_rank = {"doing": 0, "blocked": 1, "todo": 2, "done": 3, "archived": 4}
        return (
            priority_rank.get(task.priority, 9),
            status_rank.get(task.status, 9),
            task.created_at.isoformat(),
        )

    def _render_markdown(self, snapshot: TaskBoardSnapshot, tasks: list[ResearchTask]) -> str:
        summary = snapshot.summary_json or {}
        lines = [
            f"# {snapshot.title}",
            "",
            f"- Snapshot ID: `{snapshot.id}`",
            f"- Idea ID: `{snapshot.idea_id or 'all'}`",
            f"- Owner Type: `{snapshot.owner_type or 'all'}`",
            f"- Status Filter: {self._inline(snapshot.status_filter_json or [])}",
            f"- Task Count: {summary.get('task_count', 0)}",
            "",
            "## Status Summary",
            "",
        ]
        for status, count in (summary.get("by_status") or {}).items():
            lines.append(f"- `{status}`: {count}")
        lines.extend(["", "## Priority Summary", ""])
        for priority, count in (summary.get("by_priority") or {}).items():
            lines.append(f"- `{priority}`: {count}")

        lines.extend(["", "## Next Actions", ""])
        next_actions = summary.get("next_actions") or []
        if not next_actions:
            lines.append("- No tasks matched this snapshot.")
        for action in next_actions:
            lines.append(
                f"- `{action['priority']}` `{action['status']}` "
                f"{action['title']} ({action.get('due_phase') or 'no due phase'})"
            )

        lines.extend(["", "## Tasks", ""])
        for task in tasks:
            lines.append(
                f"- `{task.id}` `{task.priority}` `{task.status}` {task.title}: {task.description}"
            )
        return "\n".join(lines).strip() + "\n"

    def _inline(self, items: list[str]) -> str:
        if not items:
            return "`all`"
        return ", ".join(f"`{item}`" for item in items)
