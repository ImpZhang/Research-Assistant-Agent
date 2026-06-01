from sqlalchemy.orm import Session

from backend.research.models import (
    ExperimentAnalysis,
    Idea,
    IdeaDecisionMemo,
    NoveltyCheck,
    ProposalRevision,
    ResearchPlanSnapshot,
    ResearchTask,
    ResearchTaskEvent,
)
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

    def create_from_experiment_analysis(
        self,
        analysis_id: str,
        *,
        created_by: str = "system",
    ) -> list[ResearchTask]:
        analysis = self.session.get(ExperimentAnalysis, analysis_id)
        if analysis is None:
            raise ValueError("Experiment analysis not found")
        actions = analysis.next_actions_json or [
            "Review the experiment analysis and decide the next execution step."
        ]
        tasks = [
            ResearchTask(
                idea_id=analysis.idea_id,
                owner_type="experiment_analysis",
                owner_id=analysis.id,
                source_type="analysis_next_action",
                source_id=f"next_action_{idx}",
                title=self._short_task_title(action, idx),
                description=action,
                priority=self._analysis_task_priority(analysis.decision),
                status="todo",
                due_phase="next_experiment_cycle",
                metadata_json={
                    "experiment_run_id": analysis.experiment_run_id,
                    "experiment_plan_id": analysis.experiment_plan_id,
                    "decision": analysis.decision,
                    "confidence": analysis.confidence,
                },
                created_by=created_by or "system",
            )
            for idx, action in enumerate(actions, start=1)
        ]
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
                    note=f"Created from experiment analysis {analysis.id}.",
                    metadata_json={
                        "owner_type": task.owner_type,
                        "owner_id": task.owner_id,
                        "source_type": task.source_type,
                        "source_id": task.source_id,
                        "experiment_run_id": analysis.experiment_run_id,
                    },
                    created_by=created_by or "system",
                )
                for task in tasks
            ]
        )
        self.session.commit()
        for task in tasks:
            self.session.refresh(task)
        ArtifactGraphService(GraphService(self.session)).link_experiment_analysis_tasks(
            analysis,
            tasks,
        )
        self.session.commit()
        return tasks

    def create_from_idea_decision_memo(
        self,
        memo_id: str,
        *,
        created_by: str = "system",
    ) -> list[ResearchTask]:
        memo = self.session.get(IdeaDecisionMemo, memo_id)
        if memo is None:
            raise ValueError("Idea decision memo not found")
        commitments = self._unique_commitments(
            memo.next_commitments_json
            or ["Review the decision memo and define the next concrete research step."]
        )[:8]
        priority = self._decision_task_priority(memo.decision)
        tasks = [
            ResearchTask(
                idea_id=memo.idea_id,
                owner_type="idea_decision_memo",
                owner_id=memo.id,
                source_type="decision_commitment",
                source_id=f"commitment_{idx}",
                title=self._short_task_title(commitment, idx),
                description=commitment,
                priority=priority,
                status="todo",
                due_phase="decision_follow_up",
                metadata_json={
                    "decision": memo.decision,
                    "source_artifacts": memo.source_artifacts_json or {},
                },
                created_by=created_by or "system",
            )
            for idx, commitment in enumerate(commitments, start=1)
        ]
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
                    note=f"Created from idea decision memo {memo.id}.",
                    metadata_json={
                        "owner_type": task.owner_type,
                        "owner_id": task.owner_id,
                        "source_type": task.source_type,
                        "source_id": task.source_id,
                        "decision": memo.decision,
                    },
                    created_by=created_by or "system",
                )
                for task in tasks
            ]
        )
        self.session.commit()
        for task in tasks:
            self.session.refresh(task)
        ArtifactGraphService(GraphService(self.session)).link_idea_decision_memo_tasks(
            memo,
            tasks,
        )
        self.session.commit()
        return tasks

    def create_from_research_plan(
        self,
        plan_id: str,
        *,
        created_by: str = "system",
    ) -> list[ResearchTask]:
        plan = self.session.get(ResearchPlanSnapshot, plan_id)
        if plan is None:
            raise ValueError("Research plan not found")
        tasks = []
        for item_index, item in enumerate(plan.plan_items_json or [], start=1):
            actions = item.get("actions") or []
            for action_index, action in enumerate(actions[:4], start=1):
                action_text = " ".join(str(action).split())
                if not action_text:
                    continue
                tasks.append(
                    ResearchTask(
                        idea_id=item.get("idea_id") or None,
                        owner_type="research_plan",
                        owner_id=plan.id,
                        source_type="plan_action",
                        source_id=f"item_{item_index}_action_{action_index}",
                        title=self._short_task_title(action_text, action_index),
                        description=action_text,
                        priority=self._plan_task_priority(str(item.get("phase") or "")),
                        status="todo",
                        due_phase=str(item.get("days") or ""),
                        metadata_json={
                            "plan_title": plan.title,
                            "phase": item.get("phase", ""),
                            "success_check": item.get("success_check", ""),
                            "source_task_ids": item.get("task_ids") or [],
                        },
                        created_by=created_by or "system",
                    )
                )
        tasks = self._deduplicate_plan_tasks(tasks)[:12]
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
                    note=f"Created from research plan {plan.id}.",
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
        ArtifactGraphService(GraphService(self.session)).link_research_plan_tasks(plan, tasks)
        self.session.commit()
        return tasks

    def create_from_idea_readiness(
        self,
        idea_id: str,
        *,
        blockers: list[str],
        readiness_score: float,
        decision: str,
        created_by: str = "system",
    ) -> list[ResearchTask]:
        idea = self.session.get(Idea, idea_id)
        if idea is None:
            raise ValueError("Idea not found")

        blocker_actions = self._unique_commitments(
            blockers or ["Prepare an execution handoff for this ready idea."]
        )[:8]
        tasks = [
            ResearchTask(
                idea_id=idea.id,
                owner_type="idea_readiness",
                owner_id=idea.id,
                source_type="readiness_blocker" if blockers else "readiness_handoff",
                source_id=f"blocker_{idx}" if blockers else "execution_handoff",
                title=self._readiness_task_title(blocker, idx),
                description=blocker,
                priority=self._readiness_task_priority(blocker, decision),
                status="todo",
                due_phase="readiness_follow_up",
                metadata_json={
                    "readiness_score": readiness_score,
                    "readiness_decision": decision,
                    "blocker": blocker,
                },
                created_by=created_by or "system",
            )
            for idx, blocker in enumerate(blocker_actions, start=1)
        ]
        tasks = self._deduplicate_readiness_tasks(tasks)[:8]
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
                    note=f"Created from readiness blockers for idea {idea.id}.",
                    metadata_json={
                        "owner_type": task.owner_type,
                        "owner_id": task.owner_id,
                        "source_type": task.source_type,
                        "source_id": task.source_id,
                        "readiness_score": readiness_score,
                        "readiness_decision": decision,
                    },
                    created_by=created_by or "system",
                )
                for task in tasks
            ]
        )
        self.session.commit()
        for task in tasks:
            self.session.refresh(task)
        ArtifactGraphService(GraphService(self.session)).link_idea_readiness_tasks(idea, tasks)
        self.session.commit()
        return tasks

    def create_from_idea_quality_gate(
        self,
        idea_id: str,
        *,
        gate_score: float,
        decision: str,
        recommended_actions: list[str],
        blocking_risks: list[str],
        missing_evidence_count: int,
        created_by: str = "system",
    ) -> list[ResearchTask]:
        idea = self.session.get(Idea, idea_id)
        if idea is None:
            raise ValueError("Idea not found")

        actions = self._unique_commitments(
            recommended_actions
            or blocking_risks
            or ["Review the quality gate and define the next de-risking action."]
        )[:8]
        tasks = [
            ResearchTask(
                idea_id=idea.id,
                owner_type="idea_quality_gate",
                owner_id=idea.id,
                source_type="quality_gate_recommended_action",
                source_id=f"recommended_action_{idx}",
                title=self._quality_gate_task_title(action, idx),
                description=action,
                priority=self._quality_gate_task_priority(action, decision),
                status="todo",
                due_phase="quality_gate_follow_up",
                metadata_json={
                    "gate_score": gate_score,
                    "quality_gate_decision": decision,
                    "blocking_risk_count": len(blocking_risks),
                    "missing_evidence_count": missing_evidence_count,
                    "blocking_risks": blocking_risks[:5],
                },
                created_by=created_by or "system",
            )
            for idx, action in enumerate(actions, start=1)
        ]
        tasks = self._deduplicate_quality_gate_tasks(tasks)[:8]
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
                    note=f"Created from quality gate for idea {idea.id}.",
                    metadata_json={
                        "owner_type": task.owner_type,
                        "owner_id": task.owner_id,
                        "source_type": task.source_type,
                        "source_id": task.source_id,
                        "gate_score": gate_score,
                        "quality_gate_decision": decision,
                    },
                    created_by=created_by or "system",
                )
                for task in tasks
            ]
        )
        self.session.commit()
        for task in tasks:
            self.session.refresh(task)
        ArtifactGraphService(GraphService(self.session)).link_idea_quality_gate_tasks(idea, tasks)
        self.session.commit()
        return tasks

    def create_from_project_triage(
        self,
        *,
        next_actions: list[str],
        risk_focus: list[str],
        limit: int = 8,
        created_by: str = "system",
    ) -> list[ResearchTask]:
        limit = max(1, min(limit, 20))
        action_items = [
            ("triage_next_action", action)
            for action in self._unique_commitments(next_actions or [])
        ]
        risk_items = [
            ("triage_risk_focus", risk) for risk in self._unique_commitments(risk_focus or [])
        ]
        items = self._deduplicate_triage_items([*action_items, *risk_items])[:limit]
        if not items:
            items = [
                (
                    "triage_next_action",
                    "Review the project triage brief and define the next research action.",
                )
            ]
        tasks = [
            ResearchTask(
                idea_id=None,
                owner_type="project_triage",
                owner_id="project_triage",
                source_type=source_type,
                source_id=f"{source_type}_{idx}",
                title=self._triage_task_title(action, idx),
                description=action,
                priority=self._triage_task_priority(source_type, action),
                status="todo",
                due_phase="triage_follow_up",
                metadata_json={
                    "triage_source_type": source_type,
                    "source_rank": idx,
                },
                created_by=created_by or "system",
            )
            for idx, (source_type, action) in enumerate(items, start=1)
        ]
        self.session.add_all(tasks)
        self.session.flush()
        self.session.add_all(
            [
                ResearchTaskEvent(
                    task_id=task.id,
                    idea_id=None,
                    event_type="created",
                    status_to=task.status,
                    priority_to=task.priority,
                    note="Created from project triage brief.",
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
        ArtifactGraphService(GraphService(self.session)).link_project_triage_tasks(tasks)
        self.session.commit()
        return tasks

    def create_from_opportunity_radar(
        self,
        opportunities: list[dict],
        *,
        actions_per_opportunity: int = 2,
        created_by: str = "system",
    ) -> list[ResearchTask]:
        actions_per_opportunity = max(1, min(actions_per_opportunity, 4))
        tasks = []
        for opportunity in opportunities[:10]:
            idea = self.session.get(Idea, opportunity.get("idea_id", ""))
            if idea is None:
                continue
            actions = self._unique_commitments(opportunity.get("next_actions") or [])[
                :actions_per_opportunity
            ]
            if not actions:
                actions = [f"Review opportunity radar item for {idea.title}."]
            for idx, action in enumerate(actions, start=1):
                tasks.append(
                    ResearchTask(
                        idea_id=idea.id,
                        owner_type="opportunity_radar",
                        owner_id=idea.id,
                        source_type="radar_next_action",
                        source_id=f"rank_{opportunity.get('rank', 0)}_action_{idx}",
                        title=self._opportunity_task_title(action, idx),
                        description=action,
                        priority=self._opportunity_task_priority(
                            str(opportunity.get("priority") or "medium")
                        ),
                        status="todo",
                        due_phase="opportunity_follow_up",
                        metadata_json={
                            "radar_score": opportunity.get("radar_score", 0.0),
                            "weighted_score": opportunity.get("weighted_score", 0.0),
                            "readiness_score": opportunity.get("readiness_score", 0.0),
                            "readiness_decision": opportunity.get("readiness_decision", ""),
                            "opportunity_type": opportunity.get("opportunity_type", ""),
                            "why_now": opportunity.get("why_now", ""),
                        },
                        created_by=created_by or "system",
                    )
                )

        tasks = self._deduplicate_opportunity_tasks(tasks)[:20]
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
                    note=f"Created from opportunity radar for idea {task.idea_id}.",
                    metadata_json={
                        "owner_type": task.owner_type,
                        "owner_id": task.owner_id,
                        "source_type": task.source_type,
                        "source_id": task.source_id,
                        "radar_score": (task.metadata_json or {}).get("radar_score", 0.0),
                    },
                    created_by=created_by or "system",
                )
                for task in tasks
            ]
        )
        self.session.commit()
        for task in tasks:
            self.session.refresh(task)
        ArtifactGraphService(GraphService(self.session)).link_opportunity_radar_tasks(tasks)
        self.session.commit()
        return tasks

    def create_from_novelty_check(
        self,
        check_id: str,
        *,
        created_by: str = "system",
    ) -> list[ResearchTask]:
        check = self.session.get(NoveltyCheck, check_id)
        if check is None:
            raise ValueError("Novelty check not found")
        actions = self._unique_commitments(
            check.recommended_actions_json
            or ["Review novelty signals and update the idea novelty claim."]
        )[:8]
        tasks = [
            ResearchTask(
                idea_id=check.idea_id,
                owner_type="novelty_check",
                owner_id=check.id,
                source_type="novelty_recommended_action",
                source_id=f"recommended_action_{idx}",
                title=self._novelty_task_title(action, idx),
                description=action,
                priority=self._novelty_task_priority(check.risk_level),
                status="todo",
                due_phase="novelty_follow_up",
                metadata_json={
                    "novelty_check_id": check.id,
                    "risk_level": check.risk_level,
                    "local_overlap_score": check.local_overlap_score,
                    "external_overlap_score": check.external_overlap_score,
                    "status": check.status,
                },
                created_by=created_by or "system",
            )
            for idx, action in enumerate(actions, start=1)
        ]
        tasks = self._deduplicate_novelty_tasks(tasks)[:8]
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
                    note=f"Created from novelty check {check.id}.",
                    metadata_json={
                        "owner_type": task.owner_type,
                        "owner_id": task.owner_id,
                        "source_type": task.source_type,
                        "source_id": task.source_id,
                        "risk_level": check.risk_level,
                    },
                    created_by=created_by or "system",
                )
                for task in tasks
            ]
        )
        self.session.commit()
        for task in tasks:
            self.session.refresh(task)
        ArtifactGraphService(GraphService(self.session)).link_novelty_check_tasks(check, tasks)
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

    def _analysis_task_priority(self, decision: str) -> str:
        if decision in {"revise_method", "needs_more_evidence"}:
            return "critical"
        if decision == "supports_hypothesis":
            return "high"
        return "medium"

    def _decision_task_priority(self, decision: str) -> str:
        if decision in {"pursue", "revise"}:
            return "high"
        if decision == "park":
            return "low"
        if decision == "reject":
            return "low"
        return "medium"

    def _plan_task_priority(self, phase: str) -> str:
        if phase == "triage":
            return "critical"
        if phase == "execution":
            return "high"
        return "medium"

    def _short_task_title(self, action: str, idx: int) -> str:
        clean = " ".join(str(action).split())
        if not clean:
            return f"Follow up experiment analysis action {idx}"
        return clean[:96]

    def _readiness_task_title(self, blocker: str, idx: int) -> str:
        clean = " ".join(str(blocker).split())
        lower = clean.lower()
        if "related-work matrix" in lower:
            return "Create related-work matrix"
        if "proposal readiness review" in lower:
            return "Run proposal readiness review"
        if "experiment analysis" in lower:
            return "Analyze latest experiment signal"
        if "decision memo" in lower:
            return "Create idea decision memo"
        if "assumption audit" in lower:
            return "Create assumption audit"
        if "high-risk assumptions" in lower:
            return "Validate high-risk assumptions"
        if lower.startswith("blocked task:"):
            return self._short_task_title(
                "Unblock " + clean.removeprefix("Blocked task:").strip(), idx
            )
        return self._short_task_title(f"Resolve readiness blocker {idx}: {clean}", idx)

    def _readiness_task_priority(self, blocker: str, decision: str) -> str:
        lower = str(blocker).lower()
        if "blocked task" in lower or "high-risk" in lower or decision in {"park", "reject"}:
            return "critical"
        if (
            "no " in lower
            or "missing" in lower
            or "assumption" in lower
            or decision == "needs_work"
        ):
            return "high"
        return "medium"

    def _quality_gate_task_title(self, action: str, idx: int) -> str:
        clean = " ".join(str(action).split())
        lower = clean.lower()
        if "novelty" in lower or "collision" in lower:
            return "De-risk novelty claim"
        if "proposal readiness review" in lower:
            return "Run proposal readiness review"
        if "experiment" in lower:
            return "Strengthen experiment evidence"
        if "decision memo" in lower:
            return "Record quality-gate decision memo"
        if "assumption" in lower:
            return "Validate quality-gate assumptions"
        if lower.startswith("unblock task"):
            return self._short_task_title(clean, idx)
        return self._short_task_title(clean or f"Work quality-gate action {idx}", idx)

    def _quality_gate_task_priority(self, action: str, decision: str) -> str:
        lower = str(action).lower()
        if decision in {"de_risk_novelty", "revise_before_investment", "reject"}:
            return "critical"
        if "blocked" in lower or "high-risk" in lower or "missing" in lower:
            return "critical"
        if decision in {"needs_targeted_revision", "park"}:
            return "high"
        if "review" in lower or "experiment" in lower or "decision" in lower:
            return "high"
        return "medium"

    def _triage_task_title(self, action: str, idx: int) -> str:
        clean = " ".join(str(action).split())
        lower = clean.lower()
        if lower.startswith("blocked task"):
            return self._short_task_title(clean.replace("Blocked task", "Unblock task", 1), idx)
        if "de-risk" in lower or "risk" in lower:
            return self._short_task_title(f"De-risk project item {idx}: {clean}", idx)
        if "opportunity" in lower:
            return self._short_task_title(clean, idx)
        return self._short_task_title(clean or f"Work project triage action {idx}", idx)

    def _triage_task_priority(self, source_type: str, action: str) -> str:
        lower = str(action).lower()
        if source_type == "triage_risk_focus":
            return "critical"
        if "blocked" in lower or "de-risk" in lower or "high-risk" in lower:
            return "critical"
        if "advance" in lower or "opportunity" in lower:
            return "high"
        return "medium"

    def _opportunity_task_title(self, action: str, idx: int) -> str:
        clean = " ".join(str(action).split())
        if clean.lower().startswith("work task"):
            clean = clean.split(":", 1)[-1].strip() or clean
        if clean.lower().startswith("clear blocker:"):
            clean = clean.split(":", 1)[-1].strip() or clean
        return self._short_task_title(clean or f"Work opportunity radar action {idx}", idx)

    def _opportunity_task_priority(self, priority: str) -> str:
        if priority == "critical":
            return "critical"
        if priority == "high":
            return "high"
        if priority == "low":
            return "low"
        return "medium"

    def _novelty_task_title(self, action: str, idx: int) -> str:
        clean = " ".join(str(action).split())
        lower = clean.lower()
        if "external literature search" in lower:
            return "Run external novelty search"
        if "novelty claim" in lower:
            return "Rewrite novelty claim"
        if "collision signals" in lower:
            return "Review novelty collision signals"
        return self._short_task_title(clean or f"Follow up novelty action {idx}", idx)

    def _novelty_task_priority(self, risk_level: str) -> str:
        if risk_level == "high":
            return "critical"
        if risk_level == "medium":
            return "high"
        if risk_level == "low":
            return "medium"
        return "medium"

    def _unique_commitments(self, commitments: list) -> list[str]:
        unique = []
        seen = set()
        for commitment in commitments:
            clean = " ".join(str(commitment).split())
            key = clean.lower()
            if clean and key not in seen:
                unique.append(clean)
                seen.add(key)
        return unique

    def _deduplicate_triage_items(self, items: list[tuple[str, str]]) -> list[tuple[str, str]]:
        unique = []
        seen = set()
        for source_type, action in items:
            clean = " ".join(str(action).split())
            key = clean.lower()
            if clean and key not in seen:
                unique.append((source_type, clean))
                seen.add(key)
        return unique

    def _deduplicate_plan_tasks(self, tasks: list[ResearchTask]) -> list[ResearchTask]:
        unique = []
        seen = set()
        for task in tasks:
            key = (task.idea_id or "", task.title.lower(), task.owner_id)
            if key not in seen:
                unique.append(task)
                seen.add(key)
        return unique

    def _deduplicate_readiness_tasks(self, tasks: list[ResearchTask]) -> list[ResearchTask]:
        unique = []
        seen = set()
        for task in tasks:
            key = (task.idea_id or "", task.title.lower(), task.description.lower())
            if key not in seen:
                unique.append(task)
                seen.add(key)
        return unique

    def _deduplicate_quality_gate_tasks(self, tasks: list[ResearchTask]) -> list[ResearchTask]:
        unique = []
        seen = set()
        for task in tasks:
            key = (task.idea_id or "", task.title.lower(), task.description.lower())
            if key not in seen:
                unique.append(task)
                seen.add(key)
        return unique

    def _deduplicate_opportunity_tasks(self, tasks: list[ResearchTask]) -> list[ResearchTask]:
        unique = []
        seen = set()
        for task in tasks:
            key = (task.idea_id or "", task.title.lower(), task.description.lower())
            if key not in seen:
                unique.append(task)
                seen.add(key)
        return unique

    def _deduplicate_novelty_tasks(self, tasks: list[ResearchTask]) -> list[ResearchTask]:
        unique = []
        seen = set()
        for task in tasks:
            key = (task.idea_id or "", task.title.lower(), task.description.lower())
            if key not in seen:
                unique.append(task)
                seen.add(key)
        return unique
