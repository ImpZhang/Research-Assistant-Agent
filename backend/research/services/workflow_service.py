from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.research.models import ExperimentPlan, Idea, Paper, PaperCard, ResearchGap, Review
from backend.research.services.experiment_service import ExperimentService
from backend.research.services.export_service import ExportService
from backend.research.services.gap_service import GapService
from backend.research.services.idea_service import IdeaService
from backend.research.services.review_service import ReviewService
from backend.research.services.structured_extraction_service import StructuredExtractionService


@dataclass
class LiteratureToIdeasResult:
    paper: Paper
    card: PaperCard
    gaps: list[ResearchGap]
    ideas: list[Idea]
    reviews: list[Review]
    experiment_plans: list[ExperimentPlan]
    markdown_export: str


class WorkflowService:
    def __init__(self, session: Session):
        self.session = session

    def run_literature_to_ideas(
        self,
        paper_id: str,
        max_gaps: int = 4,
        max_ideas_per_gap: int = 2,
        run_review: bool = True,
        run_experiment_plan: bool = True,
        include_markdown_export: bool = True,
    ) -> LiteratureToIdeasResult:
        paper = self.session.get(Paper, paper_id)
        if paper is None:
            raise ValueError("Paper not found")

        max_gaps = max(1, min(max_gaps, 20))
        max_ideas_per_gap = max(1, min(max_ideas_per_gap, 5))

        card = StructuredExtractionService(self.session).extract_paper_card(paper.id)
        gaps = GapService(self.session).mine_gaps([paper.id], max_gaps)
        ideas = IdeaService(self.session).generate_from_gaps(
            [gap.id for gap in gaps],
            max_ideas_per_gap,
        )

        reviews: list[Review] = []
        experiment_plans: list[ExperimentPlan] = []
        review_service = ReviewService(self.session)
        experiment_service = ExperimentService(self.session)
        for idea in ideas:
            if run_review:
                reviews.append(review_service.create_review(idea.id))
            if run_experiment_plan:
                experiment_plans.append(experiment_service.create_plan(idea.id))

        markdown_export = ""
        if include_markdown_export:
            markdown_export = self._render_markdown_bundle(ideas)

        self.session.refresh(paper)
        self.session.refresh(card)
        return LiteratureToIdeasResult(
            paper=paper,
            card=card,
            gaps=gaps,
            ideas=ideas,
            reviews=reviews,
            experiment_plans=experiment_plans,
            markdown_export=markdown_export,
        )

    def _render_markdown_bundle(self, ideas: list[Idea]) -> str:
        if not ideas:
            return ""

        export_service = ExportService(self.session)
        sections = [
            export_service.render_idea_markdown(idea.id)
            for idea in ideas
        ]
        return "\n---\n\n".join(section.strip() for section in sections) + "\n"
