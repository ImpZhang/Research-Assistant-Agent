import re

from sqlalchemy.orm import Session

from backend.research.models import Evidence, Idea, ResearchGap
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
        topic = self._gap_topic(gap)
        gap_signal = self._gap_signal(gap)

        if variant == 0:
            title = f"Gap-Targeted Method for {topic}"
            research_question = (
                f"Can a method designed around the cited {gap_signal} improve {topic} "
                "over the source-paper baseline?"
            )
            core_hypothesis = (
                f"Targeting {topic} with the cited evidence as design constraints will outperform "
                "a generic extension because the intervention is aligned to the observed failure mode."
            )
            method_sketch = (
                f"Translate the evidence about {topic} into design constraints, implement one "
                "focused method variant, keep paper evidence linked to generated ideas, and "
                "compare it against the source-paper baseline."
            )
        else:
            title = f"Diagnostic Benchmark for {topic}"
            research_question = (
                f"Which benchmark slice best exposes failures in {topic}, and do current "
                "aggregate metrics hide that gap?"
            )
            core_hypothesis = (
                f"A benchmark slice aligned with the cited {gap_signal} will reveal {topic} "
                "failure modes that standard aggregate metrics hide."
            )
            method_sketch = (
                f"Construct a targeted evaluation split for {topic}, define diagnostic metrics "
                "around the cited evidence, and test existing methods before proposing model changes."
            )

        return Idea(
            title=title,
            research_question=research_question,
            core_hypothesis=core_hypothesis,
            motivation=gap.why_important,
            related_gap_ids_json=[gap.id],
            related_paper_ids_json=gap.source_paper_ids_json or [],
            evidence_ids_json=self._evidence_ids_for_gap(gap),
            method_sketch=method_sketch,
            expected_contribution=(
                f"An evidence-grounded contribution on {topic} with a focused experimental setup "
                "and clear comparison against source-paper baselines."
            ),
            novelty_argument=(
                f"The novelty is positioned around an explicit {gap_signal} and linked "
                "future-work context rather than a broad combination of existing techniques."
            ),
            datasets_json=["To be selected from source-paper datasets and related benchmarks."],
            baselines_json=[
                "Source paper baseline",
                "Strong recent method",
                "Ablated proposed variant",
            ],
            metrics_json=[
                "Task metric",
                "Gap-specific diagnostic metric",
                "Efficiency/cost metric",
            ],
            risks_json=[
                "The gap may already be addressed by newer external literature.",
                "The proposed change may improve only a narrow benchmark slice.",
            ],
            resource_requirements="MVP experiment should fit a single small benchmark slice first.",
            target_venues_json=[
                "Workshop",
                "Domain conference",
                "Full conference after validation",
            ],
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

    def _evidence_ids_for_gap(self, gap: ResearchGap, max_context: int = 6) -> list[str]:
        evidence_ids = self._dedupe_ids(gap.evidence_ids_json or [])
        if self.session is None or not (gap.source_paper_ids_json or []):
            return evidence_ids

        context_evidences = (
            self.session.query(Evidence)
            .filter(Evidence.paper_id.in_(gap.source_paper_ids_json or []))
            .order_by(Evidence.created_at.asc())
            .limit(24)
            .all()
        )
        priority = {
            "limitation": 0,
            "future_work": 1,
            "problem": 2,
            "result": 3,
            "method": 4,
            "dataset": 5,
            "claim": 6,
            "comparison": 7,
        }
        context_evidences.sort(
            key=lambda evidence: (
                priority.get(evidence.evidence_type, 99),
                evidence.created_at,
                evidence.id,
            )
        )
        for evidence in context_evidences:
            if evidence.id not in evidence_ids:
                evidence_ids.append(evidence.id)
            if len(evidence_ids) >= max_context:
                break
        return evidence_ids

    def _dedupe_ids(self, values: list[str]) -> list[str]:
        deduped = []
        seen = set()
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            deduped.append(value)
        return deduped

    def _shorten(self, text: str, max_len: int) -> str:
        compact = " ".join((text or "research gap").split())
        if len(compact) <= max_len:
            return compact
        return compact[: max_len - 3].rstrip() + "..."

    def _gap_signal(self, gap: ResearchGap) -> str:
        return {
            "method_gap": "method limitation",
            "application_gap": "future-work direction",
            "evaluation_gap": "evaluation gap",
        }.get(gap.gap_type or "", "research gap")

    def _gap_topic(self, gap: ResearchGap, max_len: int = 64) -> str:
        text = self._clean_gap_text(gap.description or gap.title or "the documented gap")
        lower = text.lower()
        phrase_map = [
            ("fine-grained geo-localization", "fine-grained geo-localization"),
            ("fine-grained geolocalization", "fine-grained geolocalization"),
            ("coordinate-level localization", "coordinate-level localization"),
            ("coordinate-level geolocalization", "coordinate-level geolocalization"),
            ("worldwide image geolocalization", "worldwide image geolocalization"),
            ("worldwide geolocalization", "worldwide geolocalization"),
            ("image geo-localization", "image geo-localization"),
            ("image geolocalization", "image geolocalization"),
            ("distance-aware ranking", "distance-aware ranking"),
            ("hierarchical geolocalization", "hierarchical geolocalization"),
            ("hierarchical sequence-prediction", "hierarchical sequence prediction"),
            ("evidence-grounded claims", "evidence-grounded claims"),
            ("evidence coverage", "evidence coverage"),
            ("claim validation", "claim validation"),
        ]
        for needle, label in phrase_map:
            if needle in lower:
                return label
        if "gps coordinates" in lower or "geographic coordinates" in lower:
            return "coordinate-level geolocalization"
        if "candidate" in lower and "ranking" in lower:
            return "candidate ranking"
        words = text.split()
        if len(words) > 10:
            text = " ".join(words[:10])
        return self._shorten(text or "the documented gap", max_len)

    def _clean_gap_text(self, text: str) -> str:
        compact = " ".join((text or "").split())
        compact = re.sub(
            r"^(Address limitation|Extend future work|Investigate unresolved problem|"
            r"Investigate research opportunity):\s*",
            "",
            compact,
            flags=re.IGNORECASE,
        )
        compact = re.sub(r"\[[^\]]+\]", "", compact)
        compact = re.sub(r"\s+", " ", compact).strip(" .")
        sentence_match = re.match(r"(.+?[.!?])\s+", compact)
        if sentence_match and len(sentence_match.group(1).split()) >= 5:
            return sentence_match.group(1).strip(" .")
        return compact
