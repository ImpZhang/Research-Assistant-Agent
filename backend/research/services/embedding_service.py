from dataclasses import dataclass
import hashlib
import math
import re
from typing import Any

from sqlalchemy.orm import Session

from backend.research.models import Evidence, Idea, ResearchEmbedding, ResearchGap


TOKEN_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_\-]{2,}")
LOCAL_EMBEDDING_MODEL = "local_hash_embedding_v0"
LOCAL_EMBEDDING_DIMENSION = 128


@dataclass
class EmbeddingRebuildStats:
    model: str
    dimension: int
    indexed_count: int
    evidence_count: int
    gap_count: int
    idea_count: int


@dataclass
class VectorHit:
    owner_type: str
    owner_id: str
    score: float


class EmbeddingService:
    def __init__(self, session: Session):
        self.session = session

    def rebuild_index(
        self,
        owner_types: list[str] | None = None,
        paper_ids: list[str] | None = None,
        limit: int = 500,
    ) -> EmbeddingRebuildStats:
        owner_types = owner_types or ["evidence", "gap", "idea"]
        limit = max(1, min(limit, 2000))

        evidence_count = 0
        gap_count = 0
        idea_count = 0
        if "evidence" in owner_types:
            evidence_count = self._index_evidences(paper_ids or [], limit)
        if "gap" in owner_types:
            gap_count = self._index_gaps(paper_ids or [], limit)
        if "idea" in owner_types:
            idea_count = self._index_ideas(paper_ids or [], limit)

        self.session.commit()
        indexed_count = evidence_count + gap_count + idea_count
        return EmbeddingRebuildStats(
            model=LOCAL_EMBEDDING_MODEL,
            dimension=LOCAL_EMBEDDING_DIMENSION,
            indexed_count=indexed_count,
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
    ) -> list[VectorHit]:
        query_vector = self.embed_text(query)
        owner_types = owner_types or ["evidence", "gap", "idea"]
        rows = (
            self.session.query(ResearchEmbedding)
            .filter(ResearchEmbedding.owner_type.in_(owner_types))
            .order_by(ResearchEmbedding.updated_at.desc())
            .limit(2000)
            .all()
        )
        hits = []
        for row in rows:
            score = self.cosine_similarity(query_vector, row.vector_json or [])
            if score <= 0:
                continue
            hits.append(
                VectorHit(owner_type=row.owner_type, owner_id=row.owner_id, score=round(score, 4))
            )

        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[: max(1, min(limit, 100))]

    def embed_text(self, text: str) -> list[float]:
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

    def _index_evidences(self, paper_ids: list[str], limit: int) -> int:
        query = self.session.query(Evidence).order_by(Evidence.updated_at.desc())
        if paper_ids:
            query = query.filter(Evidence.paper_id.in_(paper_ids))
        count = 0
        for evidence in query.limit(limit).all():
            self._upsert_embedding(
                owner_type="evidence",
                owner_id=evidence.id,
                text=" ".join(
                    [evidence.evidence_type, evidence.summary, evidence.text, evidence.supports]
                ),
                payload={"paper_id": evidence.paper_id, "evidence_type": evidence.evidence_type},
            )
            count += 1
        return count

    def _index_gaps(self, paper_ids: list[str], limit: int) -> int:
        candidates = (
            self.session.query(ResearchGap)
            .order_by(ResearchGap.updated_at.desc())
            .limit(limit)
            .all()
        )
        count = 0
        for gap in candidates:
            if paper_ids and not set(gap.source_paper_ids_json or []).intersection(paper_ids):
                continue
            self._upsert_embedding(
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
            count += 1
        return count

    def _index_ideas(self, paper_ids: list[str], limit: int) -> int:
        candidates = self.session.query(Idea).order_by(Idea.updated_at.desc()).limit(limit).all()
        count = 0
        for idea in candidates:
            if paper_ids and not set(idea.related_paper_ids_json or []).intersection(paper_ids):
                continue
            self._upsert_embedding(
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
            count += 1
        return count

    def _upsert_embedding(
        self, owner_type: str, owner_id: str, text: str, payload: dict[str, Any]
    ) -> None:
        text_hash = hashlib.sha256((text or "").encode("utf-8")).hexdigest()
        row = (
            self.session.query(ResearchEmbedding)
            .filter(
                ResearchEmbedding.owner_type == owner_type,
                ResearchEmbedding.owner_id == owner_id,
                ResearchEmbedding.embedding_model == LOCAL_EMBEDDING_MODEL,
            )
            .one_or_none()
        )
        vector = self.embed_text(text)
        if row is None:
            row = ResearchEmbedding(
                owner_type=owner_type,
                owner_id=owner_id,
                embedding_model=LOCAL_EMBEDDING_MODEL,
                dimension=LOCAL_EMBEDDING_DIMENSION,
            )
            self.session.add(row)

        row.text_hash = text_hash
        row.vector_json = vector
        row.payload_json = payload
