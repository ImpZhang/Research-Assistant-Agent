from backend.research.models import (
    Evidence,
    ExperimentAnalysis,
    ExperimentPlan,
    ExperimentRun,
    Idea,
    IdeaAssumptionAudit,
    IdeaDecisionMemo,
    IdeaEvidenceLedger,
    NoveltyCheck,
    ProposalDraft,
    ProposalReview,
    ProposalRevision,
    ResearchBrief,
    ResearchPlanSnapshot,
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

    def link_experiment_analysis(
        self,
        run: ExperimentRun,
        analysis: ExperimentAnalysis,
        task: ResearchTask | None = None,
    ) -> None:
        idea_node = self._idea_node(analysis.idea_id)
        run_node = self.graph.get_or_create_node(
            node_type="experiment_run",
            label=run.title,
            canonical_key=run.id,
            payload={
                "status": run.status,
                "experiment_plan_id": run.experiment_plan_id,
                "task_id": run.task_id,
            },
        )
        analysis_node = self.graph.get_or_create_node(
            node_type="experiment_analysis",
            label=f"{analysis.decision} ({analysis.confidence:.2f})",
            canonical_key=analysis.id,
            payload={
                "decision": analysis.decision,
                "confidence": analysis.confidence,
                "experiment_run_id": analysis.experiment_run_id,
                "task_id": analysis.task_id,
            },
        )
        self.graph.create_edge(
            source_node=run_node,
            target_node=analysis_node,
            edge_type="experiment_run_has_analysis",
            payload={"source": "experiment_analysis"},
        )
        self.graph.create_edge(
            source_node=idea_node,
            target_node=analysis_node,
            edge_type="idea_has_experiment_analysis",
            payload={"source": "experiment_analysis"},
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
                target_node=analysis_node,
                edge_type="task_records_experiment_analysis",
                payload={"source": "experiment_analysis"},
            )

    def link_experiment_analysis_tasks(
        self,
        analysis: ExperimentAnalysis,
        tasks: list[ResearchTask],
    ) -> None:
        analysis_node = self.graph.get_or_create_node(
            node_type="experiment_analysis",
            label=f"{analysis.decision} ({analysis.confidence:.2f})",
            canonical_key=analysis.id,
            payload={
                "decision": analysis.decision,
                "confidence": analysis.confidence,
                "experiment_run_id": analysis.experiment_run_id,
            },
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
                source_node=analysis_node,
                target_node=task_node,
                edge_type="experiment_analysis_creates_task",
                payload={"source": "experiment_analysis_next_actions"},
            )

    def link_idea_decision_memo(self, memo: IdeaDecisionMemo) -> None:
        idea_node = self._idea_node(memo.idea_id)
        memo_node = self.graph.get_or_create_node(
            node_type="idea_decision_memo",
            label=f"{memo.decision}: {memo.id}",
            canonical_key=memo.id,
            payload={
                "decision": memo.decision,
                "source_artifacts": memo.source_artifacts_json or {},
            },
        )
        self.graph.create_edge(
            source_node=idea_node,
            target_node=memo_node,
            edge_type="idea_has_decision_memo",
            evidence_ids=memo.evidence_ids_json or [],
            payload={"source": "idea_decision_memo"},
        )

    def link_idea_decision_memo_tasks(
        self,
        memo: IdeaDecisionMemo,
        tasks: list[ResearchTask],
    ) -> None:
        memo_node = self.graph.get_or_create_node(
            node_type="idea_decision_memo",
            label=f"{memo.decision}: {memo.id}",
            canonical_key=memo.id,
            payload={"decision": memo.decision},
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
                source_node=memo_node,
                target_node=task_node,
                edge_type="decision_memo_creates_task",
                payload={"source": "idea_decision_memo_next_commitments"},
            )

    def link_research_plan_tasks(
        self,
        plan: ResearchPlanSnapshot,
        tasks: list[ResearchTask],
    ) -> None:
        plan_node = self.graph.get_or_create_node(
            node_type="research_plan",
            label=plan.title,
            canonical_key=plan.id,
            payload={
                "horizon_days": plan.horizon_days,
                "idea_ids": plan.idea_ids_json or [],
                "profile": (plan.profile_summary_json or {}).get("name", ""),
            },
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
                source_node=plan_node,
                target_node=task_node,
                edge_type="research_plan_creates_task",
                payload={"source": "research_plan_snapshot"},
            )

    def link_idea_readiness_tasks(
        self,
        idea: Idea,
        tasks: list[ResearchTask],
    ) -> None:
        idea_node = self._idea_node(idea.id)
        readiness_node = self.graph.get_or_create_node(
            node_type="idea_readiness",
            label=f"Readiness follow-up: {idea.title}",
            canonical_key=f"{idea.id}:readiness",
            payload={
                "idea_id": idea.id,
                "task_count": len(tasks),
            },
        )
        self.graph.create_edge(
            source_node=idea_node,
            target_node=readiness_node,
            edge_type="idea_has_readiness_assessment",
            payload={"source": "idea_readiness_task_generation"},
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
                source_node=readiness_node,
                target_node=task_node,
                edge_type="idea_readiness_creates_task",
                payload={"source": "idea_readiness_blocker"},
            )

    def link_idea_quality_gate_tasks(
        self,
        idea: Idea,
        tasks: list[ResearchTask],
    ) -> None:
        idea_node = self._idea_node(idea.id)
        quality_gate_node = self.graph.get_or_create_node(
            node_type="idea_quality_gate",
            label=f"Quality gate follow-up: {idea.title}",
            canonical_key=f"{idea.id}:quality_gate",
            payload={
                "idea_id": idea.id,
                "task_count": len(tasks),
            },
        )
        self.graph.create_edge(
            source_node=idea_node,
            target_node=quality_gate_node,
            edge_type="idea_has_quality_gate",
            payload={"source": "idea_quality_gate_task_generation"},
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
                source_node=quality_gate_node,
                target_node=task_node,
                edge_type="quality_gate_creates_task",
                payload={"source": "quality_gate_recommended_action"},
            )

    def link_project_triage_tasks(self, tasks: list[ResearchTask]) -> None:
        triage_node = self.graph.get_or_create_node(
            node_type="project_triage",
            label="Project triage brief",
            canonical_key="project_triage:latest",
            payload={
                "task_count": len(tasks),
                "owner_type": "project_triage",
            },
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
                source_node=triage_node,
                target_node=task_node,
                edge_type="project_triage_creates_task",
                payload={"source": task.source_type},
            )

    def link_project_cockpit_tasks(self, cockpit: dict, tasks: list[ResearchTask]) -> None:
        cockpit_node = self.graph.get_or_create_node(
            node_type="project_cockpit",
            label="Project cockpit",
            canonical_key="project_cockpit:latest",
            payload={
                "phase": cockpit.get("phase", ""),
                "readiness_level": cockpit.get("readiness_level", ""),
                "task_count": len(tasks),
                "owner_type": "project_cockpit",
            },
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
                source_node=cockpit_node,
                target_node=task_node,
                edge_type="project_cockpit_creates_task",
                payload={"source": task.source_type},
            )

    def link_project_pilot_report_snapshot_tasks(
        self,
        snapshot: ResearchBrief,
        tasks: list[ResearchTask],
    ) -> None:
        summary = snapshot.summary_json or {}
        snapshot_node = self.graph.get_or_create_node(
            node_type="project_pilot_report_snapshot",
            label=snapshot.title,
            canonical_key=snapshot.id,
            payload={
                "report_status": summary.get("report_status", ""),
                "readiness_level": summary.get("readiness_level", ""),
                "cockpit_phase": summary.get("cockpit_phase", ""),
                "task_count": len(tasks),
                "owner_type": "project_pilot_report_snapshot",
            },
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
                source_node=snapshot_node,
                target_node=task_node,
                edge_type="project_pilot_report_snapshot_creates_task",
                payload={"source": task.source_type},
            )

    def link_project_onboarding_tasks(
        self,
        readiness: dict,
        tasks: list[ResearchTask],
    ) -> None:
        onboarding_node = self.graph.get_or_create_node(
            node_type="project_onboarding",
            label="Project onboarding readiness",
            canonical_key="project_onboarding:latest",
            payload={
                "readiness_level": readiness.get("readiness_level", ""),
                "readiness_score": readiness.get("readiness_score", 0.0),
                "missing_required": readiness.get("missing_required", []),
                "task_count": len(tasks),
                "owner_type": "project_onboarding",
            },
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
                source_node=onboarding_node,
                target_node=task_node,
                edge_type="project_onboarding_creates_task",
                payload={"source": task.source_type},
            )

    def link_project_advisor_chat_tasks(self, chat: dict, tasks: list[ResearchTask]) -> None:
        chat_node = self.graph.get_or_create_node(
            node_type="project_advisor_chat",
            label=f"Advisor chat: {chat.get('intent', 'project_status')}",
            canonical_key="project_advisor_chat:latest",
            payload={
                "intent": chat.get("intent", ""),
                "question": chat.get("question", ""),
                "cockpit_phase": chat.get("cockpit_phase", ""),
                "readiness_level": chat.get("readiness_level", ""),
                "task_count": len(tasks),
                "owner_type": "project_advisor_chat",
            },
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
                source_node=chat_node,
                target_node=task_node,
                edge_type="project_advisor_chat_creates_task",
                payload={"source": task.source_type},
            )

    def link_project_triage_comparison_tasks(
        self,
        comparison: dict,
        tasks: list[ResearchTask],
    ) -> None:
        comparison_node = self.graph.get_or_create_node(
            node_type="project_triage_snapshot_comparison",
            label="Project triage snapshot comparison",
            canonical_key=(
                f"{comparison.get('baseline_snapshot_id', '')}:"
                f"{comparison.get('candidate_snapshot_id', '')}"
            ),
            payload={
                "baseline_snapshot_id": comparison.get("baseline_snapshot_id", ""),
                "candidate_snapshot_id": comparison.get("candidate_snapshot_id", ""),
                "task_count": len(tasks),
            },
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
                source_node=comparison_node,
                target_node=task_node,
                edge_type="project_triage_comparison_creates_task",
                payload={"source": task.source_type},
            )

    def link_opportunity_radar_tasks(self, tasks: list[ResearchTask]) -> None:
        tasks_by_idea: dict[str, list[ResearchTask]] = {}
        for task in tasks:
            if task.idea_id:
                tasks_by_idea.setdefault(task.idea_id, []).append(task)

        for idea_id, idea_tasks in tasks_by_idea.items():
            idea_node = self._idea_node(idea_id)
            radar_node = self.graph.get_or_create_node(
                node_type="opportunity_radar",
                label=f"Opportunity radar: {idea_id}",
                canonical_key=f"{idea_id}:opportunity_radar",
                payload={
                    "idea_id": idea_id,
                    "task_count": len(idea_tasks),
                    "owner_type": "opportunity_radar",
                },
            )
            self.graph.create_edge(
                source_node=idea_node,
                target_node=radar_node,
                edge_type="idea_has_opportunity_radar",
                payload={"source": "opportunity_radar_task_generation"},
            )
            for task in idea_tasks:
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
                    source_node=radar_node,
                    target_node=task_node,
                    edge_type="opportunity_radar_creates_task",
                    payload={"source": "opportunity_radar_next_action"},
                )

    def link_novelty_check_tasks(
        self,
        check: NoveltyCheck,
        tasks: list[ResearchTask],
    ) -> None:
        idea_node = self._idea_node(check.idea_id)
        novelty_node = self.graph.get_or_create_node(
            node_type="novelty_check",
            label=f"Novelty check: {check.risk_level}",
            canonical_key=check.id,
            payload={
                "idea_id": check.idea_id,
                "status": check.status,
                "risk_level": check.risk_level,
                "local_overlap_score": check.local_overlap_score,
                "external_overlap_score": check.external_overlap_score,
            },
        )
        self.graph.create_edge(
            source_node=idea_node,
            target_node=novelty_node,
            edge_type="idea_has_novelty_check",
            payload={"source": "novelty_task_generation"},
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
                source_node=novelty_node,
                target_node=task_node,
                edge_type="novelty_check_creates_task",
                payload={"source": "novelty_recommended_action"},
            )

    def link_idea_assumption_audit(self, audit: IdeaAssumptionAudit) -> None:
        idea_node = self._idea_node(audit.idea_id)
        audit_node = self.graph.get_or_create_node(
            node_type="idea_assumption_audit",
            label=f"Assumption audit {audit.id}",
            canonical_key=audit.id,
            payload={
                "status": audit.status,
                "assumption_count": len(audit.assumptions_json or []),
                "source_artifacts": audit.source_artifacts_json or {},
            },
        )
        self.graph.create_edge(
            source_node=idea_node,
            target_node=audit_node,
            edge_type="idea_has_assumption_audit",
            payload={"source": "idea_assumption_audit"},
        )

    def link_idea_evidence_ledger(self, ledger: IdeaEvidenceLedger) -> None:
        idea_node = self._idea_node(ledger.idea_id)
        ledger_node = self.graph.get_or_create_node(
            node_type="idea_evidence_ledger",
            label=f"Evidence ledger {ledger.id}",
            canonical_key=ledger.id,
            payload={
                "idea_id": ledger.idea_id,
                "coverage_score": ledger.coverage_score,
                "summary": ledger.summary_json or {},
            },
        )
        evidence_ids = [
            str(evidence_id)
            for evidence_id in (ledger.source_artifacts_json or {}).get("evidence_ids", [])
        ]
        self.graph.create_edge(
            source_node=idea_node,
            target_node=ledger_node,
            edge_type="idea_has_evidence_ledger",
            evidence_ids=evidence_ids,
            payload={"source": "idea_evidence_ledger"},
        )

        evidence_nodes = self._evidence_nodes(evidence_ids)
        for claim in ledger.claims_json or []:
            claim_id = str(claim.get("claim_id") or "")
            claim_node = self.graph.get_or_create_node(
                node_type="claim",
                label=str(claim.get("claim") or claim_id),
                canonical_key=f"{ledger.id}:{claim_id}",
                payload={
                    "idea_id": ledger.idea_id,
                    "ledger_id": ledger.id,
                    "claim_type": claim.get("claim_type", ""),
                    "support_level": claim.get("support_level", ""),
                },
            )
            self.graph.create_edge(
                source_node=ledger_node,
                target_node=claim_node,
                edge_type="evidence_ledger_tracks_claim",
                evidence_ids=claim.get("supporting_evidence_ids") or [],
                payload={"source": "idea_evidence_ledger"},
            )
            for evidence_id in claim.get("supporting_evidence_ids") or []:
                evidence_node = evidence_nodes.get(str(evidence_id))
                if evidence_node is None:
                    continue
                self.graph.create_edge(
                    source_node=evidence_node,
                    target_node=claim_node,
                    edge_type="evidence_supports_claim",
                    evidence_ids=[str(evidence_id)],
                    payload={"source": "idea_evidence_ledger"},
                )

    def link_idea_evidence_ledger_tasks(
        self,
        ledger: IdeaEvidenceLedger,
        tasks: list[ResearchTask],
    ) -> None:
        ledger_node = self.graph.get_or_create_node(
            node_type="idea_evidence_ledger",
            label=f"Evidence ledger {ledger.id}",
            canonical_key=ledger.id,
            payload={
                "idea_id": ledger.idea_id,
                "coverage_score": ledger.coverage_score,
                "summary": ledger.summary_json or {},
            },
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
                source_node=ledger_node,
                target_node=task_node,
                edge_type="evidence_ledger_creates_task",
                payload={"source": "idea_evidence_ledger_follow_up"},
            )

    def link_claim_validation_queue_tasks(self, tasks: list[ResearchTask]) -> None:
        tasks_by_idea: dict[str, list[ResearchTask]] = {}
        for task in tasks:
            if task.idea_id:
                tasks_by_idea.setdefault(task.idea_id, []).append(task)

        for idea_id, idea_tasks in tasks_by_idea.items():
            idea_node = self._idea_node(idea_id)
            queue_node = self.graph.get_or_create_node(
                node_type="claim_validation_queue",
                label=f"Claim validation queue: {idea_id}",
                canonical_key=f"{idea_id}:claim_validation_queue",
                payload={
                    "idea_id": idea_id,
                    "task_count": len(idea_tasks),
                    "owner_type": "claim_validation_queue",
                },
            )
            self.graph.create_edge(
                source_node=idea_node,
                target_node=queue_node,
                edge_type="idea_has_claim_validation_queue",
                payload={"source": "claim_validation_queue_task_generation"},
            )
            for task in idea_tasks:
                metadata = task.metadata_json or {}
                claim_key = task.source_id or (
                    f"{metadata.get('ledger_id', '')}:{metadata.get('claim_id', '')}"
                )
                claim_node = self.graph.get_or_create_node(
                    node_type="claim",
                    label=str(metadata.get("claim") or metadata.get("claim_id") or claim_key),
                    canonical_key=claim_key,
                    payload={
                        "idea_id": idea_id,
                        "ledger_id": metadata.get("ledger_id", ""),
                        "claim_id": metadata.get("claim_id", ""),
                        "support_level": metadata.get("support_level", ""),
                        "urgency_score": metadata.get("urgency_score", 0.0),
                    },
                )
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
                    source_node=queue_node,
                    target_node=claim_node,
                    edge_type="claim_validation_queue_prioritizes_claim",
                    payload={"source": "claim_validation_queue"},
                )
                self.graph.create_edge(
                    source_node=queue_node,
                    target_node=task_node,
                    edge_type="claim_validation_queue_creates_task",
                    payload={"source": "claim_validation_queue_follow_up"},
                )

    def _evidence_nodes(self, evidence_ids: list[str]) -> dict[str, object]:
        if not evidence_ids:
            return {}
        evidences = (
            self.graph.session.query(Evidence)
            .filter(Evidence.id.in_(evidence_ids))
            .limit(200)
            .all()
        )
        nodes = {}
        for evidence in evidences:
            nodes[evidence.id] = self.graph.get_or_create_node(
                node_type="evidence",
                label=evidence.summary or evidence.supports or evidence.id,
                canonical_key=evidence.id,
                payload={
                    "paper_id": evidence.paper_id,
                    "evidence_type": evidence.evidence_type,
                    "confidence": evidence.confidence,
                },
            )
        return nodes

    def _idea_node(self, idea_id: str):
        return self.graph.get_or_create_node(
            node_type="idea",
            label=f"Idea {idea_id}",
            canonical_key=idea_id,
        )
