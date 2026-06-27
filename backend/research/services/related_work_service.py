import re
from typing import Any

from sqlalchemy.orm import Session

from backend.research.models import Idea, RelatedWorkMatrix
from backend.research.schemas import LiteratureSearchItem, LiteratureSearchResponse
from backend.research.services.literature_search_service import LiteratureSearchService
from backend.research.services.retrieval_service import RetrievalService, ScoredItem


TOKEN_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_\-]{2,}")


class RelatedWorkService:
    def __init__(
        self,
        session: Session,
        *,
        retrieval_service: RetrievalService | None = None,
        literature_search_service: LiteratureSearchService | None = None,
    ):
        self.session = session
        self.retrieval_service = retrieval_service
        self.literature_search_service = literature_search_service

    def create_matrix(
        self,
        idea_id: str,
        *,
        include_external: bool = True,
        limit: int = 8,
        created_by: str = "system",
    ) -> RelatedWorkMatrix:
        idea = self.session.get(Idea, idea_id)
        if idea is None:
            raise ValueError("Idea not found")

        limit = max(1, min(limit, 25))
        query = self._build_query(idea)
        retrieval_service = self.retrieval_service or RetrievalService(self.session)
        literature_search_service = self.literature_search_service or LiteratureSearchService(
            self.session
        )
        context = retrieval_service.search_context(
            query=query,
            paper_ids=[],
            limit=limit,
            include_graph=False,
        )
        literature = literature_search_service.search(
            query=query,
            limit=limit,
            include_external=include_external,
        )

        rows = self._build_rows(
            idea=idea,
            evidences=context.evidences,
            gaps=context.gaps,
            ideas=[hit for hit in context.ideas if hit.item.id != idea.id],
            literature_items=literature.items,
            limit=limit,
        )
        differentiators = self._build_differentiators(rows, idea)
        missing_searches = self._missing_searches(literature, include_external)
        checked_sources = [
            "local_evidence_index",
            "local_gap_index",
            "local_idea_index",
            "local_literature_search",
            f"external_literature_search:{literature.external_status}",
        ]
        summary = self._summary(rows, literature)
        markdown_export = self._render_markdown(
            idea=idea,
            query=query,
            rows=rows,
            differentiators=differentiators,
            missing_searches=missing_searches,
            checked_sources=checked_sources,
            summary=summary,
        )

        matrix = RelatedWorkMatrix(
            idea_id=idea.id,
            status="completed_related_work_screening",
            query=query,
            items_json=rows,
            differentiators_json=differentiators,
            missing_searches_json=missing_searches,
            checked_sources_json=checked_sources,
            summary=summary,
            markdown_export=markdown_export,
            created_by=created_by or "system",
        )
        self.session.add(matrix)
        self.session.commit()
        self.session.refresh(matrix)
        return matrix

    def list_for_idea(self, idea_id: str, limit: int = 20) -> list[RelatedWorkMatrix]:
        if self.session.get(Idea, idea_id) is None:
            raise ValueError("Idea not found")
        limit = max(1, min(limit, 100))
        return (
            self.session.query(RelatedWorkMatrix)
            .filter(RelatedWorkMatrix.idea_id == idea_id)
            .order_by(RelatedWorkMatrix.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_matrix(self, idea_id: str, matrix_id: str) -> RelatedWorkMatrix | None:
        return (
            self.session.query(RelatedWorkMatrix)
            .filter(
                RelatedWorkMatrix.id == matrix_id,
                RelatedWorkMatrix.idea_id == idea_id,
            )
            .first()
        )

    def _build_query(self, idea: Idea) -> str:
        text = " ".join(
            [
                idea.title,
                idea.research_question,
                idea.core_hypothesis,
                idea.method_sketch,
                idea.expected_contribution,
                idea.novelty_argument,
                " ".join(idea.datasets_json or []),
                " ".join(idea.baselines_json or []),
                " ".join(idea.metrics_json or []),
            ]
        )
        query = self._clean(text)
        return query[:1600] if query else "research idea novelty evidence experiment"

    def _build_rows(
        self,
        *,
        idea: Idea,
        evidences: list[ScoredItem],
        gaps: list[ScoredItem],
        ideas: list[ScoredItem],
        literature_items: list[LiteratureSearchItem],
        limit: int,
    ) -> list[dict[str, Any]]:
        rows = []
        for hit in evidences[:limit]:
            evidence = hit.item
            rows.append(
                self._row(
                    source_type="evidence",
                    source_id=evidence.id,
                    title=evidence.summary or evidence.text[:180],
                    overlap_score=hit.score,
                    shared_terms=hit.matched_terms,
                    relevance=f"Local evidence from paper {evidence.paper_id}.",
                    differentiator=(
                        "State how the proposed method goes beyond this evidence rather than "
                        "only reusing the same motivation."
                    ),
                    metadata={
                        "paper_id": evidence.paper_id,
                        "evidence_type": evidence.evidence_type,
                        "confidence": evidence.confidence,
                    },
                )
            )

        for hit in gaps[:limit]:
            gap = hit.item
            rows.append(
                self._row(
                    source_type="gap",
                    source_id=gap.id,
                    title=gap.title,
                    overlap_score=hit.score,
                    shared_terms=hit.matched_terms,
                    relevance="Nearby mined research gap from the local corpus.",
                    differentiator=(
                        "Clarify whether the idea solves this exact gap, narrows it, or proposes "
                        "a different evaluation target."
                    ),
                    metadata={
                        "gap_type": gap.gap_type,
                        "risk_level": gap.risk_level,
                        "source_paper_ids": gap.source_paper_ids_json or [],
                    },
                )
            )

        for hit in ideas[:limit]:
            other = hit.item
            rows.append(
                self._row(
                    source_type="idea",
                    source_id=other.id,
                    title=other.title,
                    overlap_score=hit.score,
                    shared_terms=hit.matched_terms,
                    relevance="Nearest generated idea in the local idea bank.",
                    differentiator=(
                        "Separate the hypothesis, method knob, dataset, or metric so the two "
                        "ideas do not compete for the same novelty claim."
                    ),
                    metadata={
                        "status": other.status,
                        "version": other.version,
                        "parent_idea_id": other.parent_idea_id or "",
                    },
                )
            )

        for item in literature_items[:limit]:
            rows.append(self._literature_row(item, idea))

        rows.sort(key=lambda row: float(row["overlap_score"]), reverse=True)
        return rows[: max(8, limit * 2)]

    def _literature_row(self, item: LiteratureSearchItem, idea: Idea) -> dict[str, Any]:
        shared_terms = self._shared_terms(
            self._build_query(idea),
            " ".join([item.title, item.abstract, item.venue]),
        )
        return self._row(
            source_type="literature",
            source_id=item.source_id,
            title=item.title,
            overlap_score=item.score,
            shared_terms=shared_terms or [item.provider],
            relevance=f"{item.provider} literature result"
            + (f" from {item.year}" if item.year else "."),
            differentiator=(
                "Use this as a nearest-work checkpoint: name the exact setting, assumption, or "
                "failure mode where the new idea differs."
            ),
            url=item.url,
            metadata={
                "provider": item.provider,
                "authors": item.authors,
                "year": item.year,
                "venue": item.venue,
                **(item.metadata or {}),
            },
        )

    def _row(
        self,
        *,
        source_type: str,
        source_id: str,
        title: str,
        overlap_score: float,
        shared_terms: list[str],
        relevance: str,
        differentiator: str,
        url: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "source_type": source_type,
            "source_id": source_id,
            "title": self._clean(title)[:260],
            "overlap_score": round(float(overlap_score), 4),
            "shared_terms": shared_terms[:12],
            "relevance": relevance,
            "differentiator": differentiator,
            "url": url,
            "metadata": metadata or {},
        }

    def _build_differentiators(self, rows: list[dict[str, Any]], idea: Idea) -> list[str]:
        if not rows:
            return [
                "Add more source papers before treating the idea as differentiated.",
                "Run external literature search and manually inspect recent surveys.",
            ]

        source_types = {row["source_type"] for row in rows}
        differentiators = [
            "Convert the novelty claim into one falsifiable sentence and compare it against the top overlap rows.",
            "Make the first experiment test the claimed difference, not only the base task performance.",
        ]
        if "idea" in source_types:
            differentiators.append(
                "Resolve overlap with nearby generated ideas by assigning each idea a distinct hypothesis and primary metric."
            )
        if "literature" in source_types:
            differentiators.append(
                "Write a related-work paragraph that names the nearest paper and the exact assumption the new idea changes."
            )
        if "gap" in source_types:
            differentiators.append(
                "Tie the idea to one mined gap, then state which part of the gap is intentionally out of scope."
            )
        if idea.datasets_json:
            differentiators.append(
                "Use the dataset choice as a differentiator only if it reveals a new failure mode or measurement protocol."
            )
        return differentiators[:6]

    def _missing_searches(
        self,
        literature: LiteratureSearchResponse,
        include_external: bool,
    ) -> list[str]:
        searches = ["semantic_scholar_citation_chaining"]
        if not self._external_provider_present(literature, "arxiv"):
            searches.append("arxiv_recent_preprints")
        searches.append("manual_survey_and_sota_table")
        if not include_external:
            searches.insert(0, "external_literature_search_not_requested")
        elif literature.external_status == "disabled":
            searches.insert(0, "external_literature_search_disabled")
        elif "rate_limited" in literature.external_status:
            searches.insert(0, f"external_literature_search_{literature.external_status}")
        elif literature.external_status.startswith("failed"):
            searches.insert(0, f"external_literature_search_{literature.external_status}")
        elif literature.external_status == "completed":
            searches.append("external_literature_search_manual_review")
        return searches

    def _external_provider_present(
        self,
        literature: LiteratureSearchResponse,
        provider: str,
    ) -> bool:
        return any(item.provider == provider for item in literature.items)

    def _summary(self, rows: list[dict[str, Any]], literature: LiteratureSearchResponse) -> str:
        if not rows:
            return (
                "No related-work rows were found in local indexes or literature search. Treat the "
                "idea as under-screened until more corpus papers and external search adapters are used."
            )
        top_types = ", ".join(sorted({row["source_type"] for row in rows}))
        return (
            f"Built {len(rows)} related-work rows across {top_types}. External literature search "
            f"status is {literature.external_status}; this matrix is an actionable screening artifact, "
            "not a final novelty proof."
        )

    def _render_markdown(
        self,
        *,
        idea: Idea,
        query: str,
        rows: list[dict[str, Any]],
        differentiators: list[str],
        missing_searches: list[str],
        checked_sources: list[str],
        summary: str,
    ) -> str:
        lines = [
            f"# Related Work Matrix: {self._clean(idea.title)}",
            "",
            f"- Idea ID: `{idea.id}`",
            "- Status: `completed_related_work_screening`",
            f"- Query: {self._clean(query)[:280]}",
            "",
            "## Summary",
            "",
            summary,
            "",
            "## Matrix",
            "",
        ]
        if rows:
            lines.extend(
                [
                    "| Source | Score | Related Work | Shared Terms | Differentiator |",
                    "| --- | ---: | --- | --- | --- |",
                ]
            )
            for row in rows:
                source = f"`{row['source_type']}` `{row['source_id']}`"
                terms = ", ".join(row["shared_terms"]) or "none"
                title = self._clean(row["title"])
                if row["url"]:
                    title = f"[{title}]({row['url']})"
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            source,
                            str(row["overlap_score"]),
                            title,
                            self._clean(terms),
                            self._clean(row["differentiator"]),
                        ]
                    )
                    + " |"
                )
        else:
            lines.append("No related-work rows found.")

        lines.extend(["", "## Differentiators", ""])
        lines.extend([f"- {self._clean(item)}" for item in differentiators])
        lines.extend(["", "## Missing Searches", ""])
        lines.extend([f"- `{self._clean(item)}`" for item in missing_searches])
        lines.extend(["", "## Checked Sources", ""])
        lines.extend([f"- `{self._clean(item)}`" for item in checked_sources])
        return "\n".join(lines).strip() + "\n"

    def _shared_terms(self, query: str, text: str) -> list[str]:
        normalized = text.lower()
        terms = []
        for token in TOKEN_RE.findall(query.lower()):
            if token in normalized and token not in terms:
                terms.append(token)
        return terms[:12]

    def _clean(self, text: str) -> str:
        return " ".join((text or "").split())
