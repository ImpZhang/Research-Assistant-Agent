# Model Provider Strategy

This project uses OpenAI-compatible model-provider settings so local, DashScope, OpenAI-compatible, or self-hosted endpoints can be swapped through environment variables.

Vector-store boundaries and Milvus/Qdrant/pgvector migration triggers are documented separately in `docs/vector_store_strategy.md`.

## Current Local Provider

The current local `.env` is intentionally untracked and should not be committed. It is configured for a DashScope-style OpenAI-compatible endpoint:

```text
MAIN_MODEL=qwen3-32b
EXTRACTION_MODEL=qwen3-32b
JUDGE_MODEL=qwen3-32b
EMBEDDER=qwen3-vl-embedding
RERANK_MODEL=qwen3-rerank
```

The shared base URL is:

```text
https://dashscope.aliyuncs.com/compatible-mode/v1
```

Keep real API keys only in `.env` or another ignored local secret file.

## Runtime Roles

| Role | Current Model | Current Code Status | Purpose |
| --- | --- | --- | --- |
| `MAIN_MODEL` | `qwen3-32b` | Wired | General structured reasoning and agent-facing generation. |
| `EXTRACTION_MODEL` | `qwen3-32b` | Wired | Paper-card extraction and structured paper understanding. |
| `JUDGE_MODEL` | `qwen3-32b` | Wired | Review, critique, readiness, and judgement-style calls. |
| `EMBEDDER` | `qwen3-vl-embedding` | Wired through provider adapter | Replace local hash embeddings for semantic retrieval when provider mode allows it. |
| `RERANK_MODEL` | `qwen3-rerank` | Wired through provider adapter | Re-rank retrieved evidence, gaps, ideas, and chunks when provider mode allows it. |

## Important Current Limitation

The retrieval implementation now supports external embedding and rerank providers. In `auto` mode, a fully configured provider is used; otherwise the system keeps the deterministic local hash embedding path and skips learned rerank. `/health/ready` reports whether each model role is configured and which retrieval provider modes are selected without exposing key values.

DashScope compatibility notes:

- Qwen3 chat completions require `enable_thinking=false` for non-streaming JSON calls; the JSON client adds this automatically for DashScope Qwen3 models.
- `qwen3-vl-embedding` is not served through the OpenAI-compatible `/embeddings` path. The embedding adapter falls back to DashScope native multimodal embedding when needed.
- `qwen3-rerank` is not served through the OpenAI-compatible `/rerank` path. The rerank adapter falls back to DashScope native text-rerank when needed.

That means:

- `qwen3-32b` can affect current structured model behavior immediately.
- `qwen3-32b` can optionally rank Advisor read-tool candidates when `tool_selection_mode="model_ranked"` is set on Advisor requests; deterministic selection remains the default and fallback.
- `qwen3-vl-embedding` can replace the local hash vectors when `RETRIEVAL_EMBEDDING_PROVIDER=auto` or `external` and the provider is fully configured.
- `qwen3-rerank` can re-rank retrieved evidence, gaps, and ideas when `RETRIEVAL_RERANK_PROVIDER=auto` or `external` and the provider is fully configured.

Provider modes:

- `auto`: use the external provider when model, base URL, and API key are configured; otherwise fall back to the local path.
- `external`: require the external provider and surface provider failures.
- `local` / `local_hash`: force deterministic local hash embeddings.
- `disabled` / `none`: disable rerank, or force local behavior for embedding where applicable.

## Text Versus Vision Embedding

For the current PDF workflow, text-only embedding is enough because the ingestion layer extracts text from PDFs, `.txt`, and `.md` files before retrieval.

Use visual/document-image embedding later when the workflow needs:

- scanned PDFs with weak text extraction;
- figures, tables, maps, or screenshots as evidence;
- geolocalization image examples;
- document-page image retrieval rather than extracted-text retrieval.

## Recommended Next Implementation

1. Add optional document-image/page-image ingestion for scanned PDFs and figure-heavy geolocalization papers.
2. Add retrieval evaluation fixtures comparing local hash, external embedding, and rerank modes.
3. Review real-paper evaluation reports from `scripts/evaluate_real_papers.py` or the Workbench Real Eval panel and turn recurring quality gaps into focused prompt/retrieval tasks.

Run `python3 scripts/check_model_provider_config.py` to inspect whether the current shell has each model role configured without printing secret values or calling providers. Add `--require-real` when you want the command to fail unless main, extraction, judge, embedding, and rerank roles are all configured.

An explicit real-provider smoke script is available at `scripts/smoke_model_providers.py`. It refuses to call providers unless `ALLOW_REAL_MODEL_PROVIDER_SMOKE=1` is set. Batch embedding is implemented for rebuilds so multiple pending texts can share one provider request.

The real-paper evaluator at `scripts/evaluate_real_papers.py` refuses to run unless `ALLOW_REAL_PAPER_EVAL=1` is set. Its default report includes a retrieval-mode comparison between the configured provider path and a local hash/no-rerank baseline for the same context queries. Local report summaries can be loaded through `/research/evaluations/real-paper/reports` and the Workbench Real Eval panel.

Latest real-provider smoke status:

- `qwen3-32b` main/extraction/judge roles: passed.
- `qwen3-vl-embedding`: passed with 2560-dimensional vectors.
- `qwen3-rerank`: passed and ranked the relevant document first in the smoke pair.

## Test Safety

Automated tests avoid real model-provider calls by forcing local/disabled retrieval provider modes unless `ALLOW_REAL_MODEL_PROVIDER_TESTS=1` is set. Provider adapter tests use monkeypatched fake clients and fake responses. Real provider tests should be explicit smoke tests only, with clear cost and rate-limit expectations.

Never print, snapshot, commit, or export real provider keys.
