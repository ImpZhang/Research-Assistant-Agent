from sqlalchemy.orm import Session

from backend.research.models import Evidence, Paper, ResearchGap


GAP_TYPE_BY_EVIDENCE = {
    "limitation": "method_gap",
    "future_work": "application_gap",
    "problem": "evaluation_gap",
}


class GapService:
    def __init__(self, session: Session):
        self.session = session

    def list_gaps(self) -> list[ResearchGap]:
        return self.session.query(ResearchGap).order_by(ResearchGap.created_at.desc()).all()

    def get_gap(self, gap_id: str) -> ResearchGap | None:
        return self.session.get(ResearchGap, gap_id)

    def mine_gaps(self, paper_ids: list[str] | None = None, max_gaps: int = 10) -> list[ResearchGap]:
        query = self.session.query(Evidence).filter(
            Evidence.evidence_type.in_(["limitation", "future_work", "problem"])
        )
        if paper_ids:
            query = query.filter(Evidence.paper_id.in_(paper_ids))

        evidences = query.order_by(Evidence.created_at.asc()).limit(max_gaps).all()
        gaps = []
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
        return f"The evidence frames a problem in {source}, which can be converted into a testable research question."

    def _why_unsolved(self, evidence: Evidence) -> str:
        if evidence.evidence_type == "future_work":
            return "The source frames this as future work, so the current paper likely does not fully solve it."
        if evidence.evidence_type == "limitation":
            return "The source explicitly presents this as a limitation or unresolved weakness."
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
        return [
            "Formalize the problem into a measurable research question.",
            "Search for datasets and baselines that expose the problem clearly.",
        ]
