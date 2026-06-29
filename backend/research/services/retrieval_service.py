from collections import Counter
from dataclasses import dataclass, field
import re
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.research.adapters.retrieval_provider_adapter import OpenAICompatibleRerankClient
from backend.research.config import settings
from backend.research.models import (
    Chunk,
    Evidence,
    Idea,
    PaperSection,
    ResearchEdge,
    ResearchGap,
    ResearchNode,
)
from backend.research.services.embedding_service import (
    LOCAL_EMBEDDING_MODEL,
    EmbeddingService,
    VectorHit,
)


TOKEN_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_\-]{2,}")
STOP_TERMS = {
    "about",
    "after",
    "against",
    "between",
    "could",
    "does",
    "from",
    "have",
    "into",
    "should",
    "than",
    "that",
    "their",
    "then",
    "there",
    "these",
    "this",
    "through",
    "using",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
}


@dataclass(frozen=True)
class QueryVariant:
    label: str
    query: str
    terms: list[str]
    weight: float = 1.0


@dataclass
class ScoredItem:
    item: Any
    score: float
    matched_terms: list[str]
    score_breakdown: dict[str, float] = field(default_factory=dict)
    context_excerpt: str = ""
    compressed_evidence: str = ""
    parent_section_title: str = ""
    source_queries: list[str] = field(default_factory=list)


@dataclass
class ContextSearchResult:
    chunks: list[ScoredItem]
    evidences: list[ScoredItem]
    gaps: list[ScoredItem]
    ideas: list[ScoredItem]
    graph_nodes: list[ResearchNode]
    graph_edges: list[ResearchEdge]
    answer_brief: str
    query_variants: list[dict[str, Any]] = field(default_factory=list)
    retrieval_diagnostics: dict[str, Any] = field(default_factory=dict)


