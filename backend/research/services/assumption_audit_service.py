from sqlalchemy.orm import Session

from backend.research.models import (
    ExperimentAnalysis,
    ExperimentPlan,
    Idea,
    IdeaAssumptionAudit,
    NoveltyCheck,
    ProposalReview,
    RelatedWorkMatrix,
)
from backend.research.services.artifact_graph_service import ArtifactGraphService
from backend.research.services.graph_service import GraphService


class IdeaAssumptionAuditService:
    def __init__(self, session: Session):
        self.session = session

    def create_audit(
        self,
        idea_id: str,
        *,
        assumptions: list[dict] | None = None,
        created_by: str = "system",
    ) -> IdeaAssumptionAudit:
        idea = self.session.get(Idea, idea_id)
        if idea is None:
            raise ValueError("Idea not found")

        plan = self._latest(ExperimentPlan, idea.id)
        novelty_check = self._latest(NoveltyCheck, idea.id)
        proposal_review = self._latest(ProposalReview, idea.id)
        analysis = self._latest(ExperimentAnalysis, idea.id)
        matrix = self._latest(RelatedWorkMatrix, idea.id)
        source_artifacts = {
            "latest_experiment_plan_id": plan.id if plan else "",
            "latest_novelty_check_id": novelty_check.id if novelty_check else "",
            "latest_proposal_review_id": proposal_review.id if proposal_review else "",
            "latest_experiment_analysis_id": analysis.id if analysis else "",
            "latest_related_work_matrix_id": matrix.id if matrix else "",
        }
        audit = IdeaAssumptionAudit(
            idea_id=idea.id,
            status="completed",
            assumptions_json=self._normalize_assumptions(assumptions)
            or self._default_assumptions(
                idea,
                plan=plan,
                novelty_check=novelty_check,
                proposal_review=proposal_review,
                analysis=analysis,
                matrix=matrix,
            ),
            source_artifacts_json=source_artifacts,
            created_by=created_by or "system",
        )
        self.session.add(audit)
        self.session.flush()
        audit.markdown_export = self._render_markdown(audit, idea)
        self.session.commit()
        self.session.refresh(audit)
        ArtifactGraphService(GraphService(self.session)).link_idea_assumption_audit(audit)
        self.session.commit()
        self.session.refresh(audit)
        return audit

    def list_for_idea(self, idea_id: str, limit: int = 20) -> list[IdeaAssumptionAudit]:
        if self.session.get(Idea, idea_id) is None:
            raise ValueError("Idea not found")
        limit = max(1, min(limit, 100))
        return (
            self.session.query(IdeaAssumptionAudit)
            .filter(IdeaAssumptionAudit.idea_id == idea_id)
            .order_by(IdeaAssumptionAudit.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_audit(self, idea_id: str, audit_id: str) -> IdeaAssumptionAudit | None:
        return (
            self.session.query(IdeaAssumptionAudit)
            .filter(IdeaAssumptionAudit.id == audit_id, IdeaAssumptionAudit.idea_id == idea_id)
            .first()
        )

    def _latest(self, model, idea_id: str):
        return (
            self.session.query(model)
            .filter(model.idea_id == idea_id)
            .order_by(model.created_at.desc())
            .first()
        )

    def _default_assumptions(
        self,
        idea: Idea,
        *,
        plan: ExperimentPlan | None,
        novelty_check: NoveltyCheck | None,
        proposal_review: ProposalReview | None,
        analysis: ExperimentAnalysis | None,
        matrix: RelatedWorkMatrix | None,
    ) -> list[dict]:
        main_experiment = plan.main_experiment_json if plan else {}
        success_signal = self._clean(
            str(main_experiment.get("success_criterion") or "A measurable MVP result")
        )
        assumptions = [
            {
                "assumption": self._clean(idea.core_hypothesis)
                or "The core hypothesis can be falsified with an MVP experiment.",
                "why_it_matters": "If this is false, the research question needs to be reframed.",
                "validation_signal": success_signal,
                "risk_level": self._risk_from_review(proposal_review),
                "status": "untested" if not analysis else "partially_tested",
                "source": "core_hypothesis",
            },
            {
                "assumption": "The idea is sufficiently differentiated from nearest related work.",
                "why_it_matters": "Weak differentiation turns a plausible idea into an incremental variant.",
                "validation_signal": self._novelty_signal(novelty_check, matrix),
                "risk_level": novelty_check.risk_level if novelty_check else "medium",
                "status": "needs_search" if matrix is None else "screened",
                "source": "novelty_check",
            },
            {
                "assumption": "The available evidence is enough to justify the first experiment.",
                "why_it_matters": "Thin evidence leads to experiments that cannot support a publishable claim.",
                "validation_signal": f"{len(idea.evidence_ids_json or [])} linked evidence records.",
                "risk_level": "high" if len(idea.evidence_ids_json or []) < 2 else "medium",
                "status": "needs_more_evidence"
                if len(idea.evidence_ids_json or []) < 2
                else "supported",
                "source": "evidence_ids",
            },
            {
                "assumption": "The evaluation setup can distinguish real improvement from noise.",
                "why_it_matters": "A vague metric or missing baseline makes the idea hard to defend.",
                "validation_signal": self._evaluation_signal(idea, plan),
                "risk_level": "medium",
                "status": "planned" if plan else "unplanned",
                "source": "experiment_plan",
            },
            {
                "assumption": "The project fits the available resource budget.",
                "why_it_matters": "A strong idea can still fail if compute, data, or time are unrealistic.",
                "validation_signal": self._clean(idea.resource_requirements)
                or "Resource requirements need an explicit estimate.",
                "risk_level": "medium",
                "status": "needs_estimate" if not idea.resource_requirements else "estimated",
                "source": "resource_requirements",
            },
        ]
        for idx, risk in enumerate(idea.risks_json or [], start=1):
            assumptions.append(
                {
                    "assumption": str(risk),
                    "why_it_matters": "This risk can invalidate the path from idea to publishable result.",
                    "validation_signal": "Turn this risk into a concrete check or ablation.",
                    "risk_level": "medium",
                    "status": "open",
                    "source": f"idea_risk_{idx}",
                }
            )
        return self._normalize_assumptions(assumptions)

    def _normalize_assumptions(self, assumptions: list[dict] | None) -> list[dict]:
        if not assumptions:
            return []
        normalized = []
        for idx, item in enumerate(assumptions, start=1):
            normalized.append(
                {
                    "assumption": self._clean(str(item.get("assumption") or f"Assumption {idx}")),
                    "why_it_matters": self._clean(str(item.get("why_it_matters") or "")),
                    "validation_signal": self._clean(str(item.get("validation_signal") or "")),
                    "risk_level": self._clean(str(item.get("risk_level") or "medium")),
                    "status": self._clean(str(item.get("status") or "untested")),
                    "source": self._clean(str(item.get("source") or "manual")),
                }
            )
        return normalized

    def _render_markdown(self, audit: IdeaAssumptionAudit, idea: Idea) -> str:
        lines = [
            f"# Idea Assumption Audit: {idea.title}",
            "",
            f"- Audit ID: `{audit.id}`",
            f"- Idea ID: `{idea.id}`",
            f"- Status: `{audit.status}`",
            f"- Created By: {audit.created_by}",
            "",
            "## Source Artifacts",
            "",
        ]
        for key, value in (audit.source_artifacts_json or {}).items():
            lines.append(f"- {key}: `{value}`")
        lines.extend(["", "## Assumptions", ""])
        for idx, item in enumerate(audit.assumptions_json or [], start=1):
            lines.extend(
                [
                    f"### A{idx}. {item.get('assumption', '')}",
                    "",
                    f"- Why It Matters: {item.get('why_it_matters', '')}",
                    f"- Validation Signal: {item.get('validation_signal', '')}",
                    f"- Risk Level: `{item.get('risk_level', 'medium')}`",
                    f"- Status: `{item.get('status', 'untested')}`",
                    f"- Source: `{item.get('source', 'unknown')}`",
                    "",
                ]
            )
        return "\n".join(lines).strip() + "\n"

    def _risk_from_review(self, proposal_review: ProposalReview | None) -> str:
        if proposal_review is None:
            return "medium"
        if proposal_review.readiness_score < 0.45:
            return "high"
        if proposal_review.readiness_score >= 0.75:
            return "low"
        return "medium"

    def _novelty_signal(
        self,
        novelty_check: NoveltyCheck | None,
        matrix: RelatedWorkMatrix | None,
    ) -> str:
        parts = []
        if novelty_check:
            parts.append(novelty_check.summary)
        if matrix:
            parts.append(
                f"{len(matrix.items_json or [])} related-work rows and "
                f"{len(matrix.missing_searches_json or [])} missing searches."
            )
        if not parts:
            parts.append("Run novelty screening and build a related-work matrix.")
        return self._clean(" ".join(parts))

    def _evaluation_signal(self, idea: Idea, plan: ExperimentPlan | None) -> str:
        if plan:
            metrics = ", ".join(str(item) for item in (plan.metrics_json or [])[:4])
            baselines = ", ".join(str(item) for item in (plan.baselines_json or [])[:4])
            return self._clean(
                f"Metrics: {metrics or 'not specified'}; baselines: {baselines or 'not specified'}."
            )
        metrics = ", ".join(str(item) for item in (idea.metrics_json or [])[:4])
        baselines = ", ".join(str(item) for item in (idea.baselines_json or [])[:4])
        return self._clean(
            f"Metrics: {metrics or 'not specified'}; baselines: {baselines or 'not specified'}."
        )

    def _clean(self, text: str) -> str:
        return " ".join((text or "").split())
