# Local Personal Agent Distribution

This document defines the current product target: Research Assistant Agent is distributed as a personal, local-deployable agent project. Each operator clones the GitHub repository, creates a local `.env`, supplies their own model provider keys, and runs the backend, Workbench, and optional MCP bridge on their own machine.

## Target Shape

- Distribution: public or private GitHub repository clone.
- Runtime: local FastAPI backend plus browser Workbench.
- Agent interface: Workbench first, with optional HTTP API, scripts, and MCP bridge.
- Storage: project-local SQLite database, uploaded papers, benchmark datasets, predictions, generated dossiers, logs, and caches.
- Secrets: untracked local `.env` files only; committed files contain placeholders and examples.
- Model access: each user configures their own OpenAI-compatible chat, extraction, judge, embedding, and rerank endpoints.
- Benchmarking: local benchmark commands run only when explicitly enabled and use project-local `data/` and `outputs/` paths.

This target does not require a central system access key, centralized user accounts, hosted tenant isolation, billing, SSO, or a shared production server.

## Clone-To-Run Flow

1. Clone `ImpZhang/Research-Assistant-Agent.git`.
2. Enter the project root and keep all generated artifacts inside that root.
3. Create `.env` from `.env.example`; do not commit `.env`.
4. Fill model provider keys only in `.env`.
5. Run `./scripts/setup-local.sh` with a local Python 3.12+ interpreter.
6. Run `source scripts/env.sh`.
7. Run `bash scripts/check_local_agent_readiness.sh`.
8. Start the app with `./scripts/run-local.sh`.
9. Open `http://127.0.0.1:8000/workbench`.
10. Optionally run `bash scripts/check_local_runtime_smoke.sh` for a transient health/readiness/Workbench check.
11. Optionally run `bash scripts/check_local_geoloc_benchmark_smoke.sh` to verify the project-local geolocalization JSONL benchmark path with temporary fixtures.
12. Run `bash scripts/check_local_safe_suite.sh` before sharing changes.

## Required Local Artifacts

- `.venv/` for Python dependencies.
- `.cache/` for tool and package caches.
- `data/` for SQLite data, uploaded papers, local datasets, and service state.
- `models/` for manually downloaded model weights if any are used.
- `outputs/` for evaluations, predictions, benchmark runs, and exported dossiers.
- `logs/` for local runtime logs.
- `.docker/` for project-scoped Docker metadata when Docker is used.

These paths are ignored or treated as local artifacts according to `docs/local_isolation.md`.

## Model Roles

The current model-provider split is:

- `MAIN_*`: general reasoning and idea generation.
- `EXTRACTION_*`: structured paper-card extraction.
- `JUDGE_*`: review, scoring, and evaluator-style judgments.
- `EMBEDDER_*`: optional learned embedding provider for retrieval.
- `RERANK_*`: optional learned rerank provider for retrieval ranking.

The same chat model can back `MAIN_*`, `EXTRACTION_*`, and `JUDGE_*` for a personal deployment. A separate embedding model is needed for learned vector retrieval. A separate rerank model is recommended for realistic retrieval quality but is not required for deterministic fallback mode.

## Current Reality Level

The project is already more than a basic RAG demo:

- It has a structured literature-to-ideas workflow.
- It stores research artifacts, task boards, graph links, evidence ledgers, decisions, and exportable dossiers.
- It supports model-provider configuration, deterministic fallbacks, local benchmark profiles, benchmark execution, comparison briefs, and SOTA signoff readiness.
- It includes a local geolocalization benchmark smoke so clone users can verify the JSONL metric path before adding real benchmark datasets and predictions.
- It has Workbench and MCP bridge surfaces for local agent-style operation.

It is not yet a finished polished local product. The remaining local-agent work is mostly packaging, preflight quality, real-data evaluation, better local prediction pipelines, and user-facing simplification rather than SaaS multi-user engineering.

## Explicitly Out Of Scope For Now

- Multi-user account management.
- Tenant or organization isolation.
- Central admin console for hosted customers.
- Billing, SSO, managed cloud deployment, or shared production operations.
- Mandatory Milvus, Qdrant, pgvector, or other external vector database services.
- Remote server or SSH-based default workflow.

Project/user scoping docs remain as deferred design notes only. They should not drive current implementation unless the product target changes.

## Next Engineering Priorities

1. Make clone-to-run setup and local preflight feel boring and reliable.
2. Keep `.env.example`, setup scripts, and local isolation docs aligned with the real run path.
3. Improve real-provider and real-paper evaluation with saved reports under `outputs/`.
4. Add practical local benchmark recipes, including real geolocalization prediction generation where applicable.
5. Improve Workbench flow for a single researcher using the tool repeatedly.
6. Keep optional Docker compose single-user and project-scoped; do not make it the default path.
7. Add a vector-store strategy only when local SQLite/hash retrieval plus provider embeddings become a measurable bottleneck.
