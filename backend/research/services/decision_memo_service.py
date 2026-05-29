from sqlalchemy.orm import Session

from backend.research.models import (
    ExperimentAnalysis,
    Idea,
    IdeaDecisionMemo,
    IdeaFeedback,
    NoveltyCheck,
    ProposalReview,
    RelatedWorkMatrix,
    ResearchTask,
    Review,
)
from backend.research.services.artifact_graph_service import ArtifactGraphService
from backend.research.services.graph_service import GraphService


class IdeaDecisionMemoService:
    def __init__(self, session: Session):
        self.session = session

    def create_memo(
        self,
        idea_id: str,
        *,
        decision: str = "revise",
        rationale: list[str] | None = None,
        evidence_ids: list[str] | None = None,
        risks: list[str] | None = None,
        next_commitments: list[str] | None = None,
        created_by: str = "researcher",
    ) -> IdeaDecisionMemo:
        idea = self.session.get(Idea, idea_id)
        if idea is None:
            raise ValueError("Idea not found")

        feedback = self._latest(IdeaFeedback, idea.id)
        novelty_check = self._latest(NoveltyCheck, idea.id)
        review = self._latest(Review, idea.id)
        proposal_review = self._latest(ProposalReview, idea.id)
        analysis = self._latest(ExperimentAnalysis, idea.id)
        matrix = self._latest(RelatedWorkMatrix, idea.id)
        tasks = self._open_tasks(idea.id)

        source_artifacts = {
            "latest_feedback_id": feedback.id if feedback else "",
            "latest_novelty_check_id": novelty_check.id if novelty_check else "",
            "latest_review_id": review.id if review else "",
            "latest_proposal_review_id": proposal_review.id if proposal_review else "",
            "latest_experiment_analysis_id": analysis.id if analysis else "",
            "latest_related_work_matrix_id": matrix.id if matrix else "",
            "open_task_ids": [task.id for task in tasks[:8]],
        }
        memo = IdeaDecisionMemo(
            idea_id=idea.id,
            decision=decision or "revise",
            rationale_json=self._clean_list(rationale)
            or self._default_rationale(
                idea,
                feedback=feedback,
                novelty_check=novelty_check,
                review=review,
                proposal_review=proposal_review,
                analysis=analysis,
            ),
            evidence_ids_json=self._clean_list(evidence_ids) or list(idea.evidence_ids_json or []),
            risk_register_json=self._clean_list(risks)
            or self._default_risks(
                idea,
                novelty_check=novelty_check,
                proposal_review=proposal_review,
                analysis=analysis,
                matrix=matrix,
            ),
            next_commitments_json=self._clean_list(next_commitments)
            or self._default_next_commitments(
                proposal_review=proposal_review,
                analysis=analysis,
                matrix=matrix,
                tasks=tasks,
            ),
            source_artifacts_json=source_artifacts,
            created_by=created_by or "researcher",
        )
        self.session.add(memo)
        self.session.flush()
        memo.markdown_export = self._render_markdown(memo, idea)
        self.session.commit()
        self.session.refresh(memo)
        ArtifactGraphService(GraphService(self.session)).link_idea_decision_memo(memo)
        self.session.commit()
        self.session.refresh(memo)
        return memo

    def list_for_idea(self, idea_id: str, limit: int = 20) -> list[IdeaDecisionMemo]:
        if self.session.get(Idea, idea_id) is None:
            raise ValueError("Idea not found")
        limit = max(1, min(limit, 100))
        return (
            self.session.query(IdeaDecisionMemo)
            .filter(IdeaDecisionMemo.idea_id == idea_id)
            .order_by(IdeaDecisionMemo.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_memo(self, idea_id: str, memo_id: str) -> IdeaDecisionMemo | None:
        return (
            self.session.query(IdeaDecisionMemo)
            .filter(IdeaDecisionMemo.id == memo_id, IdeaDecisionMemo.idea_id == idea_id)
            .first()
        )

    def _latest(self, model, idea_id: str):
        return (
            self.session.query(model)
            .filter(model.idea_id == idea_id)
            .order_by(model.created_at.desc())
            .first()
        )

    def _open_tasks(self, idea_id: str) -> list[ResearchTask]:
        priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        tasks = (
            self.session.query(ResearchTask)
            .filter(ResearchTask.idea_id == idea_id)
            .filter(ResearchTask.status.in_(["todo", "doing", "blocked"]))
            .order_by(ResearchTask.created_at.desc())
            .limit(50)
            .all()
        )
        return sorted(
            tasks, key=lambda task: (priority_rank.get(task.priority, 9), task.created_at)
        )

    def _default_rationale(
        self,
        idea: Idea,
        *,
        feedback: IdeaFeedback | None,
        novelty_check: NoveltyCheck | None,
        review: Review | None,
        proposal_review: ProposalReview | None,
        analysis: ExperimentAnalysis | None,
    ) -> list[str]:
        items = [
            f"Research question: {self._clean(idea.research_question)}",
            f"Expected contribution: {self._clean(idea.expected_contribution)}",
            f"Novelty argument: {self._clean(idea.novelty_argument)}",
        ]
        if feedback:
            rating = f" rating={feedback.rating:.1f}" if feedback.rating is not None else ""
            items.append(f"Latest human feedback: {feedback.decision}{rating}. {feedback.comment}")
        if novelty_check:
            items.append(f"Novelty screen: {novelty_check.risk_level}. {novelty_check.summary}")
        if review:
            items.append(f"Reviewer simulation: {review.decision}. {review.summary}")
        if proposal_review:
            items.append(
                "Proposal readiness: "
                f"{proposal_review.decision} score={proposal_review.readiness_score:.2f}."
            )
        if analysis:
            items.append(
                f"Latest experiment analysis: {analysis.decision} "
                f"confidence={analysis.confidence:.2f}."
            )
        return self._clean_list(items)

    def _default_risks(
        self,
        idea: Idea,
        *,
        novelty_check: NoveltyCheck | None,
        proposal_review: ProposalReview | None,
        analysis: ExperimentAnalysis | None,
        matrix: RelatedWorkMatrix | None,
    ) -> list[str]:
        risks = [str(item) for item in (idea.risks_json or [])]
        if novelty_check and novelty_check.risk_level not in {"", "low"}:
            risks.append(f"Novelty risk is {novelty_check.risk_level}: {novelty_check.summary}")
        if proposal_review:
            risks.extend(str(item) for item in (proposal_review.concerns_json or [])[:5])
            risks.extend(str(item) for item in (proposal_review.missing_evidence_json or [])[:5])
        if analysis:
            risks.extend(str(item) for item in (analysis.concerns_json or [])[:5])
        if matrix:
            risks.extend(
                f"Missing search: {item}" for item in (matrix.missing_searches_json or [])[:5]
            )
        if not risks:
            risks.append("The decision still needs explicit falsification evidence.")
        return self._clean_list(risks)

    def _default_next_commitments(
        self,
        *,
        proposal_review: ProposalReview | None,
        analysis: ExperimentAnalysis | None,
        matrix: RelatedWorkMatrix | None,
        tasks: list[ResearchTask],
    ) -> list[str]:
        commitments = []
        if tasks:
            commitments.extend(f"{task.priority}/{task.status}: {task.title}" for task in tasks[:5])
        if analysis:
            commitments.extend(str(item) for item in (analysis.next_actions_json or [])[:5])
        if proposal_review:
            commitments.extend(
                str(item) for item in (proposal_review.required_revisions_json or [])[:5]
            )
        if matrix:
            commitments.extend(
                f"Resolve missing related-work search: {item}"
                for item in (matrix.missing_searches_json or [])[:5]
            )
        if not commitments:
            commitments.append("Create a related-work matrix and a falsifiable MVP experiment.")
        return self._clean_list(commitments)

    def _render_markdown(self, memo: IdeaDecisionMemo, idea: Idea) -> str:
        lines = [
            f"# Idea Decision Memo: {idea.title}",
            "",
            f"- Memo ID: `{memo.id}`",
            f"- Idea ID: `{idea.id}`",
            f"- Decision: `{memo.decision}`",
            f"- Created By: {memo.created_by}",
            "",
            "## Source Artifacts",
            "",
        ]
        for key, value in (memo.source_artifacts_json or {}).items():
            lines.append(f"- {key}: `{value}`")

        lines.extend(["", "## Rationale", ""])
        lines.extend(self._bullet_lines(memo.rationale_json or []))
        lines.extend(["", "## Evidence IDs", ""])
        lines.extend(
            self._bullet_lines(memo.evidence_ids_json or [], empty="No evidence IDs attached.")
        )
        lines.extend(["", "## Risk Register", ""])
        lines.extend(self._bullet_lines(memo.risk_register_json or []))
        lines.extend(["", "## Next Commitments", ""])
        lines.extend(self._bullet_lines(memo.next_commitments_json or []))
        return "\n".join(lines).strip() + "\n"

    def _bullet_lines(self, items: list, *, empty: str = "No items recorded.") -> list[str]:
        cleaned = self._clean_list(items)
        if not cleaned:
            return [f"- {empty}"]
        return [f"- {item}" for item in cleaned]

    def _clean_list(self, items: list | None) -> list[str]:
        if not items:
            return []
        cleaned = []
        for item in items:
            text = self._clean(str(item))
            if text and text not in cleaned:
                cleaned.append(text)
        return cleaned

    def _clean(self, text: str) -> str:
        return " ".join((text or "").split())
