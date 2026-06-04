from sqlalchemy.orm import Session

from backend.research.models import (
    ExperimentAnalysis,
    Idea,
    IdeaDecisionMemo,
    IdeaEvidenceLedger,
    NoveltyCheck,
    ProposalRevision,
    ResearchBrief,
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

    def create_from_idea_evidence_ledger(
        self,
        ledger_id: str,
        *,
        created_by: str = "system",
    ) -> list[ResearchTask]:
        ledger = self.session.get(IdeaEvidenceLedger, ledger_id)
        if ledger is None:
            raise ValueError("Idea evidence ledger not found")

        tasks = []
        for idx, claim in enumerate(ledger.claims_json or [], start=1):
            support_level = str(claim.get("support_level") or "")
            if support_level not in {"unsupported", "partially_supported", "challenged"}:
                continue
            claim_id = str(claim.get("claim_id") or f"C{idx}")
            description = str(
                claim.get("next_validation")
                or claim.get("claim")
                or "Validate this evidence-ledger claim."
            )
            tasks.append(
                ResearchTask(
                    idea_id=ledger.idea_id,
                    owner_type="idea_evidence_ledger",
                    owner_id=ledger.id,
                    source_type="claim_validation",
                    source_id=claim_id,
                    title=self._ledger_task_title(description, idx, source_type="claim"),
                    description=description,
                    priority=self._ledger_task_priority(
                        support_level,
                        fallback="high",
                    ),
                    status="todo",
                    due_phase="evidence_follow_up",
                    metadata_json={
                        "claim_id": claim_id,
                        "claim_type": claim.get("claim_type", ""),
                        "support_level": support_level,
                        "supporting_evidence_ids": claim.get("supporting_evidence_ids") or [],
                        "coverage_score": ledger.coverage_score,
                    },
                    created_by=created_by or "system",
                )
            )

        for idx, item in enumerate(ledger.missing_evidence_json or [], start=1):
            gap = str(item.get("gap") or "Resolve missing evidence from the ledger.")
            tasks.append(
                ResearchTask(
                    idea_id=ledger.idea_id,
                    owner_type="idea_evidence_ledger",
                    owner_id=ledger.id,
                    source_type="missing_evidence",
                    source_id=str(item.get("source_id") or f"missing_evidence_{idx}"),
                    title=self._ledger_task_title(gap, idx, source_type="missing_evidence"),
                    description=gap,
                    priority=self._ledger_task_priority(
                        str(item.get("priority") or ""),
                        fallback="high",
                    ),
                    status="todo",
                    due_phase="evidence_follow_up",
                    metadata_json={
                        "ledger_item": item,
                        "coverage_score": ledger.coverage_score,
                    },
                    created_by=created_by or "system",
                )
            )

        for idx, item in enumerate(ledger.counterevidence_json or [], start=1):
            signal = str(item.get("signal") or "Review counterevidence from the ledger.")
            tasks.append(
                ResearchTask(
                    idea_id=ledger.idea_id,
                    owner_type="idea_evidence_ledger",
                    owner_id=ledger.id,
                    source_type="counterevidence",
                    source_id=str(item.get("source_id") or f"counterevidence_{idx}"),
                    title=self._ledger_task_title(signal, idx, source_type="counterevidence"),
                    description=signal,
                    priority=self._ledger_task_priority(
                        str(item.get("severity") or ""),
                        fallback="medium",
                    ),
                    status="todo",
                    due_phase="evidence_follow_up",
                    metadata_json={
                        "ledger_item": item,
                        "coverage_score": ledger.coverage_score,
                    },
                    created_by=created_by or "system",
                )
            )

        for idx, item in enumerate(ledger.risk_register_json or [], start=1):
            risk = str(item.get("risk") or "Resolve evidence-ledger risk.")
            tasks.append(
                ResearchTask(
                    idea_id=ledger.idea_id,
                    owner_type="idea_evidence_ledger",
                    owner_id=ledger.id,
                    source_type="evidence_risk",
                    source_id=f"evidence_risk_{idx}",
                    title=self._ledger_task_title(risk, idx, source_type="risk"),
                    description=risk,
                    priority=self._ledger_task_priority(
                        str(item.get("severity") or ""),
                        fallback="medium",
                    ),
                    status="todo",
                    due_phase="evidence_follow_up",
                    metadata_json={
                        "ledger_item": item,
                        "coverage_score": ledger.coverage_score,
                    },
                    created_by=created_by or "system",
                )
            )

        if not tasks:
            tasks.append(
                ResearchTask(
                    idea_id=ledger.idea_id,
                    owner_type="idea_evidence_ledger",
                    owner_id=ledger.id,
                    source_type="evidence_review",
                    source_id="ledger_review",
                    title="Review evidence ledger with advisor",
                    description=(
                        "Review the evidence ledger and decide whether the idea can advance "
                        "to advisor discussion or needs a sharper validation pass."
                    ),
                    priority="medium",
                    status="todo",
                    due_phase="evidence_follow_up",
                    metadata_json={
                        "coverage_score": ledger.coverage_score,
                        "summary": ledger.summary_json or {},
                    },
                    created_by=created_by or "system",
                )
            )

        tasks = self._deduplicate_evidence_ledger_tasks(tasks)[:12]
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
                    note=f"Created from idea evidence ledger {ledger.id}.",
                    metadata_json={
                        "owner_type": task.owner_type,
                        "owner_id": task.owner_id,
                        "source_type": task.source_type,
                        "source_id": task.source_id,
                        "coverage_score": ledger.coverage_score,
                    },
                    created_by=created_by or "system",
                )
                for task in tasks
            ]
        )
        self.session.commit()
        for task in tasks:
            self.session.refresh(task)
        ArtifactGraphService(GraphService(self.session)).link_idea_evidence_ledger_tasks(
            ledger,
            tasks,
        )
        self.session.commit()
        return tasks

    def create_from_claim_validation_queue(
        self,
        queue_items: list[dict],
        *,
        limit: int = 5,
        priority_filter: list[str] | None = None,
        created_by: str = "system",
    ) -> list[ResearchTask]:
        limit = max(1, min(limit, 20))
        allowed_priorities = {str(priority) for priority in (priority_filter or [])}
        candidates = [
            item
            for item in queue_items
            if not allowed_priorities or str(item.get("priority") or "") in allowed_priorities
        ]
        if not candidates and allowed_priorities:
            candidates = list(queue_items)

        tasks = []
        for idx, item in enumerate(candidates[:limit], start=1):
            idea = item.get("idea") or {}
            idea_id = str(idea.get("id") or item.get("idea_id") or "")
            if not idea_id:
                continue
            ledger_id = str(item.get("ledger_id") or "")
            claim_id = str(item.get("claim_id") or f"claim_{idx}")
            action = str(
                item.get("recommended_action")
                or item.get("next_validation")
                or item.get("claim")
                or "Validate this claim before advancing the idea."
            )
            source_id = f"{ledger_id}:{claim_id}" if ledger_id else claim_id
            tasks.append(
                ResearchTask(
                    idea_id=idea_id,
                    owner_type="claim_validation_queue",
                    owner_id=ledger_id or "claim_validation_queue",
                    source_type="claim_validation_queue_item",
                    source_id=source_id,
                    title=self._claim_queue_task_title(action, item, idx),
                    description=action,
                    priority=self._claim_queue_task_priority(str(item.get("priority") or "")),
                    status="todo",
                    due_phase="claim_validation_follow_up",
                    metadata_json={
                        "ledger_id": ledger_id,
                        "claim_id": claim_id,
                        "claim": item.get("claim", ""),
                        "claim_type": item.get("claim_type", ""),
                        "support_level": item.get("support_level", ""),
                        "queue_priority": item.get("priority", ""),
                        "urgency_score": item.get("urgency_score", 0.0),
                        "supporting_evidence_count": item.get("supporting_evidence_count", 0),
                        "missing_evidence_count": item.get("missing_evidence_count", 0),
                        "counterevidence_count": item.get("counterevidence_count", 0),
                        "related_task_count": item.get("related_task_count", 0),
                        "source_rank": idx,
                    },
                    created_by=created_by or "system",
                )
            )

        tasks = self._deduplicate_claim_queue_tasks(tasks)[:limit]
        if not tasks:
            return []

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
                    note="Created from claim validation queue.",
                    metadata_json={
                        "owner_type": task.owner_type,
                        "owner_id": task.owner_id,
                        "source_type": task.source_type,
                        "source_id": task.source_id,
                        "queue_priority": (task.metadata_json or {}).get("queue_priority", ""),
                        "urgency_score": (task.metadata_json or {}).get("urgency_score", 0.0),
                    },
                    created_by=created_by or "system",
                )
                for task in tasks
            ]
        )
        self.session.commit()
        for task in tasks:
            self.session.refresh(task)
        ArtifactGraphService(GraphService(self.session)).link_claim_validation_queue_tasks(tasks)
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

    def create_from_project_cockpit(
        self,
        cockpit: dict,
        *,
        limit: int = 8,
        include_primary_action: bool = True,
        include_next_actions: bool = True,
        include_risks: bool = True,
        include_highlights: bool = False,
        created_by: str = "system",
    ) -> list[ResearchTask]:
        limit = max(1, min(limit, 20))
        phase = str(cockpit.get("phase") or "")
        readiness_level = str(cockpit.get("readiness_level") or "")
        source_summaries = cockpit.get("source_summaries") or {}
        items: list[tuple[str, str, dict]] = []
        if include_primary_action:
            primary = cockpit.get("primary_next_action") or {}
            label = str(primary.get("label") or "").strip()
            reason = str(primary.get("reason") or "").strip()
            if label:
                items.append(
                    (
                        "cockpit_primary_action",
                        f"{label}. {reason}".strip(),
                        {
                            "method": primary.get("method", ""),
                            "path": primary.get("path", ""),
                            "enabled": primary.get("enabled", True),
                        },
                    )
                )
        if include_next_actions:
            for action in self._unique_commitments(source_summaries.get("next_actions") or []):
                items.append(("cockpit_next_action", action, {}))
        if include_risks:
            for risk in self._unique_commitments(cockpit.get("risk_alerts") or []):
                items.append(("cockpit_risk_alert", risk, {}))
        if include_highlights:
            for highlight in self._unique_commitments(cockpit.get("highlights") or []):
                items.append(("cockpit_highlight", highlight, {}))

        items = self._deduplicate_cockpit_items(items)[:limit]
        if not items:
            items = [
                (
                    "cockpit_review",
                    "Review the project cockpit and define the next customer-facing research action.",
                    {},
                )
            ]

        tasks = [
            ResearchTask(
                idea_id=None,
                owner_type="project_cockpit",
                owner_id="project_cockpit",
                source_type=source_type,
                source_id=f"{source_type}_{idx}",
                title=self._cockpit_task_title(action, idx, source_type=source_type),
                description=action,
                priority=self._cockpit_task_priority(source_type, action, phase),
                status="todo",
                due_phase="cockpit_follow_up",
                metadata_json={
                    "cockpit_phase": phase,
                    "cockpit_readiness_level": readiness_level,
                    "cockpit_source_type": source_type,
                    "source_rank": idx,
                    **metadata,
                },
                created_by=created_by or "system",
            )
            for idx, (source_type, action, metadata) in enumerate(items, start=1)
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
                    note="Created from project cockpit.",
                    metadata_json={
                        "owner_type": task.owner_type,
                        "owner_id": task.owner_id,
                        "source_type": task.source_type,
                        "source_id": task.source_id,
                        "cockpit_phase": phase,
                        "cockpit_readiness_level": readiness_level,
                    },
                    created_by=created_by or "system",
                )
                for task in tasks
            ]
        )
        self.session.commit()
        for task in tasks:
            self.session.refresh(task)
        ArtifactGraphService(GraphService(self.session)).link_project_cockpit_tasks(cockpit, tasks)
        self.session.commit()
        return tasks

    def create_from_project_pilot_report_snapshot(
        self,
        snapshot: ResearchBrief,
        *,
        limit: int = 8,
        include_risks: bool = True,
        include_next_actions: bool = True,
        include_quick_actions: bool = True,
        created_by: str = "system",
    ) -> list[ResearchTask]:
        limit = max(1, min(limit, 20))
        summary = snapshot.summary_json or {}
        report_status = str(summary.get("report_status") or "")
        readiness_level = str(summary.get("readiness_level") or "")
        cockpit_phase = str(summary.get("cockpit_phase") or "")
        items: list[tuple[str, str, dict]] = []

        if include_risks:
            for risk in self._unique_commitments(summary.get("risks") or []):
                items.append(("pilot_report_risk", risk, {}))
        if include_next_actions:
            for action in self._unique_commitments(summary.get("next_actions") or []):
                items.append(("pilot_report_next_action", action, {}))
        if include_quick_actions:
            for action in summary.get("quick_actions") or []:
                if not isinstance(action, dict):
                    text = " ".join(str(action).split())
                    metadata = {}
                else:
                    label = str(action.get("label") or "Pilot report quick action").strip()
                    reason = str(action.get("reason") or "").strip()
                    text = f"{label}: {reason}" if reason else label
                    metadata = {
                        "method": action.get("method", ""),
                        "path": action.get("path", ""),
                        "enabled": action.get("enabled", True),
                    }
                if text:
                    items.append(("pilot_report_quick_action", text, metadata))

        items = self._deduplicate_pilot_report_items(items)[:limit]
        if not items:
            items = [
                (
                    "pilot_report_review",
                    "Review the saved pilot report snapshot and define the next customer-facing action.",
                    {},
                )
            ]

        tasks = [
            ResearchTask(
                idea_id=None,
                owner_type="project_pilot_report_snapshot",
                owner_id=snapshot.id,
                source_type=source_type,
                source_id=f"{source_type}_{idx}",
                title=self._pilot_report_snapshot_task_title(
                    action,
                    idx,
                    source_type=source_type,
                ),
                description=action,
                priority=self._pilot_report_snapshot_task_priority(
                    source_type,
                    action,
                    report_status,
                ),
                status="todo",
                due_phase="pilot_report_follow_up",
                metadata_json={
                    "snapshot_id": snapshot.id,
                    "snapshot_title": snapshot.title,
                    "report_status": report_status,
                    "readiness_level": readiness_level,
                    "cockpit_phase": cockpit_phase,
                    "source_rank": idx,
                    **metadata,
                },
                created_by=created_by or "system",
            )
            for idx, (source_type, action, metadata) in enumerate(items, start=1)
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
                    note="Created from project pilot report snapshot.",
                    metadata_json={
                        "owner_type": task.owner_type,
                        "owner_id": task.owner_id,
                        "source_type": task.source_type,
                        "source_id": task.source_id,
                        "snapshot_id": snapshot.id,
                        "report_status": report_status,
                    },
                    created_by=created_by or "system",
                )
                for task in tasks
            ]
        )
        self.session.commit()
        for task in tasks:
            self.session.refresh(task)
        ArtifactGraphService(GraphService(self.session)).link_project_pilot_report_snapshot_tasks(
            snapshot,
            tasks,
        )
        self.session.commit()
        return tasks

    def create_from_project_onboarding(
        self,
        readiness: dict,
        *,
        limit: int = 8,
        include_optional: bool = True,
        created_by: str = "system",
    ) -> list[ResearchTask]:
        limit = max(1, min(limit, 20))
        readiness_level = str(readiness.get("readiness_level") or "")
        readiness_score = float(readiness.get("readiness_score") or 0.0)
        checklist = readiness.get("checklist") or []
        items = [
            item
            for item in checklist
            if item.get("status") != "done" and (item.get("required", True) or include_optional)
        ][:limit]
        if not items:
            items = [
                {
                    "id": "onboarding_review",
                    "label": "Review project onboarding readiness",
                    "status": readiness_level,
                    "detail": "Confirm the pilot setup with the customer and open project cockpit.",
                    "required": False,
                    "action_label": "Open cockpit",
                    "action_method": "GET",
                    "action_path": "/research/cockpit",
                }
            ]

        tasks = [
            ResearchTask(
                idea_id=None,
                owner_type="project_onboarding",
                owner_id="project_onboarding",
                source_type=(
                    "onboarding_required_check"
                    if item.get("required", True)
                    else "onboarding_optional_check"
                ),
                source_id=str(item.get("id") or f"onboarding_{idx}"),
                title=self._onboarding_task_title(item, idx),
                description=self._onboarding_task_description(item),
                priority=self._onboarding_task_priority(item),
                status="todo",
                due_phase="onboarding_follow_up",
                metadata_json={
                    "check_id": item.get("id", ""),
                    "check_label": item.get("label", ""),
                    "check_status": item.get("status", ""),
                    "required": item.get("required", True),
                    "action_label": item.get("action_label", ""),
                    "action_method": item.get("action_method", ""),
                    "action_path": item.get("action_path", ""),
                    "readiness_level": readiness_level,
                    "readiness_score": readiness_score,
                    "source_rank": idx,
                },
                created_by=created_by or "system",
            )
            for idx, item in enumerate(items, start=1)
        ]
        tasks = self._deduplicate_onboarding_tasks(tasks)[:limit]
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
                    note="Created from project onboarding readiness.",
                    metadata_json={
                        "owner_type": task.owner_type,
                        "owner_id": task.owner_id,
                        "source_type": task.source_type,
                        "source_id": task.source_id,
                        "readiness_level": readiness_level,
                        "readiness_score": readiness_score,
                    },
                    created_by=created_by or "system",
                )
                for task in tasks
            ]
        )
        self.session.commit()
        for task in tasks:
            self.session.refresh(task)
        ArtifactGraphService(GraphService(self.session)).link_project_onboarding_tasks(
            readiness,
            tasks,
        )
        self.session.commit()
        return tasks

    def create_from_project_advisor_chat(
        self,
        chat: dict,
        *,
        limit: int = 8,
        include_recommendations: bool = True,
        include_risks: bool = True,
        include_tool_suggestions: bool = False,
        created_by: str = "system",
    ) -> list[ResearchTask]:
        limit = max(1, min(limit, 20))
        question = str(chat.get("question") or "")
        intent = str(chat.get("intent") or "project_status")
        cockpit_phase = str(chat.get("cockpit_phase") or "")
        readiness_level = str(chat.get("readiness_level") or "")
        items: list[tuple[str, str, dict]] = []
        if include_recommendations:
            for action in self._unique_commitments(chat.get("recommended_actions") or []):
                items.append(("advisor_recommended_action", action, {}))
        if include_risks:
            for risk in self._unique_commitments(chat.get("risk_alerts") or []):
                items.append(("advisor_risk_alert", risk, {}))
        if include_tool_suggestions:
            for idx, tool in enumerate(chat.get("tool_suggestions") or [], start=1):
                name = str(tool.get("name") or f"tool_{idx}")
                reason = str(tool.get("reason") or "")
                action = f"Use {name}: {reason}".strip()
                items.append(
                    (
                        "advisor_tool_suggestion",
                        action,
                        {
                            "tool_name": name,
                            "method": tool.get("method", ""),
                            "path": tool.get("path", ""),
                        },
                    )
                )

        items = self._deduplicate_advisor_chat_items(items)[:limit]
        if not items:
            items = [
                (
                    "advisor_chat_review",
                    "Review the advisor chat answer and define the next research action.",
                    {},
                )
            ]

        tasks = [
            ResearchTask(
                idea_id=None,
                owner_type="project_advisor_chat",
                owner_id="project_advisor_chat",
                source_type=source_type,
                source_id=f"{source_type}_{idx}",
                title=self._advisor_chat_task_title(action, idx, source_type=source_type),
                description=action,
                priority=self._advisor_chat_task_priority(source_type, action, intent),
                status="todo",
                due_phase="advisor_chat_follow_up",
                metadata_json={
                    "advisor_question": question,
                    "advisor_intent": intent,
                    "cockpit_phase": cockpit_phase,
                    "readiness_level": readiness_level,
                    "advisor_source_type": source_type,
                    "source_rank": idx,
                    **metadata,
                },
                created_by=created_by or "system",
            )
            for idx, (source_type, action, metadata) in enumerate(items, start=1)
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
                    note="Created from project advisor chat.",
                    metadata_json={
                        "owner_type": task.owner_type,
                        "owner_id": task.owner_id,
                        "source_type": task.source_type,
                        "source_id": task.source_id,
                        "advisor_intent": intent,
                        "cockpit_phase": cockpit_phase,
                        "readiness_level": readiness_level,
                    },
                    created_by=created_by or "system",
                )
                for task in tasks
            ]
        )
        self.session.commit()
        for task in tasks:
            self.session.refresh(task)
        ArtifactGraphService(GraphService(self.session)).link_project_advisor_chat_tasks(
            chat, tasks
        )
        self.session.commit()
        return tasks

    def create_from_project_triage_comparison(
        self,
        comparison: dict,
        *,
        limit: int = 8,
        include_focus: bool = True,
        include_risks: bool = True,
        created_by: str = "system",
    ) -> list[ResearchTask]:
        limit = max(1, min(limit, 20))
        items = [
            ("triage_comparison_added_next_action", action)
            for action in self._unique_commitments(comparison.get("added_next_actions") or [])
        ]
        if include_risks:
            items.extend(
                ("triage_comparison_added_risk", risk)
                for risk in self._unique_commitments(comparison.get("added_risks") or [])
            )
        if include_focus:
            items.extend(
                ("triage_comparison_added_focus", focus)
                for focus in self._unique_commitments(comparison.get("added_focus") or [])
            )
        items = self._deduplicate_triage_items(items)[:limit]
        if not items:
            items = [
                (
                    "triage_comparison_review",
                    comparison.get("summary")
                    or "Review the latest project triage snapshot comparison.",
                )
            ]

        candidate_id = comparison.get("candidate_snapshot_id", "")
        baseline_id = comparison.get("baseline_snapshot_id", "")
        tasks = [
            ResearchTask(
                idea_id=None,
                owner_type="project_triage_comparison",
                owner_id=candidate_id or "project_triage_comparison",
                source_type=source_type,
                source_id=f"{source_type}_{idx}",
                title=self._triage_comparison_task_title(action, idx),
                description=action,
                priority=self._triage_comparison_task_priority(source_type, action),
                status="todo",
                due_phase="triage_change_follow_up",
                metadata_json={
                    "baseline_snapshot_id": baseline_id,
                    "candidate_snapshot_id": candidate_id,
                    "comparison_source_type": source_type,
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
                    note="Created from project triage snapshot comparison.",
                    metadata_json={
                        "owner_type": task.owner_type,
                        "owner_id": task.owner_id,
                        "source_type": task.source_type,
                        "source_id": task.source_id,
                        "baseline_snapshot_id": baseline_id,
                        "candidate_snapshot_id": candidate_id,
                    },
                    created_by=created_by or "system",
                )
                for task in tasks
            ]
        )
        self.session.commit()
        for task in tasks:
            self.session.refresh(task)
        ArtifactGraphService(GraphService(self.session)).link_project_triage_comparison_tasks(
            comparison, tasks
        )
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

    def _cockpit_task_title(self, action: str, idx: int, *, source_type: str) -> str:
        clean = " ".join(str(action).split())
        lower = clean.lower()
        if source_type == "cockpit_primary_action":
            return self._short_task_title(clean or "Work cockpit primary action", idx)
        if source_type == "cockpit_risk_alert":
            return self._short_task_title(f"Resolve cockpit risk {idx}: {clean}", idx)
        if "blocked" in lower:
            return self._short_task_title(clean.replace("Blocked", "Unblock", 1), idx)
        if "de-risk" in lower or "risk" in lower:
            return self._short_task_title(f"De-risk cockpit item {idx}: {clean}", idx)
        if source_type == "cockpit_highlight":
            return self._short_task_title(f"Review cockpit highlight {idx}: {clean}", idx)
        return self._short_task_title(clean or f"Work cockpit action {idx}", idx)

    def _cockpit_task_priority(self, source_type: str, action: str, phase: str) -> str:
        lower = str(action).lower()
        if source_type == "cockpit_risk_alert":
            return "critical"
        if "blocked" in lower or "critical" in lower or "high-risk" in lower:
            return "critical"
        if (
            "de-risk" in lower
            or "quality-gate" in lower
            or phase in {"validation", "unblock_execution"}
        ):
            return "high"
        if source_type == "cockpit_primary_action":
            return "high"
        if source_type == "cockpit_highlight":
            return "medium"
        return "medium"

    def _pilot_report_snapshot_task_title(
        self,
        action: str,
        idx: int,
        *,
        source_type: str,
    ) -> str:
        clean = " ".join(str(action).split())
        lower = clean.lower()
        if source_type == "pilot_report_risk":
            return self._short_task_title(f"Resolve pilot report risk {idx}: {clean}", idx)
        if source_type == "pilot_report_quick_action":
            return self._short_task_title(clean or f"Run pilot report quick action {idx}", idx)
        if "blocked" in lower:
            return self._short_task_title(clean.replace("Blocked", "Unblock", 1), idx)
        if "de-risk" in lower or "risk" in lower:
            return self._short_task_title(f"De-risk pilot report item {idx}: {clean}", idx)
        return self._short_task_title(clean or f"Work pilot report action {idx}", idx)

    def _pilot_report_snapshot_task_priority(
        self,
        source_type: str,
        action: str,
        report_status: str,
    ) -> str:
        lower = str(action).lower()
        if source_type == "pilot_report_risk":
            return "critical"
        if "blocked" in lower or "critical" in lower or "high-risk" in lower:
            return "critical"
        if (
            source_type == "pilot_report_next_action"
            or "de-risk" in lower
            or report_status in {"blocked_pilot", "at_risk_pilot"}
        ):
            return "high"
        if source_type == "pilot_report_quick_action":
            return "medium"
        return "medium"

    def _onboarding_task_title(self, item: dict, idx: int) -> str:
        check_id = str(item.get("id") or "")
        label = str(item.get("label") or "")
        if check_id == "profile":
            return "Complete research profile setup"
        if check_id == "paper_ingest":
            return "Upload first literature seed"
        if check_id == "workflow":
            return "Run first literature-to-ideas workflow"
        if check_id == "task_board":
            return "Seed onboarding task board"
        if check_id == "bundle_export":
            return "Prepare project handoff bundle"
        if check_id == "advisor_loop":
            return "Run first advisor action session"
        if check_id == "pilot_security":
            return "Enable pilot API key guard"
        if check_id == "mcp_bridge":
            return "Review MCP bridge setup"
        return self._short_task_title(label or f"Resolve onboarding check {idx}", idx)

    def _onboarding_task_description(self, item: dict) -> str:
        label = str(item.get("label") or "Onboarding check")
        detail = str(item.get("detail") or "").strip()
        action_label = str(item.get("action_label") or "").strip()
        action_path = str(item.get("action_path") or "").strip()
        parts = [label]
        if detail:
            parts.append(detail)
        if action_label and action_path:
            parts.append(f"Suggested action: {action_label} via {action_path}.")
        return " ".join(parts)

    def _onboarding_task_priority(self, item: dict) -> str:
        check_id = str(item.get("id") or "")
        required = bool(item.get("required", True))
        status = str(item.get("status") or "")
        if check_id in {"paper_ingest", "workflow", "task_board", "bundle_export"}:
            return "critical" if required else "high"
        if check_id == "profile":
            return "high"
        if check_id == "pilot_security":
            return "high"
        if status == "warning":
            return "medium"
        return "medium"

    def _advisor_chat_task_title(self, action: str, idx: int, *, source_type: str) -> str:
        clean = " ".join(str(action).split())
        lower = clean.lower()
        if source_type == "advisor_risk_alert":
            return self._short_task_title(f"Resolve advisor risk {idx}: {clean}", idx)
        if source_type == "advisor_tool_suggestion":
            return self._short_task_title(clean or f"Use advisor suggested tool {idx}", idx)
        if "blocked" in lower:
            return self._short_task_title(clean.replace("Blocked", "Unblock", 1), idx)
        if "de-risk" in lower or "risk" in lower:
            return self._short_task_title(f"De-risk advisor item {idx}: {clean}", idx)
        return self._short_task_title(clean or f"Work advisor recommendation {idx}", idx)

    def _advisor_chat_task_priority(self, source_type: str, action: str, intent: str) -> str:
        lower = str(action).lower()
        if source_type == "advisor_risk_alert":
            return "critical"
        if "blocked" in lower or "critical" in lower or "high-risk" in lower:
            return "critical"
        if (
            "de-risk" in lower
            or "claim validation" in lower
            or intent in {"risk_review", "evidence_review"}
        ):
            return "high"
        if source_type == "advisor_recommended_action":
            return "high"
        return "medium"

    def _triage_comparison_task_title(self, action: str, idx: int) -> str:
        clean = " ".join(str(action).split())
        if "risk" in clean.lower() or "de-risk" in clean.lower():
            return self._short_task_title(f"Resolve triage change risk {idx}: {clean}", idx)
        return self._short_task_title(clean or f"Review triage comparison change {idx}", idx)

    def _triage_comparison_task_priority(self, source_type: str, action: str) -> str:
        lower = str(action).lower()
        if source_type == "triage_comparison_added_risk":
            return "critical"
        if "blocked" in lower or "risk" in lower or "de-risk" in lower:
            return "critical"
        if source_type == "triage_comparison_added_next_action":
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

    def _ledger_task_title(self, action: str, idx: int, *, source_type: str) -> str:
        clean = " ".join(str(action).split())
        lower = clean.lower()
        if source_type == "claim":
            return self._short_task_title(f"Validate ledger claim {idx}: {clean}", idx)
        if source_type == "missing_evidence":
            return self._short_task_title(f"Collect missing evidence {idx}: {clean}", idx)
        if source_type == "counterevidence":
            return self._short_task_title(f"Resolve counterevidence {idx}: {clean}", idx)
        if source_type == "risk":
            if "evidence gaps remain open" in lower:
                return "Close evidence gaps"
            return self._short_task_title(f"De-risk evidence issue {idx}: {clean}", idx)
        return self._short_task_title(clean or f"Follow up evidence ledger item {idx}", idx)

    def _ledger_task_priority(self, signal: str, *, fallback: str) -> str:
        normalized = str(signal).lower()
        if normalized in {"critical", "high"}:
            return "critical" if normalized == "critical" else "high"
        if normalized in {"unsupported", "challenged"}:
            return "critical"
        if normalized in {"medium", "partially_supported"}:
            return "high"
        if normalized == "low":
            return "medium"
        return fallback

    def _claim_queue_task_title(self, action: str, item: dict, idx: int) -> str:
        claim_id = str(item.get("claim_id") or idx)
        claim = " ".join(str(item.get("claim") or "").split())
        clean_action = " ".join(str(action).split())
        if claim:
            return self._short_task_title(f"Validate claim {claim_id}: {claim}", idx)
        return self._short_task_title(
            f"Validate claim {claim_id}: {clean_action}",
            idx,
        )

    def _claim_queue_task_priority(self, priority: str) -> str:
        normalized = str(priority).lower()
        if normalized == "critical":
            return "critical"
        if normalized == "high":
            return "high"
        if normalized == "low":
            return "low"
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

    def _deduplicate_cockpit_items(
        self, items: list[tuple[str, str, dict]]
    ) -> list[tuple[str, str, dict]]:
        unique = []
        seen = set()
        for source_type, action, metadata in items:
            clean = " ".join(str(action).split())
            key = clean.lower()
            if clean and key not in seen:
                unique.append((source_type, clean, metadata))
                seen.add(key)
        return unique

    def _deduplicate_pilot_report_items(
        self, items: list[tuple[str, str, dict]]
    ) -> list[tuple[str, str, dict]]:
        unique = []
        seen = set()
        for source_type, action, metadata in items:
            clean = " ".join(str(action).split())
            key = clean.lower()
            if clean and key not in seen:
                unique.append((source_type, clean, metadata))
                seen.add(key)
        return unique

    def _deduplicate_advisor_chat_items(
        self, items: list[tuple[str, str, dict]]
    ) -> list[tuple[str, str, dict]]:
        unique = []
        seen = set()
        for source_type, action, metadata in items:
            clean = " ".join(str(action).split())
            key = clean.lower()
            if clean and key not in seen:
                unique.append((source_type, clean, metadata))
                seen.add(key)
        return unique

    def _deduplicate_onboarding_tasks(self, tasks: list[ResearchTask]) -> list[ResearchTask]:
        unique = []
        seen = set()
        for task in tasks:
            key = (task.owner_type, task.source_id, task.title.lower(), task.description.lower())
            if key not in seen:
                unique.append(task)
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

    def _deduplicate_evidence_ledger_tasks(self, tasks: list[ResearchTask]) -> list[ResearchTask]:
        unique = []
        seen = set()
        for task in tasks:
            key = (
                task.idea_id or "",
                task.owner_id,
                task.source_type,
                task.source_id,
                task.description.lower(),
            )
            if key not in seen:
                unique.append(task)
                seen.add(key)
        return unique

    def _deduplicate_claim_queue_tasks(self, tasks: list[ResearchTask]) -> list[ResearchTask]:
        unique = []
        seen = set()
        for task in tasks:
            key = (
                task.idea_id or "",
                task.owner_id,
                task.source_id,
                task.description.lower(),
            )
            if key not in seen:
                unique.append(task)
                seen.add(key)
        return unique
