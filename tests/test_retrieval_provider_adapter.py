from __future__ import annotations

import time
from typing import Any

from backend.research.adapters import model_adapter
from backend.research.adapters import retrieval_provider_adapter as adapter
from backend.research.adapters.retrieval_provider_adapter import RerankScore
from backend.research.db import SessionLocal
from backend.research.models import Evidence, Paper, ResearchEmbedding
from backend.research.services.embedding_service import (
    EXTERNAL_EMBEDDING_BATCH_SIZE,
    EXTERNAL_EMBEDDING_MAX_TEXT_CHARS,
    EmbeddingService,
)
from backend.research.services.retrieval_service import RetrievalService


class _FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200):
        self.payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError("fake http error", response=self)
        return None

    def json(self) -> dict[str, Any]:
        return self.payload


def test_qwen3_dashscope_json_client_disables_thinking_for_non_streaming(monkeypatch) -> None:
    captured = {}

    def fake_post(url, *, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return _FakeResponse({"choices": [{"message": {"content": '{"ok": true}'}}]})

    monkeypatch.setattr(model_adapter.requests, "post", fake_post)
    client = model_adapter.OpenAICompatibleJsonClient(
        model="qwen3-32b",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="unit-test-key",
        timeout=9,
    )

    assert client.complete_json(system_prompt="Return JSON.", user_prompt="Return ok.") == {
        "ok": True
    }
    assert captured["json"]["enable_thinking"] is False
    assert captured["json"]["model"] == "qwen3-32b"


def test_embedding_client_parses_openai_compatible_embeddings(monkeypatch) -> None:
    captured = {}

    def fake_post(url, *, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return _FakeResponse(
            {
                "data": [
                    {"index": 1, "embedding": [0.0, 1.0]},
                    {"index": 0, "embedding": [1.0, 0.0]},
                ]
            }
        )

    monkeypatch.setattr(adapter.requests, "post", fake_post)
    client = adapter.OpenAICompatibleEmbeddingClient(
        model="fake-embedding",
        base_url="https://provider.example/v1/",
        api_key="unit-test-key",
        timeout=12,
    )

    vectors = client.embed_texts(["alpha", "beta"])

    assert captured["url"] == "https://provider.example/v1/embeddings"
    assert captured["json"] == {"model": "fake-embedding", "input": ["alpha", "beta"]}
    assert captured["headers"]["Authorization"] == "Bearer unit-test-key"
    assert captured["timeout"] == 12
    assert vectors == [[1.0, 0.0], [0.0, 1.0]]


def test_embedding_client_falls_back_to_dashscope_multimodal_endpoint(monkeypatch) -> None:
    calls = []

    def fake_post(url, *, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        if len(calls) == 1:
            return _FakeResponse({"error": {"message": "unsupported"}}, status_code=404)
        vector = [0.1, 0.2] if len(calls) == 2 else [0.3, 0.4]
        return _FakeResponse({"output": {"embeddings": [{"embedding": vector}]}})

    monkeypatch.setattr(adapter.requests, "post", fake_post)
    client = adapter.OpenAICompatibleEmbeddingClient(
        model="multimodal-embedding-v1",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="unit-test-key",
    )

    vectors = client.embed_texts(["alpha", "beta"])

    assert calls[0]["url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
    assert (
        calls[1]["url"]
        == "https://dashscope.aliyuncs.com/api/v1/services/embeddings/multimodal-embedding/multimodal-embedding"
    )
    assert calls[1]["json"] == {
        "model": "multimodal-embedding-v1",
        "input": {"contents": [{"text": "alpha"}]},
    }
    assert calls[2]["json"] == {
        "model": "multimodal-embedding-v1",
        "input": {"contents": [{"text": "beta"}]},
    }
    assert vectors == [[0.1, 0.2], [0.3, 0.4]]


def test_embedding_client_falls_back_to_dashscope_text_embedding_endpoint(monkeypatch) -> None:
    calls = []

    def fake_post(url, *, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        if len(calls) == 1:
            return _FakeResponse({"error": {"message": "bad request"}}, status_code=400)
        return _FakeResponse(
            {
                "output": {
                    "embeddings": [
                        {"text_index": 1, "embedding": [0.3, 0.4]},
                        {"text_index": 0, "embedding": [0.1, 0.2]},
                    ]
                }
            }
        )

    monkeypatch.setattr(adapter.requests, "post", fake_post)
    client = adapter.OpenAICompatibleEmbeddingClient(
        model="text-embedding-v1",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="unit-test-key",
    )

    vectors = client.embed_texts(["alpha", "beta"])

    assert calls[0]["url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
    assert (
        calls[1]["url"]
        == "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
    )
    assert calls[1]["json"] == {
        "model": "text-embedding-v1",
        "input": {"texts": ["alpha", "beta"]},
    }
    assert vectors == [[0.1, 0.2], [0.3, 0.4]]


def test_rerank_client_parses_common_rerank_results(monkeypatch) -> None:
    captured = {}

    def fake_post(url, *, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return _FakeResponse(
            {
                "output": {
                    "results": [
                        {"index": 1, "relevance_score": 0.95},
                        {"index": 0, "relevance_score": 0.15},
                    ]
                }
            }
        )

    monkeypatch.setattr(adapter.requests, "post", fake_post)
    client = adapter.OpenAICompatibleRerankClient(
        model="fake-rerank",
        base_url="https://provider.example/v1",
        api_key="unit-test-key",
        path="rerank",
        timeout=7,
    )

    scores = client.rerank(query="alpha", documents=["doc-a", "doc-b"], top_n=2)

    assert captured["url"] == "https://provider.example/v1/rerank"
    assert captured["json"] == {
        "model": "fake-rerank",
        "query": "alpha",
        "documents": ["doc-a", "doc-b"],
        "top_n": 2,
        "return_documents": False,
    }
    assert captured["headers"]["Authorization"] == "Bearer unit-test-key"
    assert captured["timeout"] == 7
    assert scores == [RerankScore(index=1, score=0.95), RerankScore(index=0, score=0.15)]


def test_rerank_client_falls_back_to_dashscope_text_rerank_endpoint(monkeypatch) -> None:
    calls = []

    def fake_post(url, *, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        if len(calls) == 1:
            return _FakeResponse({"error": {"message": "not found"}}, status_code=404)
        return _FakeResponse(
            {
                "output": {
                    "results": [
                        {"index": 0, "relevance_score": 0.8},
                        {"index": 1, "relevance_score": 0.1},
                    ]
                }
            }
        )

    monkeypatch.setattr(adapter.requests, "post", fake_post)
    client = adapter.OpenAICompatibleRerankClient(
        model="qwen3-rerank",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="unit-test-key",
    )

    scores = client.rerank(query="alpha", documents=["alpha document", "beta"], top_n=2)

    assert calls[0]["url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1/rerank"
    assert (
        calls[1]["url"]
        == "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"
    )
    assert calls[1]["json"] == {
        "model": "qwen3-rerank",
        "input": {"query": "alpha", "documents": ["alpha document", "beta"]},
        "parameters": {"top_n": 2, "return_documents": False},
    }
    assert scores == [RerankScore(index=0, score=0.8), RerankScore(index=1, score=0.1)]


def test_embedding_service_uses_external_provider_and_skips_unchanged_text() -> None:
    class FakeEmbeddingClient:
        model = "fake-external-embedding"
        is_configured = True

        def __init__(self) -> None:
            self.calls: list[list[str]] = []

        def embed_texts(self, texts: list[str]) -> list[list[float]]:
            self.calls.append(list(texts))
            return [[1.0, 0.0, 0.0] for _ in texts]

    marker = f"externalembedding{time.time_ns()}"
    fake_client = FakeEmbeddingClient()
    session = SessionLocal()
    try:
        paper = Paper(
            title=f"External Embedding Provider Paper {marker}",
            filename="external_embedding_provider.txt",
            source_type="pytest",
            status="indexed",
        )
        session.add(paper)
        session.flush()
        evidence = Evidence(
            paper_id=paper.id,
            evidence_type="provider_fixture",
            text=f"{marker} evidence text",
            summary=f"{marker} evidence summary",
            supports=f"{marker} evidence support",
            confidence=0.5,
        )
        second_evidence = Evidence(
            paper_id=paper.id,
            evidence_type="provider_fixture",
            text=f"{marker} second evidence text",
            summary=f"{marker} second evidence summary",
            supports=f"{marker} second evidence support",
            confidence=0.4,
        )
        session.add_all([evidence, second_evidence])
        session.commit()

        service = EmbeddingService(
            session,
            embedding_client=fake_client,
            embedding_provider_mode="external",
        )
        first = service.rebuild_index(
            owner_types=["evidence"],
            paper_ids=[paper.id],
            limit=10,
        )
        second = service.rebuild_index(
            owner_types=["evidence"],
            paper_ids=[paper.id],
            limit=10,
        )
        cached_evidence = Evidence(
            paper_id=paper.id,
            evidence_type="provider_fixture",
            text=evidence.text,
            summary=evidence.summary,
            supports=evidence.supports,
            confidence=0.3,
        )
        session.add(cached_evidence)
        session.commit()
        third = service.rebuild_index(
            owner_types=["evidence"],
            paper_ids=[paper.id],
            limit=10,
        )

        rows = (
            session.query(ResearchEmbedding)
            .filter(
                ResearchEmbedding.embedding_model == "fake-external-embedding",
                ResearchEmbedding.owner_id.in_(
                    [evidence.id, second_evidence.id, cached_evidence.id]
                ),
            )
            .all()
        )
        assert first.model == "fake-external-embedding"
        assert first.dimension == 3
        assert first.evidence_count == 2
        assert second.model == "fake-external-embedding"
        assert second.dimension == 3
        assert second.evidence_count == 2
        assert third.model == "fake-external-embedding"
        assert third.dimension == 3
        assert third.evidence_count == 3
        assert len(fake_client.calls) == 1
        assert len(fake_client.calls[0]) == 2
        assert all(marker in text for text in fake_client.calls[0])
        assert len(rows) == 3
        assert {row.dimension for row in rows} == {3}
        assert {tuple(row.vector_json) for row in rows} == {(1.0, 0.0, 0.0)}
    finally:
        session.rollback()
        session.query(ResearchEmbedding).filter(
            ResearchEmbedding.embedding_model == "fake-external-embedding"
        ).delete(synchronize_session=False)
        session.query(Evidence).filter(Evidence.text.like(f"%{marker}%")).delete(
            synchronize_session=False
        )
        session.query(Paper).filter(Paper.title.like(f"%{marker}%")).delete(
            synchronize_session=False
        )
        session.commit()
        session.close()


def test_embedding_service_batches_and_truncates_external_provider_text() -> None:
    class FakeEmbeddingClient:
        model = "fake-external-embedding"
        is_configured = True

        def __init__(self) -> None:
            self.calls: list[list[str]] = []

        def embed_texts(self, texts: list[str]) -> list[list[float]]:
            self.calls.append(list(texts))
            return [[1.0, 0.0] for _ in texts]

    fake_client = FakeEmbeddingClient()
    session = SessionLocal()
    try:
        service = EmbeddingService(
            session,
            embedding_client=fake_client,
            embedding_provider_mode="external",
        )
        long_text = "x" * (EXTERNAL_EMBEDDING_MAX_TEXT_CHARS + 50)
        text_count = EXTERNAL_EMBEDDING_BATCH_SIZE + 1

        embeddings = service.embed_texts_results([long_text, *[f"short {idx}" for idx in range(8)]])

        assert len(embeddings) == text_count
        assert len(fake_client.calls) == 2
        assert len(fake_client.calls[0]) == EXTERNAL_EMBEDDING_BATCH_SIZE
        assert len(fake_client.calls[0][0]) == EXTERNAL_EMBEDDING_MAX_TEXT_CHARS
        assert fake_client.calls[1] == ["short 7"]
    finally:
        session.close()


def test_retrieval_service_applies_external_reranker_to_candidates() -> None:
    class FakeRerankClient:
        is_configured = True

        def rerank(self, *, query: str, documents: list[str], top_n: int | None = None):
            assert query == marker
            assert top_n == len(documents)
            return [
                RerankScore(index=0, score=0.0),
                RerankScore(index=1, score=1.0),
            ]

    marker = f"rerankprovider{time.time_ns()}"
    session = SessionLocal()
    try:
        paper = Paper(
            title=f"Rerank Provider Paper {marker}",
            filename="rerank_provider.txt",
            source_type="pytest",
            status="indexed",
        )
        session.add(paper)
        session.flush()
        lower_relevance = Evidence(
            paper_id=paper.id,
            evidence_type="rerank_fixture",
            text=f"{marker} lower relevance candidate",
            summary=f"{marker} lower relevance summary",
            supports=f"{marker} lower relevance support",
            confidence=0.9,
        )
        higher_relevance = Evidence(
            paper_id=paper.id,
            evidence_type="rerank_fixture",
            text=f"{marker} higher relevance candidate",
            summary=f"{marker} higher relevance summary",
            supports=f"{marker} higher relevance support",
            confidence=0.0,
        )
        session.add_all([lower_relevance, higher_relevance])
        session.commit()

        result = RetrievalService(
            session,
            embedding_service=EmbeddingService(session, embedding_provider_mode="local"),
            rerank_client=FakeRerankClient(),
            rerank_provider_mode="external",
        ).search_context(
            query=marker,
            paper_ids=[paper.id],
            limit=2,
            include_graph=False,
        )

        assert result.evidences[0].item.id == higher_relevance.id
        assert "rerank" in result.evidences[0].matched_terms
        assert result.evidences[0].score_breakdown["rerank"] == 4.0
        assert (
            round(sum(result.evidences[0].score_breakdown.values()), 4) == result.evidences[0].score
        )
    finally:
        session.rollback()
        owner_ids = [item.id for item in [lower_relevance, higher_relevance] if item.id]
        if owner_ids:
            session.query(ResearchEmbedding).filter(
                ResearchEmbedding.owner_id.in_(owner_ids)
            ).delete(synchronize_session=False)
            session.query(Evidence).filter(Evidence.id.in_(owner_ids)).delete(
                synchronize_session=False
            )
        session.query(Paper).filter(Paper.title.like(f"%{marker}%")).delete(
            synchronize_session=False
        )
        session.commit()
        session.close()
