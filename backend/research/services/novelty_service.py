from sqlalchemy.orm import Session

from backend.research.models import Idea, NoveltyCheck
from backend.research.schemas import LiteratureSearchItem, LiteratureSearchResponse
from backend.research.services.literature_search_service import LiteratureSearchService
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

    def create_check(
        self,
        idea_id: str,
        include_external_literature: bool = True,
        *,
        limit: int = 8,
        query_override: str = "",
        mode: str = "screening",
    ) -> NoveltyCheck:
        idea = self.session.get(Idea, idea_id)
        if idea is None:
            raise ValueError("Idea not found")

        query = " ".join(query_override.split()) or self._build_query(idea)
        limit = max(1, min(limit, 25))
        context = RetrievalService(self.session).search_context(
            query=query,
            paper_ids=[],
            limit=limit,
            include_graph=False,
        )
        literature = LiteratureSearchService(self.session).search(
            query=query,
            limit=limit,
            include_external=include_external_literature,
        )
        idea_hits = [hit for hit in context.ideas if hit.item.id != idea.id]
        collision_signals = self._build_collision_signals(
            context.evidences,
            context.gaps,
            idea_hits,
            literature.items,
        )
        local_overlap_score = self._score_overlap(collision_signals)
        external_overlap_score = self._external_overlap_score(literature)
        risk_level = self._risk_level(local_overlap_score, idea_hits)

        check = NoveltyCheck(
            idea_id=idea.id,
            status=(
                "completed_external_novelty_refresh"
                if mode == "external_refresh"
                else "completed_literature_screening"
            ),
            risk_level=risk_level,
            summary=self._summary(risk_level, local_overlap_score, collision_signals, literature),
            local_overlap_score=local_overlap_score,
            external_overlap_score=external_overlap_score,
            collision_signals_json=collision_signals,
            missing_searches_json=self._missing_searches(literature, include_external_literature),
            recommended_actions_json=self._recommended_actions(risk_level),
            checked_sources_json=[
                "local_evidence_index",
                "local_gap_index",
                "local_idea_index",
                "local_literature_search",
                f"external_literature_search:{literature.external_status}",
                f"query_override:{bool(query_override.strip())}",
                f"novelty_mode:{mode}",
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
        literature_items: list[LiteratureSearchItem],
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
        for item in literature_items[:5]:
            signals.append(
                {
                    "source_type": "literature",
                    "source_id": item.source_id,
                    "label": item.title,
                    "score": item.score,
                    "matched_terms": [item.provider],
                    "provider": item.provider,
                    "year": item.year,
                    "url": item.url,
                }
            )
        signals.sort(key=lambda signal: signal["score"], reverse=True)
        return signals[:12]

    def _score_overlap(self, signals: list[dict]) -> float:
        if not signals:
            return 0.0
        weighted = 0.0
        for signal in signals:
            multiplier = 1.3 if signal["source_type"] in {"idea", "literature"} else 1.0
            weighted += min(float(signal["score"]), 8.0) * multiplier
        return round(min(weighted / 35.0, 1.0), 4)

    def _external_overlap_score(self, literature: LiteratureSearchResponse) -> float | None:
        external_items = [item for item in literature.items if item.provider != "local"]
        if literature.external_status in {"not_requested", "disabled"}:
            return None
        if not external_items:
            return 0.0
        return round(min(sum(min(item.score, 10.0) for item in external_items) / 40.0, 1.0), 4)

    def _risk_level(self, score: float, idea_hits: list[ScoredItem]) -> str:
        if idea_hits and score >= 0.45:
            return "high"
        if score >= 0.35:
            return "medium"
        if score > 0:
            return "low"
        return "unknown"

    def _summary(
        self,
        risk_level: str,
        score: float,
        signals: list[dict],
        literature: LiteratureSearchResponse,
    ) -> str:
        if not signals:
            return (
                "No local or literature collision signals were found. External literature search "
                f"status is {literature.external_status}; deeper search is still required before "
                "claiming novelty."
            )
        return (
            f"Local novelty risk is {risk_level} with overlap score {score}. "
            f"Found {len(signals)} collision signals across local object indexes and literature "
            f"search. External literature search status is {literature.external_status}; treat "
            "this as a screening result, not a final novelty judgment."
        )

    def _missing_searches(
        self,
        literature: LiteratureSearchResponse,
        include_external_literature: bool,
    ) -> list[str]:
        searches = []
        if not self._external_provider_attempted(literature, "semantic_scholar"):
            searches.append("semantic_scholar_adapter")
        if not self._external_provider_present(literature, "arxiv"):
            searches.append("arxiv_recent_preprints")
        if not include_external_literature:
            searches.insert(0, "external_literature_search_not_requested")
        elif literature.external_status == "disabled":
            searches.insert(0, "external_literature_search_disabled")
        elif "rate_limited" in literature.external_status:
            searches.insert(0, f"external_literature_search_{literature.external_status}")
        elif literature.external_status.startswith("failed"):
            searches.insert(0, f"external_literature_search_{literature.external_status}")
        elif literature.external_status == "completed":
            searches.append("external_literature_search_needs_manual_review")
        return searches

    def _external_provider_attempted(
        self,
        literature: LiteratureSearchResponse,
        provider: str,
    ) -> bool:
        return (
            self._external_provider_present(literature, provider)
            or provider in literature.external_status
        )

    def _external_provider_present(
        self,
        literature: LiteratureSearchResponse,
        provider: str,
    ) -> bool:
        return any(item.provider == provider for item in literature.items)

    def _recommended_actions(self, risk_level: str) -> list[str]:
        actions = [
            "Review the top local literature-search collision signals.",
            "Run external literature search against recent papers and preprints.",
            "Rewrite the novelty claim as one falsifiable sentence.",
            "Compare the idea against the nearest local collision signals.",
        ]
        if risk_level in {"medium", "high"}:
            actions.insert(0, "Narrow the method or evaluation target to avoid local overlap.")
        if risk_level == "unknown":
            actions.append("Add more source papers before trusting the novelty estimate.")
        return actions
