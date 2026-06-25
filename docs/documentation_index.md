# Documentation Index

This document is the starting point for future development. Use it to find the right source of truth before changing code.

## Core Entry Points

| Document | Purpose | Read When |
| --- | --- | --- |
| `AGENTS.md` | Repository operating rules for Codex and other agents. | Before any automated work. |
| `README.md` | Product overview, capabilities, setup, and API entry points. | When orienting on the project. |
| `TODO.md` | Current prioritized follow-up list. | Before choosing the next task. |
| `docs/development_process.md` | Standard development workflow, verification ladder, and documentation policy. | Before implementing changes. |
| `docs/local_agent_distribution.md` | Personal local-agent distribution target, clone-to-run flow, and out-of-scope SaaS boundaries. | Before changing packaging, setup, deployment, auth, or project-scoping assumptions. |
| `docs/local_isolation.md` | Mac-local environment, cache, data, cleanup, and run commands. | Before running locally or installing dependencies. |
| `docs/progress_log.md` | Durable history of nontrivial work and verification. | After completing meaningful changes. |
| `scripts/check_local_agent_readiness.sh` | Read-only local-agent clone-to-run readiness check. | Before claiming a local checkout is ready to run. |
| `scripts/check_local_operational_preflight.sh` | Local deployment preflight wrapper with local strict-git alias. | Before packaging or sharing a local deployment. |
| `scripts/check_local_runtime_smoke.sh` | Transient localhost runtime smoke for health, readiness, and Workbench. | Before claiming the app starts successfully on the current machine. |
| `scripts/check_local_safe_suite.sh` | Default local focused verification suite. | Before pushing a completed implementation round. |

## Product And Architecture

| Document | Purpose |
| --- | --- |
| `docs/research_assistant_requirements.md` | Product requirements and user workflows. |
| `docs/research_assistant_technical_design.md` | Architecture, component design, API design, and technical direction. |
| `docs/user_project_scoping_design.md` | Deferred user/project scoping design and default-project compatibility boundaries. |
| `docs/workflow_queue_design.md` | Queue, job, and workflow execution design. |
| `docs/graphrag_langgraph_deerflow_evaluation.md` | GraphRAG, LangGraph, DeerFlow comparison and integration evaluation. |
| `docs/model_provider_strategy.md` | Chat, embedding, rerank, provider, and test-safety strategy. |
| `docs/real_paper_evaluation_report.md` | Real-provider, real-PDF geolocalization evaluation metrics and remaining local-product blockers. |

## Operations And Deployment

| Document | Purpose |
| --- | --- |
| `docs/deployment.md` | Runtime contract, environment variables, local deployment, optional Docker, backup/restore, MCP bridge, and Workbench access. |
| `docs/database_migration_strategy.md` | Current `create_all` behavior, migration policy, and future Alembic direction. |
| `docs/admin_authorization_policy.md` | Admin-only authorization policy for sensitive audit operations. |
| `docs/write_audit_retention_policy.md` | Write-audit retention and export rules. |
| `docs/write_operation_audit_design.md` | Write-operation audit event shape, redaction, and implementation design. |

## Evaluation And Product Evidence

| Document | Purpose |
| --- | --- |
| `docs/product_effect_report.md` | Current product-effect scorecard and demo readiness. |
| `docs/context_search_evaluation_plan.md` | Context-search evaluation fixtures and metrics. |
| `docs/demo_runbook.md` | Workbench-first demo flow and validation notes. |
| `docs/representative_paper_review.md` | Representative-paper human review protocol and records. |
| `docs/geolocalization_manual_sota_review.md` | Manual SOTA screening for geolocalization sources. |
| `docs/geolocalization_benchmark_sota_table.md` | Exact benchmark boundary table for geolocalization claims. |
| `configs/benchmark_profiles.example.json` | Template for ignored local benchmark profile overrides. |
| `scripts/benchmark_geoloc_predictions.py` | Project-local geolocalization JSONL benchmark harness. |
| `/research/ideas/{idea_id}/sota-review-package` | Runtime API that turns an idea into a persisted manual SOTA review checklist and collision package. |
| `/research/ideas/{idea_id}/sota-external-search-evidence` | Runtime API that persists local/external literature search statuses, result summaries, and signoff readiness for SOTA review queries. |
| `/research/ideas/{idea_id}/sota-signoffs` | Runtime API that records the human novelty/SOTA decision, nearest work, evidence links, benchmark links, and blockers. |
| `/research/ideas/{idea_id}/benchmark-evidence/readiness` | Runtime API that checks whether benchmark runs and comparisons are ready for manual SOTA signoff. |
| `/research/ideas/{idea_id}/benchmark-evidence/readiness/tasks` | Runtime API that turns benchmark evidence readiness actions into task-board items. |
| `/research/benchmark-profiles` | Runtime API that lists benchmark profiles, runner readiness, command templates, and missing project-local data paths. |
| `/research/experiment-plans/{plan_id}/benchmark-run` | Runtime API that records structured benchmark packets as reproducible experiment runs. |
| `/research/experiment-plans/{plan_id}/benchmark-run/execute` | Runtime API that executes a guarded local benchmark command and saves captured metrics/artifacts as an experiment run. |
| `/research/experiment-runs/compare` | Runtime API that compares two benchmark experiment runs and persists a Markdown comparison brief. |

## Handoff Documents

The `codex_handoff/` directory is historical and still useful for context. Prefer current `docs/` files for live development decisions.

| Document | Purpose |
| --- | --- |
| `codex_handoff/00_PROJECT_CONTEXT.md` | Project background and handoff assumptions. |
| `codex_handoff/01_CURRENT_STATUS.md` | Earlier current-status snapshot. |
| `codex_handoff/02_DECISIONS.md` | Historical decisions. |
| `codex_handoff/03_TODO.md` | Historical TODOs. |
| `codex_handoff/04_RUNBOOK.md` | Historical runbook. |
| `codex_handoff/05_IMPORTANT_FILES.md` | Historical important-file list. |
| `codex_handoff/06_CHAT_SUMMARY.md` | Conversation summary from prior work. |

## Documentation Update Rules

- Product behavior changes update `README.md`, requirements, and the relevant design doc.
- Runtime, deployment, secrets, storage, or backup changes update `docs/deployment.md` and `docs/local_isolation.md` when local behavior changes.
- Queue, job, or workflow execution changes update `docs/workflow_queue_design.md`.
- Database schema changes update `docs/database_migration_strategy.md`.
- Audit, authorization, or sensitive export changes update the audit/admin policy docs.
- Evaluation, scoring, or SOTA-related changes update the matching evaluation or benchmark docs.
- Nontrivial implementation rounds add a dated entry to `docs/progress_log.md`.

## Missing Or Deferred Documents

The project currently does not use `.doc` or `.docx` files for specifications. Markdown is the canonical format for development docs.

Potential future docs:

- `docs/vector_store_strategy.md` for local hash vectors, SQLite JSON vectors, Milvus/Qdrant/pgvector options, and migration triggers.
- `docs/multi_agent_architecture.md` if the project evolves from service modules plus MCP bridge into true multi-agent orchestration.
