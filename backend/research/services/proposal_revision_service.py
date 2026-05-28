from sqlalchemy.orm import Session

from backend.research.models import ProposalDraft, ProposalReview, ProposalRevision


class ProposalRevisionService:
    def __init__(self, session: Session):
        self.session = session

    def create_revision(
        self,
        proposal_draft_id: str,
        *,
        proposal_review_id: str | None = None,
        include_latest_review: bool = True,
        created_by: str = "system",
    ) -> ProposalRevision:
        draft = self.session.get(ProposalDraft, proposal_draft_id)
        if draft is None:
            raise ValueError("Proposal draft not found")

        review = self._select_review(draft.id, proposal_review_id, include_latest_review)
        applied_revisions = self._applied_revisions(review)
        missing_evidence_actions = self._missing_evidence_actions(review)
        revised_sections = self._revised_sections(draft, review, applied_revisions)
        revision_summary = self._summary(draft, review, applied_revisions, missing_evidence_actions)

        revision = ProposalRevision(
            proposal_draft_id=draft.id,
            proposal_review_id=review.id if review else None,
            idea_id=draft.idea_id,
            status="revised_from_review" if review else "revised_without_review",
            revision_summary=revision_summary,
            applied_revisions_json=applied_revisions,
            missing_evidence_actions_json=missing_evidence_actions,
            revised_sections_json=revised_sections,
            created_by=created_by or "system",
        )
        revision.markdown_export = self._render_markdown(revision, draft)
        self.session.add(revision)
        self.session.commit()
        self.session.refresh(revision)
        return revision

    def list_for_draft(self, proposal_draft_id: str, limit: int = 20) -> list[ProposalRevision]:
        if self.session.get(ProposalDraft, proposal_draft_id) is None:
            raise ValueError("Proposal draft not found")
        limit = max(1, min(limit, 100))
        return (
            self.session.query(ProposalRevision)
            .filter(ProposalRevision.proposal_draft_id == proposal_draft_id)
            .order_by(ProposalRevision.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_revision(self, proposal_draft_id: str, revision_id: str) -> ProposalRevision | None:
        return (
            self.session.query(ProposalRevision)
            .filter(
                ProposalRevision.id == revision_id,
                ProposalRevision.proposal_draft_id == proposal_draft_id,
            )
            .first()
        )

    def _select_review(
        self,
        draft_id: str,
        review_id: str | None,
        include_latest: bool,
    ) -> ProposalReview | None:
        if review_id:
            review = self.session.get(ProposalReview, review_id)
            if review is None or review.proposal_draft_id != draft_id:
                raise ValueError("Proposal review not found for draft")
            return review
        if not include_latest:
            return None
        return (
            self.session.query(ProposalReview)
            .filter(ProposalReview.proposal_draft_id == draft_id)
            .order_by(ProposalReview.created_at.desc())
            .first()
        )

    def _applied_revisions(self, review: ProposalReview | None) -> list[str]:
        if review and review.required_revisions_json:
            return [
                f"Addressed review action: {item}" for item in review.required_revisions_json[:8]
            ]
        return [
            "Sharpened the proposal into falsifiable claims.",
            "Separated novelty positioning from implementation details.",
            "Added explicit evidence and experiment follow-up actions.",
        ]

    def _missing_evidence_actions(self, review: ProposalReview | None) -> list[str]:
        if not review or not review.missing_evidence_json:
            return ["No missing evidence was flagged by the selected review."]
        return [
            f"Resolve missing evidence item `{item}` before the next readiness review."
            for item in review.missing_evidence_json
        ]

    def _revised_sections(
        self,
        draft: ProposalDraft,
        review: ProposalReview | None,
        applied_revisions: list[str],
    ) -> dict:
        revision_focus = "; ".join(applied_revisions[:3])
        readiness_context = ""
        if review:
            readiness_context = (
                f"Reviewer decision `{review.decision}` with readiness score "
                f"{review.readiness_score}."
            )

        return {
            "abstract": " ".join(
                [
                    draft.abstract,
                    "Revision focus:",
                    revision_focus,
                    readiness_context,
                ]
            ).strip(),
            "novelty_statement": " ".join(
                [
                    "Falsifiable novelty claim:",
                    draft.novelty_statement,
                    "The next version must name the nearest work, the changed assumption, and the first failing case.",
                ]
            ).strip(),
            "related_work_summary": " ".join(
                [
                    draft.related_work_summary,
                    "Revision action: close the listed missing searches and turn the top overlap rows into explicit comparison bullets.",
                ]
            ).strip(),
            "experiment_summary": " ".join(
                [
                    draft.experiment_summary,
                    "Revision action: define the smallest experiment that can invalidate the core hypothesis and record the failure threshold.",
                ]
            ).strip(),
            "risk_mitigation": "\n".join(
                [
                    draft.risk_mitigation,
                    "- Revision action: convert each major concern into a tracked experiment or literature-search task.",
                ]
            ).strip(),
            "milestone_plan": draft.milestone_plan_json or [],
        }

    def _summary(
        self,
        draft: ProposalDraft,
        review: ProposalReview | None,
        applied_revisions: list[str],
        missing_evidence_actions: list[str],
    ) -> str:
        if review:
            return (
                f"Created a revised proposal artifact for draft {draft.id} using review "
                f"{review.id}. Applied {len(applied_revisions)} revision actions and tracked "
                f"{len(missing_evidence_actions)} missing-evidence actions."
            )
        return (
            f"Created a revised proposal artifact for draft {draft.id} without an attached review. "
            "Use this as a manual revision checkpoint and run readiness review next."
        )

    def _render_markdown(self, revision: ProposalRevision, draft: ProposalDraft) -> str:
        sections = revision.revised_sections_json or {}
        lines = [
            f"# Proposal Revision: {draft.title}",
            "",
            f"- Revision ID: `{revision.id}`",
            f"- Source Draft ID: `{revision.proposal_draft_id}`",
            f"- Proposal Review ID: `{revision.proposal_review_id or 'none'}`",
            f"- Idea ID: `{revision.idea_id}`",
            f"- Status: `{revision.status}`",
            "",
            "## Revision Summary",
            "",
            revision.revision_summary,
            "",
            "## Applied Revisions",
            "",
        ]
        lines.extend([f"- {item}" for item in revision.applied_revisions_json or []])
        lines.extend(["", "## Missing Evidence Actions", ""])
        lines.extend([f"- {item}" for item in revision.missing_evidence_actions_json or []])

        ordered_sections = [
            ("Abstract", "abstract"),
            ("Novelty Statement", "novelty_statement"),
            ("Related Work Summary", "related_work_summary"),
            ("Experiment Summary", "experiment_summary"),
            ("Risk Mitigation", "risk_mitigation"),
        ]
        for title, key in ordered_sections:
            lines.extend(
                ["", f"## Revised {title}", "", str(sections.get(key) or "Not specified.")]
            )

        lines.extend(["", "## Revised Milestones", ""])
        milestones = sections.get("milestone_plan") or []
        if milestones:
            for item in milestones:
                lines.append(
                    f"- {item.get('window', 'Window')}: {item.get('goal', 'Goal')} - "
                    f"{item.get('deliverable', 'Deliverable')}"
                )
        else:
            lines.append("- Not specified.")
        return "\n".join(lines).strip() + "\n"
