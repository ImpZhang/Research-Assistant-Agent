from sqlalchemy.orm import Session

from backend.research.models import Evidence, Paper, ResearchGap
from backend.research.services.graph_service import GraphService


GAP_TYPE_BY_EVIDENCE = {
    "limitation": "method_gap",
    "future_work": "application_gap",
    "problem": "evaluation_gap",
    "claim": "evaluation_gap",
}


class GapService:
    def __init__(self, session: Session):
        self.session = session

    def list_gaps(self) -> list[ResearchGap]:
        return self.session.query(ResearchGap).order_by(ResearchGap.created_at.desc()).all()

    def get_gap(self, gap_id: str) -> ResearchGap | None:
        return self.session.get(ResearchGap, gap_id)

    def mine_gaps(
        self, paper_ids: list[str] | None = None, max_gaps: int = 10
    ) -> list[ResearchGap]:
        query = self.session.query(Evidence).filter(
            Evidence.evidence_type.in_(["limitation", "future_work", "problem"])
        )
        if paper_ids:
            query = query.filter(Evidence.paper_id.in_(paper_ids))

        evidences = query.order_by(Evidence.created_at.asc()).limit(max_gaps).all()
        if len(evidences) < max_gaps:
            existing_ids = {evidence.id for evidence in evidences}
            fallback_query = self.session.query(Evidence).filter(Evidence.evidence_type == "claim")
            if paper_ids:
                fallback_query = fallback_query.filter(Evidence.paper_id.in_(paper_ids))
            fallback_evidences = fallback_query.order_by(Evidence.created_at.asc()).all()
            for evidence in fallback_evidences:
                if evidence.id in existing_ids:
                    continue
                evidences.append(evidence)
                existing_ids.add(evidence.id)
                if len(evidences) >= max_gaps:
                    break

        gaps = []
        graph = GraphService(self.session)
        for evidence in evidences:
            paper = self.session.get(Paper, evidence.paper_id)
            gap = ResearchGap(
                title=self._build_title(evidence),
                description=evidence.summary or evidence.text[:600],
                gap_type=GAP_TYPE_BY_EVIDENCE.get(evidence.evidence_type, "method_gap"),
                source_paper_ids_json=[evidence.paper_id],
                evidence_ids_json=[evidence.id],
                why_important=self._why_important(evidence, paper),
                why_unsolved=self._why_unsolved(evidence),
                possible_approaches_json=self._possible_approaches(evidence),
                feasibility_score=3.0,
                novelty_score=3.0,
                risk_level="medium",
                status="generated",
            )
            self.session.add(gap)
            self.session.flush()
            gap_node = graph.get_or_create_node(
                node_type="gap",
                label=gap.title,
                canonical_key=gap.id,
                payload={"gap_type": gap.gap_type, "status": gap.status},
            )
            evidence_node = graph.get_or_create_node(
                node_type="evidence",
                label=f"{evidence.evidence_type}: {evidence.supports}",
                canonical_key=evidence.id,
                payload={"paper_id": evidence.paper_id, "evidence_type": evidence.evidence_type},
            )
            graph.create_edge(
                source_node=gap_node,
                target_node=evidence_node,
                edge_type="gap_supported_by_evidence",
                evidence_ids=[evidence.id],
            )
            gaps.append(gap)

        self.session.commit()
        for gap in gaps:
            self.session.refresh(gap)
        return gaps

    def _build_title(self, evidence: Evidence) -> str:
        prefix = {
            "limitation": "Address limitation",
            "future_work": "Extend future work",
            "problem": "Investigate unresolved problem",
            "claim": "Investigate research opportunity",
        }.get(evidence.evidence_type, "Research gap")
        text = " ".join((evidence.summary or evidence.text).split())
        if len(text) > 80:
            text = text[:77].rstrip() + "..."
        return f"{prefix}: {text}"

    def _why_important(self, evidence: Evidence, paper: Paper | None) -> str:
        source = paper.title if paper and paper.title else "the source paper"
        if evidence.evidence_type == "limitation":
            return f"The evidence describes a limitation in {source}, which may point to a publishable improvement opportunity."
        if evidence.evidence_type == "future_work":
            return f"The evidence names a future direction in {source}, making it a natural candidate for follow-up research."
        if evidence.evidence_type == "claim":
            return f"The evidence captures a central claim or framing in {source}, which can be stress-tested for scope, robustness, and evaluation gaps."
        return f"The evidence frames a problem in {source}, which can be converted into a testable research question."

    def _why_unsolved(self, evidence: Evidence) -> str:
        if evidence.evidence_type == "future_work":
            return "The source frames this as future work, so the current paper likely does not fully solve it."
        if evidence.evidence_type == "limitation":
            return "The source explicitly presents this as a limitation or unresolved weakness."
        if evidence.evidence_type == "claim":
            return "The source states or motivates a claim, but additional evidence, stress tests, and comparison slices may be needed."
        return "The source motivates the problem, but additional method and evaluation design are needed."

    def _possible_approaches(self, evidence: Evidence) -> list[str]:
        if evidence.evidence_type == "limitation":
            return [
                "Design a method variant that targets the stated limitation.",
                "Build an evaluation slice that isolates the limitation.",
            ]
        if evidence.evidence_type == "future_work":
            return [
                "Turn the future-work direction into a concrete hypothesis.",
                "Compare against the source paper as the nearest baseline.",
            ]
        if evidence.evidence_type == "claim":
            return [
                "Turn the claim into a falsifiable research question.",
                "Design evaluation slices that test robustness, scope, and comparison baselines.",
            ]
        return [
            "Formalize the problem into a measurable research question.",
            "Search for datasets and baselines that expose the problem clearly.",
        ]
