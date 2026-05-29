from sqlalchemy.orm import Session

from backend.research.models import ProposalRevision, ResearchTask, ResearchTaskEvent
from backend.research.services.artifact_graph_service import ArtifactGraphService
from backend.research.services.graph_service import GraphService


class ResearchTaskService:
    def __init__(self, session: Session):
        self.session = session

    def create_from_proposal_revision(
        self,
        revision_id: str,
        *,
        created_by: str = "system",
    ) -> list[ResearchTask]:
        revision = self.session.get(ProposalRevision, revision_id)
        if revision is None:
            raise ValueError("Proposal revision not found")

        tasks = []
        for idx, action in enumerate(revision.applied_revisions_json or [], start=1):
            tasks.append(
                self._task(
                    revision,
                    source_type="applied_revision",
                    source_id=f"applied_revision_{idx}",
                    title=f"Apply proposal revision {idx}",
                    description=action,
                    priority="high" if idx <= 3 else "medium",
                    due_phase="next_revision",
                    created_by=created_by,
                )
            )

        for idx, action in enumerate(revision.missing_evidence_actions_json or [], start=1):
            priority = "critical" if "No missing evidence" not in action else "low"
            tasks.append(
                self._task(
                    revision,
                    source_type="missing_evidence_action",
                    source_id=f"missing_evidence_{idx}",
                    title=f"Resolve missing evidence {idx}",
                    description=action,
                    priority=priority,
                    due_phase="before_next_review",
                    created_by=created_by,
                )
            )

        milestones = (revision.revised_sections_json or {}).get("milestone_plan") or []
        for idx, milestone in enumerate(milestones, start=1):
            tasks.append(
                self._task(
                    revision,
                    source_type="milestone",
                    source_id=f"milestone_{idx}",
                    title=str(milestone.get("goal") or f"Milestone {idx}"),
                    description=str(milestone.get("deliverable") or "Deliver milestone."),
                    priority="medium",
                    due_phase=str(milestone.get("window") or ""),
                    created_by=created_by,
                    metadata={"window": milestone.get("window", "")},
                )
            )

        self.session.add_all(tasks)
        self.session.flush()
        self.session.add_all(
            [
                ResearchTaskEvent(
                    task_id=task.id,
                    idea_id=task.idea_id,
                    event_type="created",
                    status_to=task.status,
                    priority_to=task.priority,
                    note=f"Created from proposal revision {revision.id}.",
                    metadata_json={
                        "owner_type": task.owner_type,
                        "owner_id": task.owner_id,
                        "source_type": task.source_type,
                        "source_id": task.source_id,
                    },
                    created_by=created_by or "system",
                )
                for task in tasks
            ]
        )
        self.session.commit()
        for task in tasks:
            self.session.refresh(task)
        ArtifactGraphService(GraphService(self.session)).link_research_tasks(revision, tasks)
        self.session.commit()
        return tasks

    def list_tasks(
        self,
        *,
        idea_id: str | None = None,
        owner_type: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[ResearchTask]:
        limit = max(1, min(limit, 300))
        query = self.session.query(ResearchTask).order_by(ResearchTask.created_at.desc())
        if idea_id:
            query = query.filter(ResearchTask.idea_id == idea_id)
        if owner_type:
            query = query.filter(ResearchTask.owner_type == owner_type)
        if status:
            query = query.filter(ResearchTask.status == status)
        return query.limit(limit).all()

    def get_task(self, task_id: str) -> ResearchTask | None:
        return self.session.get(ResearchTask, task_id)

    def update_task(
        self,
        task_id: str,
        *,
        status: str | None = None,
        priority: str | None = None,
        description: str | None = None,
        note: str = "",
        created_by: str = "system",
    ) -> ResearchTask:
        task = self.session.get(ResearchTask, task_id)
        if task is None:
            raise ValueError("Research task not found")
        status_from = task.status
        priority_from = task.priority
        if status is not None:
            task.status = status
        if priority is not None:
            task.priority = priority
        if description is not None:
            task.description = description
        if status is not None or priority is not None or description is not None or note:
            self.session.add(
                ResearchTaskEvent(
                    task_id=task.id,
                    idea_id=task.idea_id,
                    event_type="task_updated",
                    status_from=status_from,
                    status_to=task.status,
                    priority_from=priority_from,
                    priority_to=task.priority,
                    note=note,
                    metadata_json={
                        "description_updated": description is not None,
                    },
                    created_by=created_by or "system",
                )
            )
        self.session.commit()
        self.session.refresh(task)
        return task

    def create_event(
        self,
        task_id: str,
        *,
        event_type: str = "note",
        note: str = "",
        metadata: dict | None = None,
        created_by: str = "system",
    ) -> ResearchTaskEvent:
        task = self.session.get(ResearchTask, task_id)
        if task is None:
            raise ValueError("Research task not found")
        event = ResearchTaskEvent(
            task_id=task.id,
            idea_id=task.idea_id,
            event_type=event_type or "note",
            status_from=task.status,
            status_to=task.status,
            priority_from=task.priority,
            priority_to=task.priority,
            note=note,
            metadata_json=metadata or {},
            created_by=created_by or "system",
        )
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event

    def list_events(self, task_id: str, limit: int = 50) -> list[ResearchTaskEvent]:
        if self.session.get(ResearchTask, task_id) is None:
            raise ValueError("Research task not found")
        limit = max(1, min(limit, 200))
        return (
            self.session.query(ResearchTaskEvent)
            .filter(ResearchTaskEvent.task_id == task_id)
            .order_by(ResearchTaskEvent.created_at.desc())
            .limit(limit)
            .all()
        )

    def _task(
        self,
        revision: ProposalRevision,
        *,
        source_type: str,
        source_id: str,
        title: str,
        description: str,
        priority: str,
        due_phase: str,
        created_by: str,
        metadata: dict | None = None,
    ) -> ResearchTask:
        return ResearchTask(
            idea_id=revision.idea_id,
            owner_type="proposal_revision",
            owner_id=revision.id,
            source_type=source_type,
            source_id=source_id,
            title=title,
            description=description,
            priority=priority,
            status="todo",
            due_phase=due_phase,
            metadata_json={
                "proposal_draft_id": revision.proposal_draft_id,
                "proposal_review_id": revision.proposal_review_id,
                **(metadata or {}),
            },
            created_by=created_by or "system",
        )
