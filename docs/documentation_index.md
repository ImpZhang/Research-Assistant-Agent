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
| `scripts/check_local_doctor.sh` | Combined local diagnostics for readiness, model-provider config, backup manifest, SQLite maintenance, and geoloc benchmark readiness. | After clone/setup or before asking for help with local setup. |
| `scripts/check_local_geoloc_benchmark_smoke.sh` | Temporary-fixture geolocalization benchmark smoke for the local JSONL scoring harness. | Before claiming the benchmark harness works in a fresh local checkout. |
| `scripts/check_local_operational_preflight.sh` | Local deployment preflight wrapper with local strict-git alias. | Before packaging or sharing a local deployment. |
| `scripts/check_local_runtime_smoke.sh` | Transient localhost runtime smoke for health, readiness, and Workbench. | Before claiming the app starts successfully on the current machine. |
| `scripts/check_local_safe_suite.sh` | Default local focused verification suite. | Before pushing a completed implementation round. |
| `scripts/check_model_provider_config.py` | No-network model-provider environment readiness check that does not print secrets. | Before running the opt-in real-provider smoke or diagnosing local model setup. |
| `scripts/check_single_user_docker_deployment.py` | Static single-user Docker deployment contract check for Dockerfile, compose, dockerignore, env template, and deployment docs. | Before changing optional Docker packaging or deployment docs. |
| `scripts/build_local_backup_manifest.py` | Read-only aggregate manifest for local data backup scope, counts, sizes, and excluded secret files. | Before backing up or moving a local checkout's data. |
| `scripts/rehearse_local_backup_restore.py` | Synthetic backup/restore rehearsal that validates archive, restore, manifest comparison, and secret-exclusion logic without copying live local data. | Before changing backup, restore, packaging, or local handoff behavior. |
| `scripts/check_sqlite_maintenance.py` | Read-only SQLite maintenance report for database size, sidecars, table counts, vector-index counts, trace counts, and safe recommendations. | Before SQLite troubleshooting, approved maintenance, or local handoff. |
| `scripts/check_migration_baseline.py` | SQLAlchemy metadata drift check against the committed migration baseline. | Before changing models or migration policy. |
| `scripts/run_workflow_worker.py` | Optional local SQLite worker that consumes queued workflow jobs when `WORKFLOW_BACKGROUND_TASKS_ENABLED=false`. | When running long async workflows outside the API process. |

## Product And Architecture

| Document | Purpose |
| --- | --- |
| `docs/research_assistant_requirements.md` | Product requirements and user workflows. |
| `docs/research_assistant_technical_design.md` | Architecture, component design, API design, and technical direction. |
| `docs/agent_engineering_strengthening_plan.md` | Agent trace, tool calling, skills, replay, LangGraph, and local-deployment strengthening roadmap. |
| `docs/user_project_scoping_design.md` | Deferred user/project scoping design and default-project compatibility boundaries. |
| `docs/workflow_queue_design.md` | Queue, job, and workflow execution design. |
| `docs/graphrag_langgraph_deerflow_evaluation.md` | GraphRAG, LangGraph, DeerFlow comparison and integration evaluation. |
| `docs/model_provider_strategy.md` | Chat, embedding, rerank, provider, and test-safety strategy. |
| `docs/project_skill_registry.md` | Project-local skill registry for paper ingestion, context search, workflows, SOTA review, benchmarks, and Advisor action sessions. |
| `docs/real_paper_evaluation_report.md` | Real-provider, real-PDF geolocalization evaluation metrics and remaining local-product blockers. |

## Operations And Deployment

| Document | Purpose |
| --- | --- |
| `docs/deployment.md` | Runtime contract, environment variables, local deployment, optional Docker, backup/restore, MCP bridge, and Workbench access. |
| `docs/model_provider_strategy.md` | Model-role wiring, provider modes, real-provider smoke policy, and retrieval-provider expectations. |
| `docs/vector_store_strategy.md` | Current SQLite vector-row baseline, optional provider embeddings/rerank, and migration triggers for Milvus/Qdrant/pgvector. |
| `docs/database_migration_strategy.md` | Current `create_all` behavior, migration policy, and future Alembic direction. |
| `docs/admin_authorization_policy.md` | Admin-only authorization policy for sensitive audit operations. |
| `docs/write_audit_retention_policy.md` | Write-audit retention and export rules. |
| `docs/write_operation_audit_design.md` | Write-operation audit event shape, redaction, and implementation design. |

## Evaluation And Product Evidence

| Document | Purpose |
| --- | --- |
| `docs/product_effect_report.md` | Current product-effect scorecard and demo readiness. |
| `docs/context_search_evaluation_plan.md` | Context-search evaluation fixtures and metrics. |
| `docs/agent_replay_eval.md` | Bad-case replay script, metrics, report shape, and deterministic local evaluation policy. |
| `docs/demo_runbook.md` | Workbench-first demo flow and validation notes. |
| `docs/representative_paper_review.md` | Representative-paper human review protocol and records. |
| `docs/geolocalization_manual_sota_review.md` | Manual SOTA screening for geolocalization sources. |
| `docs/geolocalization_benchmark_sota_table.md` | Exact benchmark boundary table for geolocalization claims. |
| `configs/benchmark_profiles.example.json` | Template for ignored local benchmark profile overrides. |
| `scripts/prepare_local_geoloc_benchmark.py` | Local helper for benchmark directories, example JSONL files, ignored profile manifests, and readiness checks. |
| `scripts/benchmark_geoloc_predictions.py` | Project-local geolocalization JSONL benchmark harness. |
| `scripts/run_geoloc_benchmark_pipeline.py` | Local pipeline that turns geolocalization ground-truth/prediction JSONL artifacts into JSON/Markdown benchmark reports. |
| `scripts/check_local_geoloc_benchmark_smoke.sh` | One-command local smoke for the geolocalization JSONL benchmark path. |
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

- `docs/multi_agent_architecture.md` if the project evolves from service modules plus MCP bridge into true multi-agent orchestration.
