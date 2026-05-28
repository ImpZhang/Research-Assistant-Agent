from sqlalchemy.orm import Session

from backend.research.models import Idea, ResearchGap
from backend.research.services.graph_service import GraphService


class IdeaService:
    def __init__(self, session: Session):
        self.session = session

    def list_ideas(self) -> list[Idea]:
        return self.session.query(Idea).order_by(Idea.created_at.desc()).all()

    def get_idea(self, idea_id: str) -> Idea | None:
        return self.session.get(Idea, idea_id)

    def generate_from_gaps(
        self,
        gap_ids: list[str] | None = None,
        max_ideas_per_gap: int = 2,
    ) -> list[Idea]:
        query = self.session.query(ResearchGap).order_by(ResearchGap.created_at.desc())
        if gap_ids:
            query = query.filter(ResearchGap.id.in_(gap_ids))
        gaps = query.all()

        ideas: list[Idea] = []
        graph = GraphService(self.session)
        for gap in gaps:
            for variant in range(max(1, max_ideas_per_gap)):
                idea = self._build_idea(gap, variant)
                self.session.add(idea)
                self.session.flush()
                idea_node = graph.get_or_create_node(
                    node_type="idea",
                    label=idea.title,
                    canonical_key=idea.id,
                    payload={"status": idea.status, "version": idea.version},
                )
                gap_node = graph.get_or_create_node(
                    node_type="gap",
                    label=gap.title,
                    canonical_key=gap.id,
                    payload={"gap_type": gap.gap_type, "status": gap.status},
                )
                graph.create_edge(
                    source_node=idea_node,
                    target_node=gap_node,
                    edge_type="idea_addresses_gap",
                    evidence_ids=gap.evidence_ids_json or [],
                )
                ideas.append(idea)

        self.session.commit()
        for idea in ideas:
            self.session.refresh(idea)
        return ideas

    def _build_idea(self, gap: ResearchGap, variant: int) -> Idea:
        title_prefix = "Evidence-Guided" if variant == 0 else "Evaluation-Centered"
        title = f"{title_prefix} Study for {self._shorten(gap.title, 72)}"

        if variant == 0:
            research_question = (
                "Can a targeted method improvement address the documented research gap: "
                f"{gap.description}"
            )
            core_hypothesis = (
                "A method designed directly around the cited evidence will outperform a generic "
                "extension because it optimizes for the stated limitation or future-work need."
            )
            method_sketch = (
                "Use the gap evidence as design constraints, implement a focused method variant, "
                "and compare it against the source-paper baseline."
            )
        else:
            research_question = (
                "Can an evaluation protocol expose and measure the gap more clearly than current "
                f"benchmarks? Gap: {gap.description}"
            )
            core_hypothesis = (
                "A benchmark slice aligned with the gap evidence will reveal failure modes that "
                "standard aggregate metrics hide."
            )
            method_sketch = (
                "Construct a targeted evaluation split, define metrics around the gap, and test "
                "existing methods before proposing model changes."
            )

        return Idea(
            title=title,
            research_question=research_question,
            core_hypothesis=core_hypothesis,
            motivation=gap.why_important,
            related_gap_ids_json=[gap.id],
            related_paper_ids_json=gap.source_paper_ids_json or [],
            evidence_ids_json=gap.evidence_ids_json or [],
            method_sketch=method_sketch,
            expected_contribution=(
                "A research contribution that is explicitly grounded in prior-paper evidence and "
                "evaluated with a focused experimental setup."
            ),
            novelty_argument=(
                "The idea is positioned around an explicit limitation/future-work signal rather "
                "than a broad combination of existing techniques."
            ),
            datasets_json=["To be selected from source-paper datasets and related benchmarks."],
            baselines_json=["Source paper baseline", "Strong recent method", "Ablated proposed variant"],
            metrics_json=["Task metric", "Gap-specific diagnostic metric", "Efficiency/cost metric"],
            risks_json=[
                "The gap may already be addressed by newer external literature.",
                "The proposed change may improve only a narrow benchmark slice.",
            ],
            resource_requirements="MVP experiment should fit a single small benchmark slice first.",
            target_venues_json=["Workshop", "Domain conference", "Full conference after validation"],
            score_json={
                "novelty": 3.0,
                "feasibility": 4.0,
                "impact": 3.0,
                "evidence_support": 4.0,
                "experimental_verifiability": 4.0,
                "resource_cost": 3.0,
                "publication_potential": 3.0,
                "overall_score": 3.4,
                "rationale": "Initial heuristic score based on evidence-backed gap and MVP feasibility.",
            },
            status="draft",
            version=1,
        )

    def _shorten(self, text: str, max_len: int) -> str:
        compact = " ".join((text or "research gap").split())
        if len(compact) <= max_len:
            return compact
        return compact[: max_len - 3].rstrip() + "..."
