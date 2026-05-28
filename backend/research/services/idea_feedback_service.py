from sqlalchemy.orm import Session

from backend.research.models import Idea, IdeaFeedback


VALID_DECISIONS = {"shortlist", "accept", "revise", "reject", "archive"}


class IdeaFeedbackService:
    def __init__(self, session: Session):
        self.session = session

    def create_feedback(
        self,
        idea_id: str,
        *,
        decision: str,
        rating: float | None = None,
        comment: str = "",
        tags: list[str] | None = None,
        created_by: str = "researcher",
    ) -> IdeaFeedback:
        idea = self.session.get(Idea, idea_id)
        if idea is None:
            raise ValueError("Idea not found")

        feedback = IdeaFeedback(
            idea_id=idea.id,
            decision=self._decision(decision),
            rating=self._rating(rating),
            comment=" ".join((comment or "").split()),
            tags_json=self._tags(tags or []),
            created_by=" ".join((created_by or "researcher").split()) or "researcher",
        )
        self.session.add(feedback)
        self.session.commit()
        self.session.refresh(feedback)
        return feedback

    def list_feedback_for_idea(self, idea_id: str) -> list[IdeaFeedback]:
        if self.session.get(Idea, idea_id) is None:
            raise ValueError("Idea not found")
        return (
            self.session.query(IdeaFeedback)
            .filter(IdeaFeedback.idea_id == idea_id)
            .order_by(IdeaFeedback.created_at.desc())
            .all()
        )

    def _decision(self, decision: str) -> str:
        cleaned = (decision or "revise").strip().lower()
        return cleaned if cleaned in VALID_DECISIONS else "revise"

    def _rating(self, rating: float | None) -> float | None:
        if rating is None:
            return None
        return round(max(1.0, min(float(rating), 5.0)), 2)

    def _tags(self, tags: list[str]) -> list[str]:
        result = []
        seen = set()
        for tag in tags:
            cleaned = " ".join(str(tag).split()).lower()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                result.append(cleaned)
        return result[:12]
