from collections import Counter

from sqlalchemy.orm import Session

from backend.research.models import (
    ExperimentAnalysis,
    Idea,
    IdeaDecisionMemo,
    IdeaEvidenceLedger,
    ProposalReview,
    ResearchBrief,
    ResearchPlanSnapshot,
    ResearchProfile,
    ResearchTask,
)
from backend.research.services.triage_snapshot_service import ProjectTriageSnapshotService


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
        evidence_signals = self._load_evidence_signals([idea.id for idea in ideas])
        claim_queue_signals = self._load_claim_queue_signals([idea.id for idea in ideas])
        triage_signals = self._load_triage_signals([idea.id for idea in ideas])
        triage_snapshot_comparison = self._load_triage_snapshot_comparison()
        summary = self._summary(
            ideas,
            tasks,
            analyses,
            profile,
            plan_summaries,
            readiness_signals,
            evidence_signals,
            claim_queue_signals,
            triage_signals,
            triage_snapshot_comparison,
        )
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
            evidence_signals,
            claim_queue_signals,
            triage_signals,
            triage_snapshot_comparison,
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

    def _load_evidence_signals(self, idea_ids: list[str]) -> list[dict]:
        if not idea_ids:
            return []
        ledgers = (
            self.session.query(IdeaEvidenceLedger)
            .filter(IdeaEvidenceLedger.idea_id.in_(idea_ids))
            .order_by(IdeaEvidenceLedger.created_at.desc())
            .limit(200)
            .all()
        )
        latest_ledger_by_idea = _first_by_idea(ledgers)
        signals = []
        for idea_id in idea_ids:
            ledger = latest_ledger_by_idea.get(idea_id)
            summary = (ledger.summary_json or {}) if ledger else {}
            signals.append(
                {
                    "idea_id": idea_id,
                    "ledger_id": ledger.id if ledger else "",
                    "coverage_score": ledger.coverage_score if ledger else 0.0,
                    "decision_hint": summary.get("decision_hint", ""),
                    "claim_count": summary.get("claim_count", 0),
                    "unsupported_claim_count": summary.get("unsupported_claim_count", 0),
                    "missing_evidence_count": summary.get("missing_evidence_count", 0),
                    "high_risk_count": summary.get("high_risk_count", 0),
                }
            )
        return signals

    def _load_claim_queue_signals(self, idea_ids: list[str]) -> dict:
        if not idea_ids:
            return {"items": [], "summary": {"item_count": 0}}
        ledgers = (
            self.session.query(IdeaEvidenceLedger)
            .filter(IdeaEvidenceLedger.idea_id.in_(idea_ids))
            .order_by(IdeaEvidenceLedger.created_at.desc())
            .limit(200)
            .all()
        )
        latest_ledger_by_idea = _first_by_idea(ledgers)
        ledger_ids = [ledger.id for ledger in latest_ledger_by_idea.values()]
        tasks = (
            self.session.query(ResearchTask)
            .filter(
                ResearchTask.owner_type == "idea_evidence_ledger",
                ResearchTask.owner_id.in_(ledger_ids),
            )
            .order_by(ResearchTask.created_at.desc())
            .limit(300)
            .all()
            if ledger_ids
            else []
        )
        tasks_by_ledger: dict[str, list[ResearchTask]] = {ledger_id: [] for ledger_id in ledger_ids}
        for task in tasks:
            tasks_by_ledger.setdefault(task.owner_id, []).append(task)

        items = []
        for idea_id in idea_ids:
            ledger = latest_ledger_by_idea.get(idea_id)
            if ledger is None:
                continue
            for claim in ledger.claims_json or []:
                item = self._claim_queue_item(
                    idea_id=idea_id,
                    ledger=ledger,
                    claim=claim,
                    tasks=tasks_by_ledger.get(ledger.id, []),
                )
                items.append(item)
        items = sorted(items, key=lambda item: (-item["urgency_score"], item["claim_id"]))[:10]
        priorities = Counter(item["priority"] for item in items)
        return {
            "items": items,
            "summary": {
                "item_count": len(items),
                "critical_count": priorities.get("critical", 0),
                "high_count": priorities.get("high", 0),
                "by_priority": dict(priorities),
            },
        }

    def _claim_queue_item(
        self,
        *,
        idea_id: str,
        ledger: IdeaEvidenceLedger,
        claim: dict,
        tasks: list[ResearchTask],
    ) -> dict:
        claim_id = str(claim.get("claim_id") or "")
        support_ids = claim.get("supporting_evidence_ids") or []
        related_tasks = [
            task
            for task in tasks
            if task.source_id == claim_id
            or str((task.metadata_json or {}).get("claim_id") or "") == claim_id
            or str(((task.metadata_json or {}).get("ledger_item") or {}).get("source_id") or "")
            == claim_id
        ]
        missing_evidence = [
            item
            for item in ledger.missing_evidence_json or []
            if str(item.get("source_id") or "") == claim_id
        ]
        if not support_ids and not missing_evidence:
            missing_evidence = [{"gap": f"No direct evidence is linked to claim {claim_id}."}]
        counter_count = len(claim.get("challenge_signals") or [])
        if claim.get("support_level") in {"unsupported", "partially_supported", "challenged"}:
            counter_count += len(ledger.counterevidence_json or [])
        urgency_score = _claim_queue_urgency_score(
            support_level=str(claim.get("support_level") or ""),
            supporting_evidence_count=len(support_ids),
            missing_evidence_count=len(missing_evidence),
            counterevidence_count=counter_count,
            related_task_count=len(
                [task for task in related_tasks if task.status in {"todo", "doing", "blocked"}]
            ),
        )
        priority = _claim_queue_priority(urgency_score)
        open_tasks = [task for task in related_tasks if task.status in {"todo", "doing", "blocked"}]
        recommended_action = (
            f"Work linked task `{open_tasks[0].id}`: {open_tasks[0].title}"
            if open_tasks
            else str(claim.get("next_validation") or "Validate this claim against evidence.")
        )
        return {
            "idea_id": idea_id,
            "ledger_id": ledger.id,
            "claim_id": claim_id,
            "claim": str(claim.get("claim") or ""),
            "claim_type": str(claim.get("claim_type") or ""),
            "support_level": str(claim.get("support_level") or ""),
            "priority": priority,
            "urgency_score": urgency_score,
            "supporting_evidence_count": len(support_ids),
            "missing_evidence_count": len(missing_evidence),
            "counterevidence_count": counter_count,
            "related_task_count": len(related_tasks),
            "recommended_action": recommended_action,
        }

    def _load_triage_signals(self, idea_ids: list[str]) -> dict:
        triage_owner_types = {
            "project_triage",
            "project_triage_comparison",
            "idea_quality_gate",
            "opportunity_radar",
            "idea_readiness",
        }
        tasks = (
            self.session.query(ResearchTask)
            .filter(ResearchTask.owner_type.in_(triage_owner_types))
            .order_by(ResearchTask.created_at.desc())
            .limit(300)
            .all()
        )
        idea_id_set = set(idea_ids)
        scoped_tasks = [
            task
            for task in tasks
            if task.idea_id is None or not idea_id_set or task.idea_id in idea_id_set
        ]
        open_tasks = [task for task in scoped_tasks if task.status in {"todo", "doing", "blocked"}]
        by_owner_type = Counter(task.owner_type for task in scoped_tasks)
        by_source_type = Counter(task.source_type for task in scoped_tasks)
        top_tasks = sorted(open_tasks, key=self._task_order)[:8]
        return {
            "task_count": len(scoped_tasks),
            "open_task_count": len(open_tasks),
            "project_triage_task_count": by_owner_type.get("project_triage", 0),
            "comparison_task_count": by_owner_type.get("project_triage_comparison", 0),
            "quality_gate_task_count": by_owner_type.get("idea_quality_gate", 0),
            "opportunity_task_count": by_owner_type.get("opportunity_radar", 0),
            "readiness_task_count": by_owner_type.get("idea_readiness", 0),
            "risk_focus_count": by_source_type.get("triage_risk_focus", 0),
            "top_tasks": [
                {
                    "id": task.id,
                    "idea_id": task.idea_id,
                    "owner_type": task.owner_type,
                    "source_type": task.source_type,
                    "title": task.title,
                    "priority": task.priority,
                    "status": task.status,
                }
                for task in top_tasks
            ],
        }

    def _load_triage_snapshot_comparison(self) -> dict:
        service = ProjectTriageSnapshotService(self.session)
        snapshots = service.list_snapshots(limit=2)
        if len(snapshots) < 2:
            return {}
        comparison = service.compare_snapshots(snapshots[1].id, snapshots[0].id)
        return {key: value for key, value in comparison.items() if key != "markdown_export"}

    def _summary(
        self,
        ideas: list[Idea],
        tasks: list[ResearchTask],
        analyses: list[ExperimentAnalysis],
        profile: ResearchProfile | None,
        plan_summaries: list[dict],
        readiness_signals: list[dict],
        evidence_signals: list[dict],
        claim_queue_signals: dict,
        triage_signals: dict,
        triage_snapshot_comparison: dict,
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
            "evidence_signals": evidence_signals,
            "claim_validation_queue": claim_queue_signals,
            "triage_signals": triage_signals,
            "triage_snapshot_comparison": triage_snapshot_comparison,
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
        evidence_signals: list[dict],
        claim_queue_signals: dict,
        triage_signals: dict,
        triage_snapshot_comparison: dict,
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

        lines.extend(["", "## Evidence Signals", ""])
        if evidence_signals:
            for signal in evidence_signals:
                lines.append(
                    f"- idea=`{signal['idea_id']}` ledger=`{signal['ledger_id'] or 'none'}` "
                    f"coverage={signal['coverage_score']:.2f} "
                    f"hint=`{signal['decision_hint'] or 'none'}` "
                    f"unsupported={signal['unsupported_claim_count']} "
                    f"missing={signal['missing_evidence_count']} "
                    f"high_risk={signal['high_risk_count']}"
                )
        else:
            lines.append("- No evidence ledger signals recorded.")

        lines.extend(["", "## Claim Validation Queue", ""])
        queue_items = claim_queue_signals.get("items") or []
        if queue_items:
            for item in queue_items[:8]:
                lines.append(
                    f"- `{item['priority']}` score={item['urgency_score']} "
                    f"idea=`{item['idea_id']}` ledger=`{item['ledger_id']}` "
                    f"claim=`{item['claim_id']}` support=`{item['support_level']}`: "
                    f"{item['claim']}"
                )
                lines.append(f"  - action: {item['recommended_action']}")
        else:
            lines.append("- No claim validation queue items available.")

        lines.extend(["", "## Triage Signals", ""])
        if triage_signals.get("task_count", 0):
            lines.extend(
                [
                    f"- Project Triage Tasks: {triage_signals.get('project_triage_task_count', 0)}",
                    f"- Triage Comparison Tasks: {triage_signals.get('comparison_task_count', 0)}",
                    f"- Quality Gate Tasks: {triage_signals.get('quality_gate_task_count', 0)}",
                    f"- Opportunity Tasks: {triage_signals.get('opportunity_task_count', 0)}",
                    f"- Readiness Tasks: {triage_signals.get('readiness_task_count', 0)}",
                    f"- Risk Focus Items: {triage_signals.get('risk_focus_count', 0)}",
                    "",
                    "### Top Triage Tasks",
                    "",
                ]
            )
            top_tasks = triage_signals.get("top_tasks") or []
            if top_tasks:
                for task in top_tasks:
                    lines.append(
                        f"- `{task['id']}` `{task['priority']}` `{task['status']}` "
                        f"`{task['owner_type']}` idea=`{task['idea_id'] or 'project'}` "
                        f"{task['title']}"
                    )
            else:
                lines.append("- No open triage tasks.")
        else:
            lines.append("- No triage task signals recorded.")

        lines.extend(["", "## Triage Snapshot Changes", ""])
        if triage_snapshot_comparison:
            lines.extend(
                [
                    f"- Baseline: `{triage_snapshot_comparison['baseline_snapshot_id']}` "
                    f"{triage_snapshot_comparison['baseline_title']}",
                    f"- Candidate: `{triage_snapshot_comparison['candidate_snapshot_id']}` "
                    f"{triage_snapshot_comparison['candidate_title']}",
                    f"- Summary: {triage_snapshot_comparison['summary']}",
                    "",
                    "### Metric Delta",
                    "",
                ]
            )
            for key, value in (triage_snapshot_comparison.get("metric_delta") or {}).items():
                lines.append(f"- {key}: {value}")
            lines.extend(["", "### Added Focus", ""])
            _append_brief_change_items(
                lines,
                triage_snapshot_comparison.get("added_focus") or [],
            )
            lines.extend(["", "### Added Risks", ""])
            _append_brief_change_items(
                lines,
                triage_snapshot_comparison.get("added_risks") or [],
            )
            lines.extend(["", "### Added Next Actions", ""])
            _append_brief_change_items(
                lines,
                triage_snapshot_comparison.get("added_next_actions") or [],
            )
        else:
            lines.append("- No saved triage snapshot comparison available.")

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


def _claim_queue_urgency_score(
    *,
    support_level: str,
    supporting_evidence_count: int,
    missing_evidence_count: int,
    counterevidence_count: int,
    related_task_count: int,
) -> float:
    base = {
        "challenged": 0.95,
        "unsupported": 0.9,
        "partially_supported": 0.7,
        "supported": 0.35,
    }.get(support_level, 0.55)
    score = (
        base
        + min(missing_evidence_count, 4) * 0.08
        + min(counterevidence_count, 4) * 0.06
        + min(related_task_count, 4) * 0.03
        - min(supporting_evidence_count, 4) * 0.04
    )
    return round(max(0.0, min(1.0, score)), 4)


def _claim_queue_priority(urgency_score: float) -> str:
    if urgency_score >= 0.85:
        return "critical"
    if urgency_score >= 0.65:
        return "high"
    if urgency_score >= 0.4:
        return "medium"
    return "low"


def _append_brief_change_items(lines: list[str], items: list[str]) -> None:
    if not items:
        lines.append("- none")
        return
    lines.extend(f"- {item}" for item in items[:8])


def _first_by_idea(records: list) -> dict[str, object]:
    by_idea = {}
    for record in records:
        if record.idea_id not in by_idea:
            by_idea[record.idea_id] = record
    return by_idea
