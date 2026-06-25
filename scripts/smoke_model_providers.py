#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.research.adapters.model_adapter import OpenAICompatibleJsonClient  # noqa: E402
from backend.research.adapters.retrieval_provider_adapter import (  # noqa: E402
    OpenAICompatibleEmbeddingClient,
    OpenAICompatibleRerankClient,
)
from backend.research.config import settings  # noqa: E402


def main() -> int:
    if os.getenv("ALLOW_REAL_MODEL_PROVIDER_SMOKE") != "1":
        print(
            "Refusing to call real model providers. Set "
            "ALLOW_REAL_MODEL_PROVIDER_SMOKE=1 to run this explicit smoke test."
        )
        return 2

    checks = [
        _safe_check(
            "main",
            lambda: _smoke_json_role(
                "main",
                settings.main_model,
                settings.main_base_url,
                settings.main_api_key,
            ),
        ),
        _safe_check(
            "extraction",
            lambda: _smoke_json_role(
                "extraction",
                settings.extraction_model,
                settings.extraction_base_url,
                settings.extraction_api_key,
            ),
        ),
        _safe_check(
            "judge",
            lambda: _smoke_json_role(
                "judge",
                settings.judge_model,
                settings.judge_base_url,
                settings.judge_api_key,
            ),
        ),
        _safe_check("embedding", _smoke_embedding),
        _safe_check("rerank", _smoke_rerank),
    ]
    failed = [name for name, ok in checks if not ok]
    if failed:
        print(f"Model provider smoke failed for: {', '.join(failed)}")
        return 1
    print("Model provider smoke passed for main, extraction, judge, embedding, and rerank.")
    return 0


def _safe_check(name: str, check: Callable[[], tuple[str, bool]]) -> tuple[str, bool]:
    try:
        return check()
    except Exception as exc:
        print(f"{name}: ok=False error={_safe_exception_summary(exc)}")
        return name, False


def _safe_exception_summary(exc: Exception) -> str:
    response = getattr(exc, "response", None)
    if response is not None:
        status = getattr(response, "status_code", "unknown")
        text = (getattr(response, "text", "") or "").replace("\n", " ")[:400]
        return f"{exc.__class__.__name__}: HTTP {status}: {_redact_secret_like_text(text)}"
    return f"{exc.__class__.__name__}: {_redact_secret_like_text(str(exc)[:400])}"


def _redact_secret_like_text(text: str) -> str:
    redacted = text
    for secret in [
        settings.main_api_key,
        settings.extraction_api_key,
        settings.judge_api_key,
        settings.embedder_api_key,
        settings.rerank_api_key,
    ]:
        if secret:
            redacted = redacted.replace(secret, "[redacted]")
    return redacted


def _smoke_json_role(role: str, model: str, base_url: str, api_key: str) -> tuple[str, bool]:
    client = OpenAICompatibleJsonClient(model=model, base_url=base_url, api_key=api_key, timeout=30)
    if not client.is_configured:
        print(f"{role}: not configured")
        return role, False
    payload = client.complete_json(
        system_prompt="Return valid JSON only.",
        user_prompt=f'Return exactly this JSON object: {{"ok": true, "role": "{role}"}}',
    )
    ok = bool(payload.get("ok"))
    print(f"{role}: configured={client.is_configured} ok={ok} model={model}")
    return role, ok


def _smoke_embedding() -> tuple[str, bool]:
    client = OpenAICompatibleEmbeddingClient(
        model=settings.embedder,
        base_url=settings.embedder_base_url,
        api_key=settings.embedder_api_key,
        path=settings.embedder_path,
        timeout=30,
    )
    if not client.is_configured:
        print("embedding: not configured")
        return "embedding", False
    vectors = client.embed_texts(["research assistant retrieval smoke test"])
    ok = bool(vectors and vectors[0])
    dimension = len(vectors[0]) if ok else 0
    print(
        f"embedding: configured={client.is_configured} ok={ok} model={client.model} dimension={dimension}"
    )
    return "embedding", ok


def _smoke_rerank() -> tuple[str, bool]:
    client = OpenAICompatibleRerankClient(
        model=settings.rerank_model,
        base_url=settings.rerank_binding_host,
        api_key=settings.rerank_api_key,
        path=settings.rerank_path,
        timeout=30,
    )
    if not client.is_configured:
        print("rerank: not configured")
        return "rerank", False
    scores = client.rerank(
        query="retrieval evaluation",
        documents=[
            "Retrieval evaluation measures whether relevant context is ranked highly.",
            "A cooking recipe is unrelated to research retrieval metrics.",
        ],
        top_n=2,
    )
    ok = bool(scores)
    top = max(scores, key=lambda item: item.score) if scores else None
    print(
        "rerank: "
        f"configured={client.is_configured} ok={ok} model={client.model} "
        f"top_index={top.index if top else 'none'}"
    )
    return "rerank", ok


if __name__ == "__main__":
    sys.exit(main())