class RetrievalService:
    def __init__(
        self,
        session: Session,
        embedding_service: EmbeddingService | None = None,
        rerank_client: OpenAICompatibleRerankClient | None = None,
        rerank_provider_mode: str | None = None,
    ):
        self.session = session
        self.embedding_service = embedding_service
        self.rerank_client = rerank_client or OpenAICompatibleRerankClient(
            model=settings.rerank_model,
            base_url=settings.rerank_binding_host,
            api_key=settings.rerank_api_key,
            path=settings.rerank_path,
            timeout=settings.model_provider_timeout_seconds,
        )
        self.rerank_provider_mode = _normalized_provider_mode(
            rerank_provider_mode or settings.retrieval_rerank_provider,
            default="auto",
        )
        self._section_cache: dict[str, PaperSection | None] = {}

    def search_context(
        self,
        query: str,
        paper_ids: list[str] | None = None,
        limit: int = 8,
        include_graph: bool = True,
        graph_edge_types: list[str] | None = None,
    ) -> ContextSearchResult:
        terms = self._terms(query)
        if not terms:
            raise ValueError("Query must contain at least one searchable term")

        limit = max(1, min(limit, 25))
        candidate_limit = max(30, min(limit * 5, 50))
        query_variants = self._query_variants(query, terms)
        compression_terms = self._compression_terms(terms, query_variants)
        embedding = self.embedding_service or EmbeddingService(self.session)
        embedding.ensure_indexed(paper_ids or [], max(800, candidate_limit * 20))
        vector_query_variants = self._vector_query_variants(embedding, query_variants)
        vector_hits = self._combined_vector_hits(
            embedding,
            vector_query_variants,
            limit=candidate_limit * 4,
            paper_ids=paper_ids or [],
        )

        chunks = self._score_chunks(terms, paper_ids or [], candidate_limit)
        evidences = self._score_evidences(terms, paper_ids or [], candidate_limit)
        gaps = self._score_gaps(terms, paper_ids or [], candidate_limit)
        ideas = self._score_ideas(terms, paper_ids or [], candidate_limit)
        chunks = self._merge_vector_hits(
            "chunk", chunks, vector_hits, paper_ids or [], candidate_limit
        )
        evidences = self._merge_vector_hits(
            "evidence", evidences, vector_hits, paper_ids or [], candidate_limit
        )
        gaps = self._merge_vector_hits("gap", gaps, vector_hits, paper_ids or [], candidate_limit)
        ideas = self._merge_vector_hits(
            "idea", ideas, vector_hits, paper_ids or [], candidate_limit
        )
        candidate_counts = {
            "chunks": len(chunks),
            "evidences": len(evidences),
            "gaps": len(gaps),
            "ideas": len(ideas),
        }
        chunks = self._rerank_scored_items("chunk", query, chunks, limit)
        evidences = self._rerank_scored_items("evidence", query, evidences, limit)
        gaps = self._rerank_scored_items("gap", query, gaps, limit)
        ideas = self._rerank_scored_items("idea", query, ideas, limit)
        self._annotate_context("chunk", chunks, compression_terms)
        self._annotate_context("evidence", evidences, compression_terms)
        self._annotate_context("gap", gaps, compression_terms)
        self._annotate_context("idea", ideas, compression_terms)

        graph_nodes: list[ResearchNode] = []
        graph_edges: list[ResearchEdge] = []
        if include_graph:
            graph_nodes, graph_edges = self._expand_graph_context(
                evidences,
                gaps,
                ideas,
                limit * 4,
                graph_edge_types=graph_edge_types or [],
            )

        return ContextSearchResult(
            chunks=chunks,
            evidences=evidences,
            gaps=gaps,
            ideas=ideas,
            graph_nodes=graph_nodes,
            graph_edges=graph_edges,
            answer_brief=self._build_answer_brief(query, chunks, evidences, gaps, ideas),
            query_variants=[
                {
                    "label": variant.label,
                    "query": variant.query,
                    "weight": variant.weight,
                }
                for variant in query_variants
            ],
            retrieval_diagnostics={
                "retrieval_method": "lexical_vector_multi_query_section_compression_rerank_graph_rag_lite_v1",
                "final_ranking_policy": "score_then_paper_section_diversity_v1",
                "candidate_limit": candidate_limit,
                "final_limit": limit,
                "query_variant_count": len(query_variants),
                "vector_query_variant_count": len(vector_query_variants),
                "vector_hit_count": len(vector_hits),
                "rerank_enabled": self._external_rerank_selected(),
                "candidate_counts_before_rerank": candidate_counts,
                "result_counts": {
                    "chunks": len(chunks),
                    "evidences": len(evidences),
                    "gaps": len(gaps),
                    "ideas": len(ideas),
                    "graph_nodes": len(graph_nodes),
                    "graph_edges": len(graph_edges),
                },
            },
        )

    def _vector_query_variants(
        self,
        embedding: EmbeddingService,
        query_variants: list[QueryVariant],
    ) -> list[QueryVariant]:
        if embedding.target_embedding_model == LOCAL_EMBEDDING_MODEL:
            return query_variants
        return query_variants[:2]

    def _combined_vector_hits(
        self,
        embedding: EmbeddingService,
        query_variants: list[QueryVariant],
        limit: int,
        paper_ids: list[str],
    ) -> list[VectorHit]:
        best_scores: dict[tuple[str, str], float] = {}
        for variant in query_variants:
            try:
                hits = embedding.search(variant.query, limit=limit, paper_ids=paper_ids)
            except Exception:
                if variant.label == "original":
                    raise
                continue
            for hit in hits:
                key = (hit.owner_type, hit.owner_id)
                weighted_score = round(hit.score * variant.weight, 4)
                if weighted_score > best_scores.get(key, 0.0):
                    best_scores[key] = weighted_score

        merged = [
            VectorHit(owner_type=owner_type, owner_id=owner_id, score=score)
            for (owner_type, owner_id), score in best_scores.items()
        ]
        merged.sort(key=lambda hit: hit.score, reverse=True)
        return merged[: max(1, min(limit, 200))]

    def _score_chunks(
        self,
        terms: list[str],
        paper_ids: list[str],
        limit: int,
    ) -> list[ScoredItem]:
        query = self.session.query(Chunk).order_by(Chunk.created_at.desc())
        if paper_ids:
            query = query.filter(Chunk.paper_id.in_(paper_ids))

        candidates = query.limit(500).all()
        scored = [
            self._score_item(
                chunk,
                terms,
                self._document_text("chunk", chunk),
            )
            for chunk in candidates
        ]
        return self._top(scored, limit)

    def _score_evidences(
        self,
        terms: list[str],
        paper_ids: list[str],
        limit: int,
    ) -> list[ScoredItem]:
        query = self.session.query(Evidence).order_by(Evidence.created_at.desc())
        if paper_ids:
            query = query.filter(Evidence.paper_id.in_(paper_ids))

        candidates = query.limit(500).all()
        scored = [
            self._score_item(
                evidence,
                terms,
                " ".join(
                    [
                        evidence.evidence_type,
                        self._document_text("evidence", evidence),
                    ]
                ),
                bonus=evidence.confidence,
            )
            for evidence in candidates
        ]
        return self._top(scored, limit)

    def _score_gaps(
        self,
        terms: list[str],
        paper_ids: list[str],
        limit: int,
    ) -> list[ScoredItem]:
        candidates = (
            self.session.query(ResearchGap).order_by(ResearchGap.created_at.desc()).limit(500).all()
        )
        if paper_ids:
            candidates = [
                gap
                for gap in candidates
                if set(gap.source_paper_ids_json or []).intersection(paper_ids)
            ]

        scored = [
            self._score_item(
                gap,
                terms,
                " ".join(
                    [
                        self._document_text("gap", gap),
                    ]
                ),
                bonus=(gap.feasibility_score or 0.0) / 10,
            )
            for gap in candidates
        ]
        return self._top(scored, limit)

    def _score_ideas(
        self,
        terms: list[str],
        paper_ids: list[str],
        limit: int,
    ) -> list[ScoredItem]:
        candidates = self.session.query(Idea).order_by(Idea.created_at.desc()).limit(500).all()
        if paper_ids:
            candidates = [
                idea
                for idea in candidates
                if set(idea.related_paper_ids_json or []).intersection(paper_ids)
            ]

        scored = [
            self._score_item(
                idea,
                terms,
                " ".join(
                    [
                        self._document_text("idea", idea),
                    ]
                ),
                bonus=(idea.score_json or {}).get("overall_score", 0.0) / 10,
            )
            for idea in candidates
        ]
        return self._top(scored, limit)

    def _expand_graph_context(
        self,
        evidences: list[ScoredItem],
        gaps: list[ScoredItem],
        ideas: list[ScoredItem],
        limit: int,
        graph_edge_types: list[str] | None = None,
    ) -> tuple[list[ResearchNode], list[ResearchEdge]]:
        evidence_ids = {scored.item.id for scored in evidences}
        canonical_keys = evidence_ids.union(scored.item.id for scored in gaps).union(
            scored.item.id for scored in ideas
        )

        seed_nodes = (
            self.session.query(ResearchNode)
            .filter(ResearchNode.canonical_key.in_(canonical_keys))
            .limit(limit)
            .all()
        )
        seed_node_ids = {node.id for node in seed_nodes}

        edge_query = self.session.query(ResearchEdge).order_by(ResearchEdge.created_at.desc())
        allowed_edge_types = sorted(
            {
                edge_type.strip()
                for edge_type in graph_edge_types or []
                if edge_type and edge_type.strip()
            }
        )
        if allowed_edge_types:
            edge_query = edge_query.filter(ResearchEdge.edge_type.in_(allowed_edge_types))

        edges_by_id: dict[str, ResearchEdge] = {}
        if seed_node_ids:
            connected_edges = (
                edge_query.filter(
                    or_(
                        ResearchEdge.source_node_id.in_(seed_node_ids),
                        ResearchEdge.target_node_id.in_(seed_node_ids),
                    )
                )
                .limit(limit)
                .all()
            )
            edges_by_id.update({edge.id: edge for edge in connected_edges})

        if len(edges_by_id) < limit and evidence_ids:
            candidate_edges = edge_query.limit(800).all()
            for edge in candidate_edges:
                if edge.id in edges_by_id:
                    continue
                edge_evidence_ids = set(edge.evidence_ids_json or [])
                if edge_evidence_ids.intersection(evidence_ids):
                    edges_by_id[edge.id] = edge
                if len(edges_by_id) >= limit:
                    break

        edges = list(edges_by_id.values())
        node_ids = set(seed_node_ids)
        for edge in edges:
            node_ids.add(edge.source_node_id)
            node_ids.add(edge.target_node_id)

        if not node_ids:
            return [], []

        nodes = (
            self.session.query(ResearchNode)
            .filter(ResearchNode.id.in_(node_ids))
            .order_by(ResearchNode.created_at.desc())
            .limit(limit)
            .all()
        )
        return nodes, edges

    def _merge_vector_hits(
        self,
        owner_type: str,
        scored: list[ScoredItem],
        vector_hits: list[VectorHit],
        paper_ids: list[str],
        limit: int,
    ) -> list[ScoredItem]:
        by_id = {item.item.id: item for item in scored}
        model_by_type = {"chunk": Chunk, "evidence": Evidence, "gap": ResearchGap, "idea": Idea}
        model = model_by_type[owner_type]

        for hit in vector_hits:
            if hit.owner_type != owner_type:
                continue
            item = self.session.get(model, hit.owner_id)
            if item is None or not self._matches_paper_filter(owner_type, item, paper_ids):
                continue

            vector_boost = round(hit.score * 3.0, 4)
            if item.id in by_id:
                current = by_id[item.id]
                current.score = round(current.score + vector_boost, 4)
                current.score_breakdown = self._with_vector_boost(
                    current.score_breakdown,
                    vector_boost,
                )
                if "vector" not in current.matched_terms:
                    current.matched_terms.append("vector")
            else:
                by_id[item.id] = ScoredItem(
                    item=item,
                    score=vector_boost,
                    matched_terms=["vector"],
                    score_breakdown={
                        "lexical": 0.0,
                        "bonus": 0.0,
                        "phrase": 0.0,
                        "vector": vector_boost,
                    },
                )

        return self._ranked(list(by_id.values()), limit)

    def _rerank_scored_items(
        self,
        owner_type: str,
        query: str,
        scored: list[ScoredItem],
        limit: int,
    ) -> list[ScoredItem]:
        if not scored or not self._external_rerank_selected():
            return self._ranked(scored, limit)

        documents = [self._document_text(owner_type, item.item) for item in scored]
        try:
            rerank_scores = self.rerank_client.rerank(
                query=query,
                documents=documents,
                top_n=len(documents),
            )
        except Exception:
            if self.rerank_provider_mode == "external":
                raise
            return scored

        by_index = {score.index: score.score for score in rerank_scores}
        updated = []
        for index, item in enumerate(scored):
            if index not in by_index:
                updated.append(item)
                continue
            rerank_boost = round(max(0.0, min(float(by_index[index]), 1.0)) * 4.0, 4)
            item.score = round(item.score + rerank_boost, 4)
            item.score_breakdown = self._with_rerank_boost(item.score_breakdown, rerank_boost)
            if "rerank" not in item.matched_terms:
                item.matched_terms.append("rerank")
            updated.append(item)
        return self._ranked(updated, limit)

    def _with_vector_boost(
        self,
        score_breakdown: dict[str, float],
        vector_boost: float,
    ) -> dict[str, float]:
        updated = self._normalized_score_breakdown(score_breakdown)
        updated["vector"] = round(updated["vector"] + vector_boost, 4)
        return updated

    def _with_rerank_boost(
        self,
        score_breakdown: dict[str, float],
        rerank_boost: float,
    ) -> dict[str, float]:
        updated = self._normalized_score_breakdown(score_breakdown)
        updated["rerank"] = round(updated.get("rerank", 0.0) + rerank_boost, 4)
        return updated

    def _normalized_score_breakdown(
        self,
        score_breakdown: dict[str, float],
    ) -> dict[str, float]:
        normalized = {
            "lexical": round(float(score_breakdown.get("lexical", 0.0)), 4),
            "bonus": round(float(score_breakdown.get("bonus", 0.0)), 4),
            "phrase": round(float(score_breakdown.get("phrase", 0.0)), 4),
            "vector": round(float(score_breakdown.get("vector", 0.0)), 4),
        }
        if "rerank" in score_breakdown:
            normalized["rerank"] = round(float(score_breakdown.get("rerank", 0.0)), 4)
        return normalized

    def _matches_paper_filter(self, owner_type: str, item: Any, paper_ids: list[str]) -> bool:
        if not paper_ids:
            return True
        if owner_type == "chunk":
            return item.paper_id in paper_ids
        if owner_type == "evidence":
            return item.paper_id in paper_ids
        if owner_type == "gap":
            return bool(set(item.source_paper_ids_json or []).intersection(paper_ids))
        if owner_type == "idea":
            return bool(set(item.related_paper_ids_json or []).intersection(paper_ids))
        return True

    def _score_item(
        self,
        item: Any,
        terms: list[str],
        text: str,
        bonus: float = 0.0,
    ) -> ScoredItem:
        normalized = text.lower()
        matched_terms = [term for term in terms if term in normalized]
        lexical_score = float(len(matched_terms))
        phrase_bonus = 2.0 if " ".join(terms) in normalized else 0.0
        score_breakdown = {
            "lexical": round(lexical_score, 4),
            "bonus": round(float(bonus), 4),
            "phrase": phrase_bonus,
            "vector": 0.0,
        }
        score = sum(score_breakdown.values())
        return ScoredItem(
            item=item,
            score=round(score, 4),
            matched_terms=matched_terms,
            score_breakdown=score_breakdown,
            source_queries=["original"],
        )

    def _top(self, scored: list[ScoredItem], limit: int) -> list[ScoredItem]:
        return self._ranked([item for item in scored if item.score > 0], limit)

    def _ranked(self, hits: list[ScoredItem], limit: int) -> list[ScoredItem]:
        ranked_hits = sorted(hits, key=self._rank_key, reverse=True)
        return self._diversity_aware_top(ranked_hits, limit)

    def _rank_key(self, scored: ScoredItem) -> tuple:
        created_at = getattr(scored.item, "created_at", None)
        created_rank = created_at.timestamp() if hasattr(created_at, "timestamp") else 0.0
        return (
            scored.score,
            len(set(scored.matched_terms)),
            created_rank,
            str(getattr(scored.item, "id", "")),
        )

    def _diversity_aware_top(self, ranked_hits: list[ScoredItem], limit: int) -> list[ScoredItem]:
        if limit <= 0:
            return []
        if len(ranked_hits) <= limit or limit < 3:
            return ranked_hits[:limit]

        paper_keys = [self._paper_diversity_key(scored.item) for scored in ranked_hits]
        section_keys = [self._section_diversity_key(scored.item) for scored in ranked_hits]
        distinct_papers = {key for key in paper_keys if key}
        distinct_sections = {key for key in section_keys if key}
        if len(distinct_papers) <= 1 and len(distinct_sections) <= 1:
            return ranked_hits[:limit]

        top_score = ranked_hits[0].score
        max_per_paper = max(2, (limit + 1) // 2)
        max_per_section = max(2, min(4, (limit + 2) // 3))
        selected: list[ScoredItem] = []
        deferred: list[ScoredItem] = []
        selected_ids: set[str] = set()
        paper_counts: Counter[str] = Counter()
        section_counts: Counter[str] = Counter()

        for scored in ranked_hits:
            item_id = str(getattr(scored.item, "id", id(scored.item)))
            paper_key = self._paper_diversity_key(scored.item)
            section_key = self._section_diversity_key(scored.item)
            paper_crowded = bool(
                paper_key and len(distinct_papers) > 1 and paper_counts[paper_key] >= max_per_paper
            )
            section_crowded = bool(
                section_key
                and len(distinct_sections) > 1
                and section_counts[section_key] >= max_per_section
            )
            below_diversity_band = bool(
                selected and not self._within_diversity_band(scored.score, top_score)
            )
            if paper_crowded or section_crowded or below_diversity_band:
                deferred.append(scored)
                continue
            selected.append(scored)
            selected_ids.add(item_id)
            if paper_key:
                paper_counts[paper_key] += 1
            if section_key:
                section_counts[section_key] += 1
            if len(selected) >= limit:
                return selected[:limit]

        for scored in deferred:
            item_id = str(getattr(scored.item, "id", id(scored.item)))
            if item_id in selected_ids:
                continue
            selected.append(scored)
            selected_ids.add(item_id)
            if len(selected) >= limit:
                break
        return selected[:limit]

    def _within_diversity_band(self, score: float, top_score: float) -> bool:
        if top_score <= 0:
            return True
        return score >= top_score - 0.75 or score >= top_score * 0.85

    def _paper_diversity_key(self, item: Any) -> str:
        paper_id = getattr(item, "paper_id", "")
        if paper_id:
            return str(paper_id)
        for attr in ("source_paper_ids_json", "related_paper_ids_json"):
            paper_ids = getattr(item, attr, None) or []
            if paper_ids:
                return "|".join(sorted(str(paper_id) for paper_id in paper_ids))
        return ""

    def _section_diversity_key(self, item: Any) -> str:
        section_id = getattr(item, "section_id", "")
        if section_id:
            return f"section:{section_id}"
        chunk_id = getattr(item, "chunk_id", "")
        if chunk_id:
            return f"chunk:{self._paper_diversity_key(item)}:{chunk_id}"
        return ""

    def _document_text(self, owner_type: str, item: Any) -> str:
        if owner_type == "chunk":
            section = self._section_for_chunk(item)
            return " ".join(
                [
                    item.chunk_id,
                    section.title if section is not None else "",
                    section.section_type if section is not None else "",
                    item.text,
                ]
            )
        if owner_type == "evidence":
            return " ".join([item.evidence_type, item.text, item.summary, item.supports])
        if owner_type == "gap":
            return " ".join(
                [
                    item.title,
                    item.description,
                    item.gap_type,
                    item.why_important,
                    item.why_unsolved,
                    " ".join(item.possible_approaches_json or []),
                ]
            )
        if owner_type == "idea":
            return " ".join(
                [
                    item.title,
                    item.research_question,
                    item.core_hypothesis,
                    item.motivation,
                    item.method_sketch,
                    item.expected_contribution,
                    item.novelty_argument,
                    " ".join(item.datasets_json or []),
                    " ".join(item.baselines_json or []),
                    " ".join(item.metrics_json or []),
                    " ".join(item.risks_json or []),
                ]
            )
        return ""

    def _annotate_context(
        self,
        owner_type: str,
        scored_items: list[ScoredItem],
        terms: list[str],
    ) -> None:
        for scored in scored_items:
            text = self._context_text(owner_type, scored.item)
            scored.context_excerpt = self._trim_context(text, 1200)
            scored.compressed_evidence = self._compress_context(text, terms)
            if owner_type == "chunk":
                section = self._section_for_chunk(scored.item)
                scored.parent_section_title = section.title if section is not None else ""

    def _context_text(self, owner_type: str, item: Any) -> str:
        if owner_type == "chunk":
            return self._chunk_section_context(item)
        return self._document_text(owner_type, item)

    def _chunk_section_context(self, chunk: Chunk) -> str:
        parts = []
        section = self._section_for_chunk(chunk)
        if section is not None:
            parts.extend([section.title, section.section_type])
        parts.append(chunk.text)
        if chunk.section_id:
            neighbors = (
                self.session.query(Chunk)
                .filter(Chunk.section_id == chunk.section_id)
                .filter(Chunk.chunk_idx >= max(0, chunk.chunk_idx - 1))
                .filter(Chunk.chunk_idx <= chunk.chunk_idx + 1)
                .order_by(Chunk.chunk_idx.asc())
                .limit(3)
                .all()
            )
            for neighbor in neighbors:
                if neighbor.id != chunk.id:
                    parts.append(neighbor.text)
        return " ".join(" ".join(parts).split())

    def _section_for_chunk(self, chunk: Chunk) -> PaperSection | None:
        if not chunk.section_id:
            return None
        if chunk.section_id not in self._section_cache:
            self._section_cache[chunk.section_id] = self.session.get(PaperSection, chunk.section_id)
        return self._section_cache[chunk.section_id]

    def _compress_context(self, text: str, terms: list[str], max_chars: int = 700) -> str:
        cleaned = " ".join((text or "").split())
        if not cleaned:
            return ""
        if not terms:
            return self._trim_context(cleaned, max_chars)
        lower_terms = [term.lower() for term in terms if term]
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", cleaned)
            if sentence.strip()
        ]
        if not sentences:
            return self._trim_context(cleaned, max_chars)

        selected = []
        for sentence in sentences:
            normalized = sentence.lower()
            if any(term in normalized for term in lower_terms):
                selected.append(sentence)
            if len(" ".join(selected)) >= max_chars:
                break
        if not selected:
            return self._trim_context(cleaned, max_chars)
        return self._trim_context(" ".join(selected), max_chars)

    def _trim_context(self, text: str, max_chars: int) -> str:
        cleaned = " ".join((text or "").split())
        if len(cleaned) <= max_chars:
            return cleaned
        return cleaned[: max_chars - 3].rstrip() + "..."

    def _external_rerank_selected(self) -> bool:
        if self.rerank_provider_mode in {"disabled", "local", "none"}:
            return False
        if self.rerank_provider_mode == "external":
            return True
        return self.rerank_client.is_configured

    def _query_variants(self, query: str, terms: list[str]) -> list[QueryVariant]:
        cleaned_query = " ".join(query.split())
        variants: list[QueryVariant] = []

        def add(label: str, variant_terms: list[str], weight: float) -> None:
            deduped_terms = self._dedupe_terms(variant_terms)
            variant_query = " ".join(deduped_terms)
            if not variant_query:
                return
            if any(existing.query == variant_query for existing in variants):
                return
            variants.append(
                QueryVariant(
                    label=label,
                    query=variant_query,
                    terms=deduped_terms,
                    weight=weight,
                )
            )

        variants.append(
            QueryVariant(label="original", query=cleaned_query, terms=terms, weight=1.0)
        )
        focused_terms = [term for term in terms if term not in STOP_TERMS]
        if len(focused_terms) >= 3 and focused_terms != terms:
            add("focused_terms", focused_terms, 0.96)

        term_set = set(terms)
        expansion_rules = [
            (
                "method_intent",
                {"method", "methods", "approach", "architecture", "framework", "model"},
                ["method", "approach", "architecture", "framework", "implementation"],
                0.9,
            ),
            (
                "benchmark_intent",
                {
                    "benchmark",
                    "dataset",
                    "datasets",
                    "evaluation",
                    "metric",
                    "metrics",
                    "experiment",
                    "experiments",
                    "result",
                    "results",
                },
                ["benchmark", "dataset", "evaluation", "metric", "result", "baseline"],
                0.92,
            ),
            (
                "limitation_intent",
                {"fail", "failure", "limitation", "limitations", "weakness", "risk", "robust"},
                ["limitation", "failure", "risk", "robustness", "generalization"],
                0.88,
            ),
            (
                "comparison_intent",
                {"compare", "comparison", "sota", "state-of-the-art", "baseline", "related"},
                ["comparison", "baseline", "related", "prior", "state-of-the-art"],
                0.88,
            ),
        ]
        for label, triggers, expansions, weight in expansion_rules:
            if term_set.intersection(triggers):
                add(label, focused_terms + expansions, weight)

        technical_terms = [
            term
            for term in focused_terms
            if any(char.isdigit() for char in term) or "-" in term or "_" in term or len(term) >= 8
        ]
        if len(technical_terms) >= 2:
            add("technical_terms", technical_terms[:12], 0.86)
        return variants[:6]

    def _compression_terms(self, terms: list[str], query_variants: list[QueryVariant]) -> list[str]:
        expanded = list(terms)
        for variant in query_variants:
            expanded.extend(term for term in variant.terms if term not in STOP_TERMS)
        return self._dedupe_terms(expanded)[:32]

    def _dedupe_terms(self, terms: list[str]) -> list[str]:
        seen = set()
        deduped = []
        for term in terms:
            cleaned = term.strip().lower()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            deduped.append(cleaned)
        return deduped

    def _terms(self, query: str) -> list[str]:
        seen = set()
        terms = []
        for token in TOKEN_RE.findall(query.lower()):
            if token not in seen:
                seen.add(token)
                terms.append(token)
        return terms

    def _build_answer_brief(
        self,
        query: str,
        chunks: list[ScoredItem],
        evidences: list[ScoredItem],
        gaps: list[ScoredItem],
        ideas: list[ScoredItem],
    ) -> str:
        if not chunks and not evidences and not gaps and not ideas:
            return f"No context matched the query: {query}"

        parts = [
            f"Matched {len(chunks)} source chunks",
            f"{len(evidences)} evidence records",
            f"{len(gaps)} gaps",
            f"and {len(ideas)} ideas",
        ]
        if chunks:
            top = chunks[0].item
            parts.append(f"Top chunk: {top.chunk_id}")
        if evidences:
            top = evidences[0].item
            parts.append(f"Top evidence type: {top.evidence_type}")
        if gaps:
            parts.append(f"Top gap: {gaps[0].item.title}")
        return " ".join(parts) + "."


def _normalized_provider_mode(value: str, default: str = "auto") -> str:
    mode = (value or default).strip().lower()
    if mode in {"auto", "external", "local", "disabled", "none"}:
        return mode
    return default
