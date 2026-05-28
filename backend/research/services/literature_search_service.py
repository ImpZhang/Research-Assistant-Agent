import re
from typing import Any

import requests
from sqlalchemy.orm import Session

from backend.research.config import settings
from backend.research.models import Evidence, Paper
from backend.research.schemas import LiteratureSearchItem, LiteratureSearchResponse


TOKEN_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_\-]{2,}")


class LiteratureSearchService:
    def __init__(self, session: Session):
        self.session = session

    def search(
        self,
        query: str,
        limit: int = 8,
        include_external: bool = False,
    ) -> LiteratureSearchResponse:
        terms = self._terms(query)
        if not terms:
            raise ValueError("Query must contain at least one searchable term")

        limit = max(1, min(limit, 25))
        local_items = self._search_local(terms, limit)
        external_items: list[LiteratureSearchItem] = []
        external_status = "not_requested"

        if include_external:
            if not settings.external_literature_search_enabled:
                external_status = "disabled"
            else:
                try:
                    external_items = self._search_openalex(query, limit)
                    external_status = "completed"
                except requests.RequestException as exc:
                    external_status = f"failed:{type(exc).__name__}"

        items = sorted(
            local_items + external_items,
            key=lambda item: item.score,
            reverse=True,
        )[:limit]
        return LiteratureSearchResponse(
            query=query,
            local_status="completed",
            external_status=external_status,
            items=items,
            message=(
                f"Returned {len(items)} literature search results "
                f"({len(local_items)} local, {len(external_items)} external)."
            ),
        )

    def _search_local(self, terms: list[str], limit: int) -> list[LiteratureSearchItem]:
        papers = self.session.query(Paper).order_by(Paper.created_at.desc()).limit(300).all()
        evidence_by_paper = self._load_evidence_by_paper([paper.id for paper in papers])
        items = []
        for paper in papers:
            evidence_text = " ".join(
                (evidence.summary or evidence.text)
                for evidence in evidence_by_paper.get(paper.id, [])[:5]
            )
            text = " ".join(
                [
                    paper.title,
                    " ".join(paper.authors_json or []),
                    paper.venue,
                    paper.domain,
                    paper.task,
                    evidence_text,
                ]
            )
            score = self._score(terms, text)
            if score <= 0:
                continue
            items.append(
                LiteratureSearchItem(
                    provider="local",
                    source_id=paper.id,
                    title=paper.title or paper.filename or paper.id,
                    authors=paper.authors_json or [],
                    year=paper.year,
                    venue=paper.venue,
                    url=paper.source_url,
                    abstract=evidence_text[:800],
                    score=score,
                    metadata={"filename": paper.filename, "status": paper.status},
                )
            )
        items.sort(key=lambda item: item.score, reverse=True)
        return items[:limit]

    def _load_evidence_by_paper(self, paper_ids: list[str]) -> dict[str, list[Evidence]]:
        if not paper_ids:
            return {}
        evidences = (
            self.session.query(Evidence)
            .filter(Evidence.paper_id.in_(paper_ids))
            .order_by(Evidence.created_at.asc())
            .limit(1000)
            .all()
        )
        grouped: dict[str, list[Evidence]] = {}
        for evidence in evidences:
            grouped.setdefault(evidence.paper_id, []).append(evidence)
        return grouped

    def _search_openalex(self, query: str, limit: int) -> list[LiteratureSearchItem]:
        response = requests.get(
            f"{settings.openalex_base_url.rstrip('/')}/works",
            params={"search": query, "per-page": limit},
            timeout=20,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        return [self._openalex_item(item, idx) for idx, item in enumerate(results)]

    def _openalex_item(self, item: dict[str, Any], idx: int) -> LiteratureSearchItem:
        authors = [
            authorship.get("author", {}).get("display_name", "")
            for authorship in item.get("authorships", [])
            if authorship.get("author", {}).get("display_name")
        ]
        venue = (
            item.get("primary_location", {})
            .get("source", {})
            .get("display_name", "")
        )
        return LiteratureSearchItem(
            provider="openalex",
            source_id=item.get("id", ""),
            title=item.get("title") or item.get("display_name") or "Untitled work",
            authors=authors,
            year=item.get("publication_year"),
            venue=venue,
            url=item.get("doi") or item.get("id") or "",
            abstract=self._abstract_from_inverted_index(item.get("abstract_inverted_index") or {}),
            score=max(1.0, 10.0 - idx),
            metadata={
                "cited_by_count": item.get("cited_by_count"),
                "openalex_id": item.get("id"),
            },
        )

    def _abstract_from_inverted_index(self, inverted_index: dict[str, list[int]]) -> str:
        if not inverted_index:
            return ""
        words_by_position = {}
        for word, positions in inverted_index.items():
            for position in positions:
                words_by_position[position] = word
        return " ".join(words_by_position[position] for position in sorted(words_by_position))[:1200]

    def _score(self, terms: list[str], text: str) -> float:
        normalized = text.lower()
        matched = [term for term in terms if term in normalized]
        if not matched:
            return 0.0
        phrase_bonus = 2.0 if " ".join(terms) in normalized else 0.0
        return round(float(len(matched)) + phrase_bonus, 4)

    def _terms(self, query: str) -> list[str]:
        seen = set()
        terms = []
        for token in TOKEN_RE.findall(query.lower()):
            if token not in seen:
                seen.add(token)
                terms.append(token)
        return terms
