from sqlalchemy.orm import Session

from backend.research.models import Idea, NoveltyCheck
from backend.research.services.retrieval_service import RetrievalService, ScoredItem


class NoveltyService:
    def __init__(self, session: Session):
        self.session = session

    def list_checks_for_idea(self, idea_id: str) -> list[NoveltyCheck]:
        return (
            self.session.query(NoveltyCheck)
            .filter(NoveltyCheck.idea_id == idea_id)
            .order_by(NoveltyCheck.created_at.desc())
            .all()
        )

    def create_check(self, idea_id: str) -> NoveltyCheck:
        idea = self.session.get(Idea, idea_id)
        if idea is None:
            raise ValueError("Idea not found")

        query = self._build_query(idea)
        context = RetrievalService(self.session).search_context(
            query=query,
            paper_ids=[],
            limit=8,
            include_graph=False,
        )
        idea_hits = [hit for hit in context.ideas if hit.item.id != idea.id]
        collision_signals = self._build_collision_signals(
            context.evidences,
            context.gaps,
            idea_hits,
        )
        local_overlap_score = self._score_overlap(collision_signals)
        risk_level = self._risk_level(local_overlap_score, idea_hits)

        check = NoveltyCheck(
            idea_id=idea.id,
            status="completed_local_only",
            risk_level=risk_level,
            summary=self._summary(risk_level, local_overlap_score, collision_signals),
            local_overlap_score=local_overlap_score,
            external_overlap_score=None,
            collision_signals_json=collision_signals,
            missing_searches_json=[
                "external_recent_papers",
                "semantic_scholar_or_openalex",
                "arxiv_recent_preprints",
            ],
            recommended_actions_json=self._recommended_actions(risk_level),
            checked_sources_json=[
                "local_evidence_index",
                "local_gap_index",
                "local_idea_index",
            ],
        )
        self.session.add(check)
        idea.status = "novelty_checked"
        self.session.commit()
        self.session.refresh(check)
        return check

    def _build_query(self, idea: Idea) -> str:
        return " ".join(
            [
                idea.title,
                idea.research_question,
                idea.core_hypothesis,
                idea.method_sketch,
                idea.novelty_argument,
                " ".join(idea.metrics_json or []),
                " ".join(idea.datasets_json or []),
            ]
        )

    def _build_collision_signals(
        self,
        evidences: list[ScoredItem],
        gaps: list[ScoredItem],
        ideas: list[ScoredItem],
    ) -> list[dict]:
        signals = []
        for hit in evidences[:5]:
            evidence = hit.item
            signals.append(
                {
                    "source_type": "evidence",
                    "source_id": evidence.id,
                    "label": evidence.summary or evidence.text[:180],
                    "score": hit.score,
                    "matched_terms": hit.matched_terms,
                }
            )
        for hit in gaps[:5]:
            gap = hit.item
            signals.append(
                {
                    "source_type": "gap",
                    "source_id": gap.id,
                    "label": gap.title,
                    "score": hit.score,
                    "matched_terms": hit.matched_terms,
                }
            )
        for hit in ideas[:5]:
            idea = hit.item
            signals.append(
                {
                    "source_type": "idea",
                    "source_id": idea.id,
                    "label": idea.title,
                    "score": hit.score,
                    "matched_terms": hit.matched_terms,
                }
            )
        signals.sort(key=lambda signal: signal["score"], reverse=True)
        return signals[:10]

    def _score_overlap(self, signals: list[dict]) -> float:
        if not signals:
            return 0.0
        weighted = 0.0
        for signal in signals:
            multiplier = 1.3 if signal["source_type"] == "idea" else 1.0
            weighted += min(float(signal["score"]), 8.0) * multiplier
        return round(min(weighted / 35.0, 1.0), 4)

    def _risk_level(self, score: float, idea_hits: list[ScoredItem]) -> str:
        if idea_hits and score >= 0.45:
            return "high"
        if score >= 0.35:
            return "medium"
        if score > 0:
            return "low"
        return "unknown"

    def _summary(self, risk_level: str, score: float, signals: list[dict]) -> str:
        if not signals:
            return (
                "No local collision signals were found. External literature search is still "
                "required before claiming novelty."
            )
        return (
            f"Local novelty risk is {risk_level} with overlap score {score}. "
            f"Found {len(signals)} local collision signals; treat this as a screening result, "
            "not a final novelty judgment."
        )

    def _recommended_actions(self, risk_level: str) -> list[str]:
        actions = [
            "Run external literature search against recent papers and preprints.",
            "Rewrite the novelty claim as one falsifiable sentence.",
            "Compare the idea against the nearest local collision signals.",
        ]
        if risk_level in {"medium", "high"}:
            actions.insert(0, "Narrow the method or evaluation target to avoid local overlap.")
        if risk_level == "unknown":
            actions.append("Add more source papers before trusting the novelty estimate.")
        return actions
