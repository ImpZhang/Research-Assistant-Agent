from dataclasses import dataclass
import hashlib
import logging
import math
import re
from typing import Any

from sqlalchemy.orm import Session

from backend.research.adapters.retrieval_provider_adapter import OpenAICompatibleEmbeddingClient
from backend.research.config import settings
from backend.research.models import Chunk, Evidence, Idea, ResearchEmbedding, ResearchGap


TOKEN_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_\-]{2,}")
LOCAL_EMBEDDING_MODEL = "local_hash_embedding_v0"
LOCAL_EMBEDDING_DIMENSION = 128
logger = logging.getLogger(__name__)


@dataclass
class EmbeddingRebuildStats:
    model: str
    dimension: int
    indexed_count: int
    chunk_count: int
    evidence_count: int
    gap_count: int
    idea_count: int


@dataclass
class VectorHit:
    owner_type: str
    owner_id: str
    score: float


@dataclass
class TextEmbedding:
    model: str
    dimension: int
    vector: list[float]
    provider: str


@dataclass
class EmbeddingInput:
    owner_type: str
    owner_id: str
    text: str
    payload: dict[str, Any]


class EmbeddingService:
    def __init__(
        self,
        session: Session,
        embedding_client: OpenAICompatibleEmbeddingClient | None = None,
        embedding_provider_mode: str | None = None,
    ):
        self.session = session
        self.embedding_client = embedding_client or OpenAICompatibleEmbeddingClient(
            model=settings.embedder,
            base_url=settings.embedder_base_url,
            api_key=settings.embedder_api_key,
            path=settings.embedder_path,
            timeout=settings.model_provider_timeout_seconds,
        )
        self.embedding_provider_mode = _normalized_provider_mode(
            embedding_provider_mode or settings.retrieval_embedding_provider,
            default="auto",
        )
        self._last_embedding_model = self.target_embedding_model
        self._last_embedding_dimension = self.target_embedding_dimension

    def rebuild_index(
        self,
        owner_types: list[str] | None = None,
        paper_ids: list[str] | None = None,
        limit: int = 500,
    ) -> EmbeddingRebuildStats:
        owner_types = owner_types or ["chunk", "evidence", "gap", "idea"]
        limit = max(1, min(limit, 2000))

        chunk_count = 0
        evidence_count = 0
        gap_count = 0
        idea_count = 0
        if "chunk" in owner_types:
            chunk_count = self._index_chunks(paper_ids or [], limit)
        if "evidence" in owner_types:
            evidence_count = self._index_evidences(paper_ids or [], limit)
        if "gap" in owner_types:
            gap_count = self._index_gaps(paper_ids or [], limit)
        if "idea" in owner_types:
            idea_count = self._index_ideas(paper_ids or [], limit)

        self.session.commit()
        indexed_count = chunk_count + evidence_count + gap_count + idea_count
        return EmbeddingRebuildStats(
            model=self._last_embedding_model,
            dimension=self._last_embedding_dimension,
            indexed_count=indexed_count,
            chunk_count=chunk_count,
            evidence_count=evidence_count,
            gap_count=gap_count,
            idea_count=idea_count,
        )

    def ensure_indexed(
        self, paper_ids: list[str] | None = None, limit: int = 500
    ) -> EmbeddingRebuildStats:
        return self.rebuild_index(paper_ids=paper_ids, limit=limit)

    def search(
        self,
        query: str,
        owner_types: list[str] | None = None,
        limit: int = 12,
        paper_ids: list[str] | None = None,
    ) -> list[VectorHit]:
        query_embedding = self.embed_text_result(query)
        owner_types = owner_types or ["chunk", "evidence", "gap", "idea"]
        paper_ids = paper_ids or []
        rows = (
            self.session.query(ResearchEmbedding)
            .filter(ResearchEmbedding.owner_type.in_(owner_types))
            .filter(ResearchEmbedding.embedding_model == query_embedding.model)
            .order_by(ResearchEmbedding.updated_at.desc())
            .limit(2000)
            .all()
        )
        hits = []
        for row in rows:
            if paper_ids and not self._matches_paper_filter(row, paper_ids):
                continue
            score = self.cosine_similarity(query_embedding.vector, row.vector_json or [])
            if score <= 0:
                continue
            hits.append(
                VectorHit(owner_type=row.owner_type, owner_id=row.owner_id, score=round(score, 4))
            )

        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[: max(1, min(limit, 100))]

    @property
    def target_embedding_model(self) -> str:
        if self._external_embedding_selected():
            return self.embedding_client.model
        return LOCAL_EMBEDDING_MODEL

    @property
    def target_embedding_dimension(self) -> int:
        return 0 if self._external_embedding_selected() else LOCAL_EMBEDDING_DIMENSION

    def _matches_paper_filter(self, row: ResearchEmbedding, paper_ids: list[str]) -> bool:
        payload = row.payload_json or {}
        if row.owner_type == "chunk":
            return payload.get("paper_id") in paper_ids
        if row.owner_type == "evidence":
            return payload.get("paper_id") in paper_ids
        if row.owner_type == "gap":
            return bool(set(payload.get("source_paper_ids") or []).intersection(paper_ids))
        if row.owner_type == "idea":
            return bool(set(payload.get("related_paper_ids") or []).intersection(paper_ids))
        return True

    def embed_text(self, text: str) -> list[float]:
        return self.embed_text_result(text).vector

    def embed_text_result(self, text: str) -> TextEmbedding:
        return self.embed_texts_results([text])[0]

    def embed_texts_results(self, texts: list[str]) -> list[TextEmbedding]:
        if self._external_embedding_selected():
            try:
                vectors = self.embedding_client.embed_texts([text or "" for text in texts])
                if len(vectors) != len(texts):
                    raise ValueError("Embedding provider returned an unexpected vector count.")
                return [
                    TextEmbedding(
                        model=self.embedding_client.model,
                        dimension=len(vector),
                        vector=vector,
                        provider="external",
                    )
                    for vector in vectors
                ]
            except Exception:
                if self.embedding_provider_mode == "external":
                    raise
                logger.warning(
                    "External embedding provider failed; falling back to local hash",
                    exc_info=False,
                )

        return [
            TextEmbedding(
                model=LOCAL_EMBEDDING_MODEL,
                dimension=LOCAL_EMBEDDING_DIMENSION,
                vector=self._embed_text_local(text),
                provider="local_hash",
            )
            for text in texts
        ]

    def _embed_text_local(self, text: str) -> list[float]:
        vector = [0.0 for _ in range(LOCAL_EMBEDDING_DIMENSION)]
        for token in TOKEN_RE.findall((text or "").lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % LOCAL_EMBEDDING_DIMENSION
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [round(value / norm, 6) for value in vector]

    def cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right:
            return 0.0
        width = min(len(left), len(right))
        return sum(left[idx] * right[idx] for idx in range(width))

    def _index_chunks(self, paper_ids: list[str], limit: int) -> int:
        query = self.session.query(Chunk).order_by(Chunk.updated_at.desc())
        if paper_ids:
            query = query.filter(Chunk.paper_id.in_(paper_ids))
        inputs = []
        for chunk in query.limit(limit).all():
            if not (chunk.text or "").strip():
                continue
            inputs.append(
                EmbeddingInput(
                    owner_type="chunk",
                    owner_id=chunk.id,
                    text=" ".join([chunk.chunk_id, chunk.text]),
                    payload={
                        "paper_id": chunk.paper_id,
                        "section_id": chunk.section_id,
                        "chunk_id": chunk.chunk_id,
                        "page_number": chunk.page_number,
                        "chunk_idx": chunk.chunk_idx,
                        "chunk_level": chunk.chunk_level,
                    },
                )
            )
        self._upsert_embeddings(inputs)
        return len(inputs)

    def _index_evidences(self, paper_ids: list[str], limit: int) -> int:
        query = self.session.query(Evidence).order_by(Evidence.updated_at.desc())
        if paper_ids:
            query = query.filter(Evidence.paper_id.in_(paper_ids))
        inputs = []
        for evidence in query.limit(limit).all():
            inputs.append(
                EmbeddingInput(
                    owner_type="evidence",
                    owner_id=evidence.id,
                    text=" ".join(
                        [
                            evidence.evidence_type,
                            evidence.summary,
                            evidence.text,
                            evidence.supports,
                        ]
                    ),
                    payload={
                        "paper_id": evidence.paper_id,
                        "evidence_type": evidence.evidence_type,
                    },
                )
            )
        self._upsert_embeddings(inputs)
        return len(inputs)

    def _index_gaps(self, paper_ids: list[str], limit: int) -> int:
        candidates = (
            self.session.query(ResearchGap)
            .order_by(ResearchGap.updated_at.desc())
            .limit(limit)
            .all()
        )
        inputs = []
        for gap in candidates:
            if paper_ids and not set(gap.source_paper_ids_json or []).intersection(paper_ids):
                continue
            inputs.append(
                EmbeddingInput(
                    owner_type="gap",
                    owner_id=gap.id,
                    text=" ".join(
                        [
                            gap.title,
                            gap.description,
                            gap.gap_type,
                            gap.why_important,
                            gap.why_unsolved,
                            " ".join(gap.possible_approaches_json or []),
                        ]
                    ),
                    payload={
                        "source_paper_ids": gap.source_paper_ids_json or [],
                        "gap_type": gap.gap_type,
                    },
                )
            )
        self._upsert_embeddings(inputs)
        return len(inputs)

    def _index_ideas(self, paper_ids: list[str], limit: int) -> int:
        candidates = self.session.query(Idea).order_by(Idea.updated_at.desc()).limit(limit).all()
        inputs = []
        for idea in candidates:
            if paper_ids and not set(idea.related_paper_ids_json or []).intersection(paper_ids):
                continue
            inputs.append(
                EmbeddingInput(
                    owner_type="idea",
                    owner_id=idea.id,
                    text=" ".join(
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
                    payload={
                        "related_paper_ids": idea.related_paper_ids_json or [],
                        "status": idea.status,
                    },
                )
            )
        self._upsert_embeddings(inputs)
        return len(inputs)

    def _upsert_embedding(
        self, owner_type: str, owner_id: str, text: str, payload: dict[str, Any]
    ) -> None:
        self._upsert_embeddings(
            [EmbeddingInput(owner_type=owner_type, owner_id=owner_id, text=text, payload=payload)]
        )

    def _upsert_embeddings(self, inputs: list[EmbeddingInput]) -> None:
        if not inputs:
            return

        target_model = self.target_embedding_model
        rows = (
            self.session.query(ResearchEmbedding)
            .filter(
                ResearchEmbedding.owner_type.in_([item.owner_type for item in inputs]),
                ResearchEmbedding.owner_id.in_([item.owner_id for item in inputs]),
                ResearchEmbedding.embedding_model == target_model,
            )
            .all()
        )
        rows_by_key = {(row.owner_type, row.owner_id): row for row in rows}
        pending = []
        for item in inputs:
            text_hash = hashlib.sha256((item.text or "").encode("utf-8")).hexdigest()
            row = rows_by_key.get((item.owner_type, item.owner_id))
            if row is not None and row.text_hash == text_hash and row.vector_json:
                row.payload_json = item.payload
                self._last_embedding_model = row.embedding_model
                self._last_embedding_dimension = row.dimension
                continue
            pending.append((item, text_hash, row))

        if not pending:
            return

        embeddings = self.embed_texts_results([item.text for item, _, _ in pending])
        for (item, text_hash, row), embedding in zip(pending, embeddings, strict=True):
            self._upsert_embedding_result(item, text_hash, embedding, row)

    def _upsert_embedding_result(
        self,
        item: EmbeddingInput,
        text_hash: str,
        embedding: TextEmbedding,
        row: ResearchEmbedding | None,
    ) -> None:
        if row is None or row.embedding_model != embedding.model:
            row = (
                self.session.query(ResearchEmbedding)
                .filter(
                    ResearchEmbedding.owner_type == item.owner_type,
                    ResearchEmbedding.owner_id == item.owner_id,
                    ResearchEmbedding.embedding_model == embedding.model,
                )
                .one_or_none()
            )
        if row is None:
            row = ResearchEmbedding(
                owner_type=item.owner_type,
                owner_id=item.owner_id,
                embedding_model=embedding.model,
                dimension=embedding.dimension,
            )
            self.session.add(row)

        row.text_hash = text_hash
        row.dimension = embedding.dimension
        row.vector_json = embedding.vector
        row.payload_json = item.payload
        self._last_embedding_model = embedding.model
        self._last_embedding_dimension = embedding.dimension

    def _external_embedding_selected(self) -> bool:
        if self.embedding_provider_mode in {"disabled", "local", "local_hash"}:
            return False
        if self.embedding_provider_mode == "external":
            return True
        return self.embedding_client.is_configured


def _normalized_provider_mode(value: str, default: str = "auto") -> str:
    mode = (value or default).strip().lower()
    if mode in {"auto", "external", "local", "local_hash", "disabled"}:
        return mode
    return default
