import re
from typing import Any
from xml.etree import ElementTree

import requests
from sqlalchemy.orm import Session

from backend.research.config import settings
from backend.research.models import Evidence, Paper
from backend.research.schemas import LiteratureSearchItem, LiteratureSearchResponse


TOKEN_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_\-]{2,}")
EXTERNAL_QUERY_MAX_CHARS = 240
EXTERNAL_QUERY_MAX_TERMS = 16
EXTERNAL_QUERY_STOPWORDS = {
    "address",
    "against",
    "aligned",
    "and",
    "around",
    "baseline",
    "because",
    "before",
    "cited",
    "claim",
    "compare",
    "constraints",
    "can",
    "designed",
    "design",
    "effect",
    "evidence",
    "evaluation",
    "executable",
    "experiment",
    "extension",
    "first",
    "focus",
    "focused",
    "for",
    "from",
    "generic",
    "generated",
    "gap",
    "gap-targeted",
    "hypothesis",
    "idea",
    "ideas",
    "implement",
    "improve",
    "intervention",
    "investigate",
    "keep",
    "linked",
    "making",
    "measurable",
    "method",
    "mode",
    "narrower",
    "novelty",
    "observed",
    "one",
    "opportunity",
    "original",
    "outperform",
    "over",
    "planned",
    "produce",
    "refined",
    "research",
    "revised",
    "revision",
    "scaling",
    "setup",
    "sharpen",
    "source-paper",
    "start",
    "targeting",
    "testable",
    "the",
    "translate",
    "variant",
    "while",
    "will",
    "with",
}


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
                external_items, external_status = self._search_external(query, limit)

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
        response = self._request_external(
            f"{settings.openalex_base_url.rstrip('/')}/works",
            params={"search": query, "per-page": limit},
        )
        results = response.json().get("results", [])
        return [self._openalex_item(item, idx) for idx, item in enumerate(results)]

    def _search_external(self, query: str, limit: int) -> tuple[list[LiteratureSearchItem], str]:
        provider_items: list[LiteratureSearchItem] = []
        provider_statuses: list[str] = []
        external_query = self._external_query(query)
        for provider in self._external_providers():
            try:
                if provider == "openalex":
                    provider_items.extend(self._search_openalex(external_query, limit))
                    provider_statuses.append("openalex:completed")
                elif provider == "arxiv":
                    provider_items.extend(self._search_arxiv(external_query, limit))
                    provider_statuses.append("arxiv:completed")
                elif provider == "semantic_scholar":
                    provider_items.extend(self._search_semantic_scholar(external_query, limit))
                    provider_statuses.append("semantic_scholar:completed")
            except requests.HTTPError as exc:
                provider_statuses.append(f"{provider}:{self._http_error_status(exc)}")
            except requests.RequestException as exc:
                provider_statuses.append(f"{provider}:failed:{type(exc).__name__}")
            except ElementTree.ParseError:
                provider_statuses.append(f"{provider}:failed:ParseError")
        if not provider_statuses:
            return [], "not_configured"
        if all(status.endswith(":completed") for status in provider_statuses):
            return provider_items, "completed"
        if provider_items or any(status.endswith(":completed") for status in provider_statuses):
            return provider_items, "partial:" + ",".join(provider_statuses)
        if all(":rate_limited:" in status for status in provider_statuses):
            return [], "rate_limited:" + ",".join(provider_statuses)
        return [], "failed:" + ",".join(provider_statuses)

    def _external_providers(self) -> list[str]:
        providers = []
        for provider in settings.external_literature_providers.split(","):
            normalized = provider.strip().lower()
            if normalized in {"semantic-scholar", "semanticscholar"}:
                normalized = "semantic_scholar"
            if (
                normalized in {"openalex", "arxiv", "semantic_scholar"}
                and normalized not in providers
            ):
                providers.append(normalized)
        return providers

    def _external_query(self, query: str) -> str:
        terms = [term for term in self._terms(query) if term not in EXTERNAL_QUERY_STOPWORDS]
        if not terms:
            terms = self._terms(query)
        compact = " ".join(terms[:EXTERNAL_QUERY_MAX_TERMS])
        if compact:
            return compact[:EXTERNAL_QUERY_MAX_CHARS]
        return query.strip()[:EXTERNAL_QUERY_MAX_CHARS]

    def _request_external(
        self,
        url: str,
        *,
        params: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> requests.Response:
        request_headers = {"User-Agent": settings.external_literature_user_agent}
        if headers:
            request_headers.update(headers)
        response = requests.get(
            url,
            params=params,
            headers=request_headers,
            timeout=settings.external_literature_request_timeout_seconds,
        )
        response.raise_for_status()
        return response

    def _http_error_status(self, exc: requests.HTTPError) -> str:
        label = self._http_error_label(exc)
        if label == "HTTPError_429":
            return f"rate_limited:{label}"
        return f"failed:{label}"

    def _http_error_label(self, exc: requests.HTTPError) -> str:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        return f"HTTPError_{status_code}" if status_code else "HTTPError"

    def _semantic_scholar_headers(self) -> dict[str, str]:
        if not settings.semantic_scholar_api_key:
            return {}
        return {"x-api-key": settings.semantic_scholar_api_key}

    def _openalex_item(self, item: dict[str, Any], idx: int) -> LiteratureSearchItem:
        authors = []
        for authorship in item.get("authorships", []):
            author = authorship.get("author") or {}
            if author.get("display_name"):
                authors.append(author["display_name"])
        primary_location = item.get("primary_location") or {}
        source = primary_location.get("source") or {}
        venue = source.get("display_name", "")
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

    def _search_arxiv(self, query: str, limit: int) -> list[LiteratureSearchItem]:
        response = self._request_external(
            settings.arxiv_base_url,
            params={
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": limit,
                "sortBy": "relevance",
                "sortOrder": "descending",
            },
        )
        root = ElementTree.fromstring(response.text)
        namespace = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", namespace)
        return [self._arxiv_item(entry, idx, namespace) for idx, entry in enumerate(entries)]

    def _arxiv_item(
        self,
        entry: ElementTree.Element,
        idx: int,
        namespace: dict[str, str],
    ) -> LiteratureSearchItem:
        title = self._xml_text(entry.find("atom:title", namespace))
        source_id = self._xml_text(entry.find("atom:id", namespace))
        abstract = self._xml_text(entry.find("atom:summary", namespace))
        published = self._xml_text(entry.find("atom:published", namespace))
        authors = [
            self._xml_text(author.find("atom:name", namespace))
            for author in entry.findall("atom:author", namespace)
        ]
        authors = [author for author in authors if author]
        categories = [
            category.attrib.get("term", "")
            for category in entry.findall("atom:category", namespace)
            if category.attrib.get("term")
        ]
        year = int(published[:4]) if published[:4].isdigit() else None
        return LiteratureSearchItem(
            provider="arxiv",
            source_id=source_id,
            title=" ".join(title.split()) or "Untitled arXiv preprint",
            authors=authors,
            year=year,
            venue="arXiv",
            url=source_id,
            abstract=" ".join(abstract.split())[:1200],
            score=max(1.0, 9.5 - idx),
            metadata={
                "published": published,
                "categories": categories,
            },
        )

    def _xml_text(self, element: ElementTree.Element | None) -> str:
        if element is None or element.text is None:
            return ""
        return element.text.strip()

    def _search_semantic_scholar(self, query: str, limit: int) -> list[LiteratureSearchItem]:
        response = self._request_external(
            settings.semantic_scholar_base_url,
            params={
                "query": query,
                "limit": limit,
                "fields": "title,authors,year,venue,url,abstract,citationCount,externalIds",
            },
            headers=self._semantic_scholar_headers(),
        )
        results = response.json().get("data", [])
        return [self._semantic_scholar_item(item, idx) for idx, item in enumerate(results)]

    def _semantic_scholar_item(self, item: dict[str, Any], idx: int) -> LiteratureSearchItem:
        authors = [
            author.get("name", "") for author in item.get("authors", []) if author.get("name")
        ]
        external_ids = item.get("externalIds") or {}
        source_id = item.get("paperId") or external_ids.get("DOI") or item.get("url") or ""
        return LiteratureSearchItem(
            provider="semantic_scholar",
            source_id=source_id,
            title=item.get("title") or "Untitled Semantic Scholar paper",
            authors=authors,
            year=item.get("year"),
            venue=item.get("venue") or "",
            url=item.get("url") or "",
            abstract=(item.get("abstract") or "")[:1200],
            score=max(1.0, 9.0 - idx),
            metadata={
                "citation_count": item.get("citationCount"),
                "external_ids": external_ids,
            },
        )

    def _abstract_from_inverted_index(self, inverted_index: dict[str, list[int]]) -> str:
        if not inverted_index:
            return ""
        words_by_position = {}
        for word, positions in inverted_index.items():
            for position in positions:
                words_by_position[position] = word
        return " ".join(words_by_position[position] for position in sorted(words_by_position))[
            :1200
        ]

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
