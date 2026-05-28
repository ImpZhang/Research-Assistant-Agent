from sqlalchemy.orm import Session

from backend.research.models import ProposalDraft, ProposalReview, RelatedWorkMatrix
from backend.research.services.artifact_graph_service import ArtifactGraphService
from backend.research.services.graph_service import GraphService


class ProposalReviewService:
    def __init__(self, session: Session):
        self.session = session

    def create_review(
        self,
        proposal_draft_id: str,
        *,
        reviewer_type: str = "advisor",
        created_by: str = "system",
    ) -> ProposalReview:
        draft = self.session.get(ProposalDraft, proposal_draft_id)
        if draft is None:
            raise ValueError("Proposal draft not found")

        matrix = (
            self.session.get(RelatedWorkMatrix, draft.related_work_matrix_id)
            if draft.related_work_matrix_id
            else None
        )
        strengths = self._strengths(draft, matrix)
        concerns = self._concerns(draft, matrix)
        required_revisions = self._required_revisions(draft, matrix)
        missing_evidence = self._missing_evidence(draft, matrix)
        readiness_score = self._readiness_score(draft, matrix)
        decision = self._decision(readiness_score, concerns)
        summary = self._summary(decision, readiness_score, strengths, concerns)

        review = ProposalReview(
            proposal_draft_id=draft.id,
            idea_id=draft.idea_id,
            reviewer_type=reviewer_type or "advisor",
            decision=decision,
            readiness_score=readiness_score,
            strengths_json=strengths,
            concerns_json=concerns,
            required_revisions_json=required_revisions,
            missing_evidence_json=missing_evidence,
            summary=summary,
            created_by=created_by or "system",
        )
        review.markdown_export = self._render_markdown(review)
        self.session.add(review)
        self.session.commit()
        self.session.refresh(review)
        ArtifactGraphService(GraphService(self.session)).link_proposal_review(review)
        self.session.commit()
        return review

    def list_for_draft(self, proposal_draft_id: str, limit: int = 20) -> list[ProposalReview]:
        if self.session.get(ProposalDraft, proposal_draft_id) is None:
            raise ValueError("Proposal draft not found")
        limit = max(1, min(limit, 100))
        return (
            self.session.query(ProposalReview)
            .filter(ProposalReview.proposal_draft_id == proposal_draft_id)
            .order_by(ProposalReview.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_review(self, proposal_draft_id: str, review_id: str) -> ProposalReview | None:
        return (
            self.session.query(ProposalReview)
            .filter(
                ProposalReview.id == review_id,
                ProposalReview.proposal_draft_id == proposal_draft_id,
            )
            .first()
        )

    def _strengths(
        self,
        draft: ProposalDraft,
        matrix: RelatedWorkMatrix | None,
    ) -> list[str]:
        strengths = []
        if draft.related_work_matrix_id and matrix:
            strengths.append(
                f"Related-work positioning is grounded in {len(matrix.items_json or [])} matrix rows."
            )
        if draft.experiment_plan_id:
            strengths.append(
                "The proposal references an experiment plan instead of staying at idea level."
            )
        if draft.evidence_ids_json:
            strengths.append(
                f"Evidence trace is attached through {len(draft.evidence_ids_json)} evidence ids."
            )
        if draft.milestone_plan_json:
            strengths.append("Milestones make the first 90 days auditable.")
        if draft.risk_mitigation:
            strengths.append("Risks and mitigation are explicit enough for review.")
        return strengths or ["The draft exists as a reviewable artifact with stable ids."]

    def _concerns(
        self,
        draft: ProposalDraft,
        matrix: RelatedWorkMatrix | None,
    ) -> list[str]:
        concerns = []
        if matrix is None:
            concerns.append("No related-work matrix is attached, so novelty positioning is weak.")
        elif matrix.missing_searches_json:
            concerns.append(
                "Related-work screening still has missing searches: "
                + ", ".join(matrix.missing_searches_json[:4])
            )
        if not draft.experiment_plan_id:
            concerns.append("No experiment plan is attached to falsify the proposal.")
        if not draft.evidence_ids_json:
            concerns.append("No evidence ids are attached to support the motivation.")
        if "Not specified" in draft.method_summary:
            concerns.append("Method summary still contains unspecified details.")
        if "Not specified" in draft.experiment_summary:
            concerns.append("Experiment summary still contains unspecified details.")
        return concerns

    def _required_revisions(
        self,
        draft: ProposalDraft,
        matrix: RelatedWorkMatrix | None,
    ) -> list[str]:
        revisions = [
            "Rewrite the novelty claim as one falsifiable sentence.",
            "Name the nearest related work and state the exact differentiating assumption.",
            "Define the smallest experiment that can invalidate the core hypothesis.",
        ]
        if matrix is None:
            revisions.insert(0, "Generate and inspect a related-work matrix before advisor review.")
        elif matrix.missing_searches_json:
            revisions.insert(0, "Resolve missing related-work searches before claiming novelty.")
        if not draft.experiment_plan_id:
            revisions.append(
                "Attach an experiment plan with dataset, baseline, metric, and failure mode."
            )
        if not draft.evidence_ids_json:
            revisions.append("Attach evidence ids that justify the problem statement.")
        return revisions

    def _missing_evidence(
        self,
        draft: ProposalDraft,
        matrix: RelatedWorkMatrix | None,
    ) -> list[str]:
        missing = []
        if not draft.evidence_ids_json:
            missing.append("supporting_evidence_ids")
        if matrix is None:
            missing.append("related_work_matrix")
        elif matrix.missing_searches_json:
            missing.extend(matrix.missing_searches_json[:4])
        if not draft.experiment_plan_id:
            missing.append("experiment_plan")
        return missing

    def _readiness_score(
        self,
        draft: ProposalDraft,
        matrix: RelatedWorkMatrix | None,
    ) -> float:
        score = 0.0
        if draft.abstract and draft.problem_statement and draft.novelty_statement:
            score += 0.2
        if matrix is not None:
            score += 0.2
        if draft.experiment_plan_id:
            score += 0.2
        if draft.evidence_ids_json:
            score += 0.15
        if draft.milestone_plan_json:
            score += 0.15
        if draft.risk_mitigation:
            score += 0.1
        if matrix and matrix.missing_searches_json:
            score -= 0.08
        return round(max(0.0, min(score, 1.0)), 4)

    def _decision(self, readiness_score: float, concerns: list[str]) -> str:
        if readiness_score >= 0.82 and len(concerns) <= 1:
            return "ready_for_advisor_review"
        if readiness_score >= 0.65:
            return "revise"
        return "not_ready"

    def _summary(
        self,
        decision: str,
        readiness_score: float,
        strengths: list[str],
        concerns: list[str],
    ) -> str:
        return (
            f"Decision is {decision} with readiness score {readiness_score}. "
            f"Found {len(strengths)} strengths and {len(concerns)} concerns. "
            "Treat this as a proposal-readiness screen before spending more research time."
        )

    def _render_markdown(self, review: ProposalReview) -> str:
        lines = [
            f"# Proposal Readiness Review: {review.decision}",
            "",
            f"- Review ID: `{review.id}`",
            f"- Proposal Draft ID: `{review.proposal_draft_id}`",
            f"- Idea ID: `{review.idea_id}`",
            f"- Reviewer: `{review.reviewer_type}`",
            f"- Readiness Score: {review.readiness_score}",
            "",
            "## Summary",
            "",
            review.summary,
            "",
            "## Strengths",
            "",
        ]
        lines.extend([f"- {item}" for item in review.strengths_json or []])
        lines.extend(["", "## Concerns", ""])
        if review.concerns_json:
            lines.extend([f"- {item}" for item in review.concerns_json])
        else:
            lines.append("- No blocking concerns found in this readiness pass.")
        lines.extend(["", "## Required Revisions", ""])
        lines.extend([f"- {item}" for item in review.required_revisions_json or []])
        lines.extend(["", "## Missing Evidence", ""])
        if review.missing_evidence_json:
            lines.extend([f"- `{item}`" for item in review.missing_evidence_json])
        else:
            lines.append("`none`")
        return "\n".join(lines).strip() + "\n"
