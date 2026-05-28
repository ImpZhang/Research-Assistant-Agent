from sqlalchemy.orm import Session

from backend.research.models import Idea, Review


class ReviewService:
    def __init__(self, session: Session):
        self.session = session

    def list_reviews_for_idea(self, idea_id: str) -> list[Review]:
        return (
            self.session.query(Review)
            .filter(Review.idea_id == idea_id)
            .order_by(Review.created_at.desc())
            .all()
        )

    def create_review(self, idea_id: str) -> Review:
        idea = self.session.get(Idea, idea_id)
        if idea is None:
            raise ValueError("Idea not found")

        review = Review(
            idea_id=idea.id,
            reviewer_type="skeptical_area_chair_v0",
            summary=(
                "The idea is evidence-grounded and testable, but it needs a sharper novelty "
                "argument, stronger baseline coverage, and a minimal experiment that can fail."
            ),
            major_concerns_json=[
                "Novelty may be incremental unless the method or evaluation target is clearly differentiated from the source papers.",
                "The evidence support is promising, but external literature search is still needed to reduce collision risk.",
                "The current method sketch needs a concrete baseline and ablation plan before it is proposal-ready.",
            ],
            minor_concerns_json=[
                "Target venues are broad and should be narrowed after the first experiment.",
                "Resource requirements are still approximate.",
            ],
            required_experiments_json=[
                "Run a source-paper baseline on the gap-specific evaluation slice.",
                "Add an ablation that removes the gap-targeted component.",
                "Report both task-level metrics and diagnostic metrics tied to the gap.",
            ],
            decision="revise",
            action_items_json=[
                "Add a related-work collision check.",
                "Define the first MVP experiment in executable terms.",
                "Rewrite the novelty argument as a one-sentence claim.",
            ],
        )
        self.session.add(review)
        idea.status = "reviewed"
        self.session.commit()
        self.session.refresh(review)
        return review
