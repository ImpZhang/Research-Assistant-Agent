from backend.research.models import (
    ExperimentPlan,
    ExperimentRun,
    ProposalDraft,
    ProposalReview,
    ProposalRevision,
    ResearchTask,
    TaskBoardSnapshot,
)
from backend.research.services.graph_service import GraphService


class ArtifactGraphService:
    def __init__(self, graph: GraphService):
        self.graph = graph

    def link_proposal_draft(self, draft: ProposalDraft) -> None:
        idea_node = self._idea_node(draft.idea_id)
        draft_node = self.graph.get_or_create_node(
            node_type="proposal_draft",
            label=draft.title,
            canonical_key=draft.id,
            payload={
                "status": draft.status,
                "related_work_matrix_id": draft.related_work_matrix_id,
                "experiment_plan_id": draft.experiment_plan_id,
            },
        )
        self.graph.create_edge(
            source_node=idea_node,
            target_node=draft_node,
            edge_type="idea_has_proposal_draft",
            evidence_ids=draft.evidence_ids_json or [],
            payload={"source": "proposal_draft"},
        )

    def link_proposal_review(self, review: ProposalReview) -> None:
        draft_node = self.graph.get_or_create_node(
            node_type="proposal_draft",
            label=f"Proposal draft {review.proposal_draft_id}",
            canonical_key=review.proposal_draft_id,
        )
        review_node = self.graph.get_or_create_node(
            node_type="proposal_review",
            label=f"{review.reviewer_type}: {review.decision}",
            canonical_key=review.id,
            payload={
                "decision": review.decision,
                "readiness_score": review.readiness_score,
                "idea_id": review.idea_id,
            },
        )
        self.graph.create_edge(
            source_node=review_node,
            target_node=draft_node,
            edge_type="proposal_review_reviews_draft",
            payload={"source": "proposal_review"},
        )

    def link_proposal_revision(self, revision: ProposalRevision) -> None:
        draft_node = self.graph.get_or_create_node(
            node_type="proposal_draft",
            label=f"Proposal draft {revision.proposal_draft_id}",
            canonical_key=revision.proposal_draft_id,
        )
        revision_node = self.graph.get_or_create_node(
            node_type="proposal_revision",
            label=f"Revision {revision.status}",
            canonical_key=revision.id,
            payload={
                "status": revision.status,
                "proposal_review_id": revision.proposal_review_id,
                "idea_id": revision.idea_id,
            },
        )
        self.graph.create_edge(
            source_node=revision_node,
            target_node=draft_node,
            edge_type="proposal_revision_updates_draft",
            payload={"source": "proposal_revision"},
        )
        if revision.proposal_review_id:
            review_node = self.graph.get_or_create_node(
                node_type="proposal_review",
                label=f"Proposal review {revision.proposal_review_id}",
                canonical_key=revision.proposal_review_id,
            )
            self.graph.create_edge(
                source_node=revision_node,
                target_node=review_node,
                edge_type="proposal_revision_addresses_review",
                payload={"source": "proposal_revision"},
            )

    def link_research_tasks(
        self,
        revision: ProposalRevision,
        tasks: list[ResearchTask],
    ) -> None:
        revision_node = self.graph.get_or_create_node(
            node_type="proposal_revision",
            label=f"Revision {revision.status}",
            canonical_key=revision.id,
        )
        for task in tasks:
            task_node = self.graph.get_or_create_node(
                node_type="research_task",
                label=task.title,
                canonical_key=task.id,
                payload={
                    "status": task.status,
                    "priority": task.priority,
                    "source_type": task.source_type,
                    "due_phase": task.due_phase,
                },
            )
            self.graph.create_edge(
                source_node=revision_node,
                target_node=task_node,
                edge_type="proposal_revision_creates_task",
                payload={"source": "research_task_backlog"},
            )

    def link_task_board_snapshot(
        self,
        snapshot: TaskBoardSnapshot,
        tasks: list[ResearchTask],
    ) -> None:
        snapshot_node = self.graph.get_or_create_node(
            node_type="task_board_snapshot",
            label=snapshot.title,
            canonical_key=snapshot.id,
            payload={
                "idea_id": snapshot.idea_id,
                "owner_type": snapshot.owner_type,
                "task_count": len(snapshot.task_ids_json or []),
            },
        )
        for task in tasks:
            task_node = self.graph.get_or_create_node(
                node_type="research_task",
                label=task.title,
                canonical_key=task.id,
                payload={"status": task.status, "priority": task.priority},
            )
            self.graph.create_edge(
                source_node=snapshot_node,
                target_node=task_node,
                edge_type="task_board_snapshot_tracks_task",
                payload={"source": "task_board_snapshot"},
            )

    def link_experiment_run(
        self,
        plan: ExperimentPlan,
        run: ExperimentRun,
        task: ResearchTask | None = None,
    ) -> None:
        idea_node = self._idea_node(run.idea_id)
        plan_node = self.graph.get_or_create_node(
            node_type="experiment_plan",
            label=f"Experiment plan {plan.id}",
            canonical_key=plan.id,
            payload={
                "idea_id": plan.idea_id,
                "objective": plan.objective,
            },
        )
        run_node = self.graph.get_or_create_node(
            node_type="experiment_run",
            label=run.title,
            canonical_key=run.id,
            payload={
                "status": run.status,
                "experiment_plan_id": run.experiment_plan_id,
                "task_id": run.task_id,
                "conclusion": run.conclusion,
            },
        )
        self.graph.create_edge(
            source_node=idea_node,
            target_node=plan_node,
            edge_type="idea_has_experiment_plan",
            payload={"source": "experiment_run"},
        )
        self.graph.create_edge(
            source_node=plan_node,
            target_node=run_node,
            edge_type="experiment_plan_has_run",
            payload={"source": "experiment_run"},
        )
        self.graph.create_edge(
            source_node=idea_node,
            target_node=run_node,
            edge_type="idea_has_experiment_run",
            payload={"source": "experiment_run"},
        )
        if task is not None:
            task_node = self.graph.get_or_create_node(
                node_type="research_task",
                label=task.title,
                canonical_key=task.id,
                payload={"status": task.status, "priority": task.priority},
            )
            self.graph.create_edge(
                source_node=task_node,
                target_node=run_node,
                edge_type="task_records_experiment_run",
                payload={"source": "experiment_run"},
            )

    def _idea_node(self, idea_id: str):
        return self.graph.get_or_create_node(
            node_type="idea",
            label=f"Idea {idea_id}",
            canonical_key=idea_id,
        )
