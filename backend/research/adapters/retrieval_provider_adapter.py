from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class RerankScore:
    index: int
    score: float


class OpenAICompatibleEmbeddingClient:
    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key: str,
        path: str = "/embeddings",
        timeout: float = 60,
    ):
        self.model = model
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key
        self.path = _normalize_path(path)
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self.model and self.base_url and self.api_key)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not self.is_configured:
            raise RuntimeError("Embedding client is not configured.")
        if not texts:
            return []
        if self._uses_dashscope_multimodal_embedding():
            return self._embed_texts_dashscope_multimodal(texts)

        try:
            response = requests.post(
                f"{self.base_url}{self.path}",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model, "input": texts},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            if self._should_fallback_to_dashscope_multimodal(exc):
                return self._embed_texts_dashscope_multimodal(texts)
            raise
        return _parse_embedding_vectors(response.json())

    def _uses_dashscope_multimodal_embedding(self) -> bool:
        return "multimodal-embedding" in self.path

    def _should_fallback_to_dashscope_multimodal(self, exc: requests.HTTPError) -> bool:
        response = getattr(exc, "response", None)
        if response is None or response.status_code not in {400, 404}:
            return False
        model = self.model.lower()
        return "dashscope.aliyuncs.com" in self.base_url and (
            "vl-embedding" in model or model.startswith("multimodal-embedding")
        )

    def _embed_texts_dashscope_multimodal(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            response = requests.post(
                (
                    f"{_dashscope_native_base_url(self.base_url)}"
                    "/api/v1/services/embeddings/multimodal-embedding/multimodal-embedding"
                ),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": {
                        "contents": [{"text": text or ""}],
                    },
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            parsed = _parse_embedding_vectors(response.json())
            if not parsed:
                raise ValueError("DashScope multimodal embedding returned no vectors.")
            vectors.append(parsed[0])
        return vectors


class OpenAICompatibleRerankClient:
    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key: str,
        path: str = "/rerank",
        timeout: float = 60,
    ):
        self.model = model
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key
        self.path = _normalize_path(path)
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self.model and self.base_url and self.api_key)

    def rerank(
        self, *, query: str, documents: list[str], top_n: int | None = None
    ) -> list[RerankScore]:
        if not self.is_configured:
            raise RuntimeError("Rerank client is not configured.")
        if not documents:
            return []
        if self._uses_dashscope_text_rerank():
            return self._rerank_dashscope_text(query=query, documents=documents, top_n=top_n)

        try:
            response = requests.post(
                f"{self.base_url}{self.path}",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "query": query,
                    "documents": documents,
                    "top_n": top_n or len(documents),
                    "return_documents": False,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            if self._should_fallback_to_dashscope_text_rerank(exc):
                return self._rerank_dashscope_text(query=query, documents=documents, top_n=top_n)
            raise
        return _parse_rerank_scores(response.json())

    def _uses_dashscope_text_rerank(self) -> bool:
        return "text-rerank" in self.path

    def _should_fallback_to_dashscope_text_rerank(self, exc: requests.HTTPError) -> bool:
        response = getattr(exc, "response", None)
        if response is None or response.status_code not in {400, 404}:
            return False
        return "dashscope.aliyuncs.com" in self.base_url and "rerank" in self.model.lower()

    def _rerank_dashscope_text(
        self,
        *,
        query: str,
        documents: list[str],
        top_n: int | None = None,
    ) -> list[RerankScore]:
        response = requests.post(
            (
                f"{_dashscope_native_base_url(self.base_url)}"
                "/api/v1/services/rerank/text-rerank/text-rerank"
            ),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "input": {
                    "query": query,
                    "documents": documents,
                },
                "parameters": {
                    "top_n": top_n or len(documents),
                    "return_documents": False,
                },
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return _parse_rerank_scores(response.json())


def _normalize_path(path: str) -> str:
    cleaned = (path or "").strip()
    if not cleaned:
        return ""
    return cleaned if cleaned.startswith("/") else f"/{cleaned}"


def _dashscope_native_base_url(base_url: str) -> str:
    marker = "/compatible-mode"
    if marker in base_url:
        return base_url.split(marker, 1)[0]
    return base_url.rstrip("/")


def _parse_embedding_vectors(payload: dict[str, Any]) -> list[list[float]]:
    raw_items = payload.get("data")
    if raw_items is None:
        raw_items = payload.get("embeddings")
    if raw_items is None and isinstance(payload.get("output"), dict):
        raw_items = payload["output"].get("embeddings")
    if not isinstance(raw_items, list):
        raise ValueError("Embedding response did not include a supported embeddings list.")

    indexed_items = []
    for fallback_index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            raise ValueError("Embedding response item was not an object.")
        vector = item.get("embedding") or item.get("vector")
        if not isinstance(vector, list):
            raise ValueError("Embedding response item did not include an embedding vector.")
        index = item.get("index", item.get("text_index", fallback_index))
        indexed_items.append((int(index), [float(value) for value in vector]))

    indexed_items.sort(key=lambda pair: pair[0])
    return [vector for _, vector in indexed_items]


def _parse_rerank_scores(payload: dict[str, Any]) -> list[RerankScore]:
    raw_results = payload.get("results")
    if raw_results is None and isinstance(payload.get("output"), dict):
        raw_results = payload["output"].get("results")
    if raw_results is None and isinstance(payload.get("data"), list):
        raw_results = payload["data"]
    if not isinstance(raw_results, list):
        raise ValueError("Rerank response did not include a supported results list.")

    scores = []
    for fallback_index, item in enumerate(raw_results):
        if not isinstance(item, dict):
            raise ValueError("Rerank response item was not an object.")
        index = int(item.get("index", item.get("document_index", fallback_index)))
        raw_score = item.get("relevance_score", item.get("score"))
        if raw_score is None:
            raise ValueError("Rerank response item did not include a relevance score.")
        scores.append(RerankScore(index=index, score=float(raw_score)))
    return scores
