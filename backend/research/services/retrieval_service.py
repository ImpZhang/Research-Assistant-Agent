from dataclasses import dataclass
import re
from typing import Any

from sqlalchemy.orm import Session

from backend.research.models import Evidence, Idea, ResearchEdge, ResearchGap, ResearchNode
from backend.research.services.embedding_service import EmbeddingService, VectorHit


TOKEN_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_\-]{2,}")


@dataclass
class ScoredItem:
    item: Any
    score: float
    matched_terms: list[str]


@dataclass
class ContextSearchResult:
    evidences: list[ScoredItem]
    gaps: list[ScoredItem]
    ideas: list[ScoredItem]
    graph_nodes: list[ResearchNode]
    graph_edges: list[ResearchEdge]
    answer_brief: str


class RetrievalService:
    def __init__(self, session: Session):
        self.session = session

    def search_context(
        self,
        query: str,
        paper_ids: list[str] | None = None,
        limit: int = 8,
        include_graph: bool = True,
    ) -> ContextSearchResult:
        terms = self._terms(query)
        if not terms:
            raise ValueError("Query must contain at least one searchable term")

        limit = max(1, min(limit, 25))
        embedding = EmbeddingService(self.session)
        embedding.ensure_indexed(paper_ids or [], 800)
        vector_hits = embedding.search(query, limit=limit * 6)

        evidences = self._score_evidences(terms, paper_ids or [], limit)
        gaps = self._score_gaps(terms, paper_ids or [], limit)
        ideas = self._score_ideas(terms, paper_ids or [], limit)
        evidences = self._merge_vector_hits(
            "evidence", evidences, vector_hits, paper_ids or [], limit
        )
        gaps = self._merge_vector_hits("gap", gaps, vector_hits, paper_ids or [], limit)
        ideas = self._merge_vector_hits("idea", ideas, vector_hits, paper_ids or [], limit)

        graph_nodes: list[ResearchNode] = []
        graph_edges: list[ResearchEdge] = []
        if include_graph:
            graph_nodes, graph_edges = self._expand_graph_context(evidences, gaps, ideas, limit * 4)

        return ContextSearchResult(
            evidences=evidences,
            gaps=gaps,
            ideas=ideas,
            graph_nodes=graph_nodes,
            graph_edges=graph_edges,
            answer_brief=self._build_answer_brief(query, evidences, gaps, ideas),
        )

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
                        evidence.text,
                        evidence.summary,
                        evidence.supports,
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
                        gap.title,
                        gap.description,
                        gap.gap_type,
                        gap.why_important,
                        gap.why_unsolved,
                        " ".join(gap.possible_approaches_json or []),
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
                        idea.title,
                        idea.research_question,
                        idea.core_hypothesis,
                        idea.motivation,
                        idea.method_sketch,
                        idea.expected_contribution,
                        idea.novelty_argument,
                        " ".join(idea.datasets_json or []),
                        " ".join(idea.baselines_json or []),
                        " ".join(idea.metrics_json or []),
                        " ".join(idea.risks_json or []),
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

        candidate_edges = (
            self.session.query(ResearchEdge)
            .order_by(ResearchEdge.created_at.desc())
            .limit(800)
            .all()
        )
        edges = []
        for edge in candidate_edges:
            edge_evidence_ids = set(edge.evidence_ids_json or [])
            if (
                edge.source_node_id in seed_node_ids
                or edge.target_node_id in seed_node_ids
                or edge_evidence_ids.intersection(evidence_ids)
            ):
                edges.append(edge)
            if len(edges) >= limit:
                break

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
        model_by_type = {"evidence": Evidence, "gap": ResearchGap, "idea": Idea}
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
                if "vector" not in current.matched_terms:
                    current.matched_terms.append("vector")
            else:
                by_id[item.id] = ScoredItem(
                    item=item,
                    score=vector_boost,
                    matched_terms=["vector"],
                )

        merged = list(by_id.values())
        merged.sort(key=lambda item: item.score, reverse=True)
        return merged[:limit]

    def _matches_paper_filter(self, owner_type: str, item: Any, paper_ids: list[str]) -> bool:
        if not paper_ids:
            return True
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
        score = float(len(matched_terms)) + bonus
        if " ".join(terms) in normalized:
            score += 2.0
        return ScoredItem(item=item, score=round(score, 4), matched_terms=matched_terms)

    def _top(self, scored: list[ScoredItem], limit: int) -> list[ScoredItem]:
        hits = [item for item in scored if item.score > 0]
        hits.sort(key=lambda item: item.score, reverse=True)
        return hits[:limit]

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
        evidences: list[ScoredItem],
        gaps: list[ScoredItem],
        ideas: list[ScoredItem],
    ) -> str:
        if not evidences and not gaps and not ideas:
            return f"No context matched the query: {query}"

        parts = [
            f"Matched {len(evidences)} evidence records",
            f"{len(gaps)} gaps",
            f"and {len(ideas)} ideas",
        ]
        if evidences:
            top = evidences[0].item
            parts.append(f"Top evidence type: {top.evidence_type}")
        if gaps:
            parts.append(f"Top gap: {gaps[0].item.title}")
        return " ".join(parts) + "."
