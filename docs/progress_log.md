# Progress Log

This log records remote-first maintenance and implementation progress for Research Assistant Agent. It intentionally excludes passwords, API keys, real `.env` values, cookies, private keys, and other secret material.

## 2026-06-12 Remote Handoff Baseline

Remote source of truth:

- Path: `/home/zhangwz/Research-Assistant-Agent`
- Branch: `main`
- GitHub: `ImpZhang/Research-Assistant-Agent.git`
- Current pushed baseline after formatting: `9178e46 Format research service modules`

Remote worktree notes:

- Two historical root-level docs remain untracked and intentionally untouched:
  - `research_assistant_requirements.md`
  - `research_assistant_technical_design.md`
- `uv.lock` was restored after `uv run` changed registry URLs during verification.
- Future verification should prefer `.venv/bin/ruff` and `.venv/bin/pytest` when dependency sync is not intended.

Verification summary:

- `.venv/bin/ruff check .`: passed
- `.venv/bin/ruff format --check .`: passed after formatting six service modules
- `uv run pytest -q`: passed before formatting, `43 passed in 727.94s`
- `uv run python scripts/smoke_api.py`: passed before formatting, manifest count `114`, project bundle file count `158`

Completed maintenance:

- Formatted six research service modules.
- Committed and pushed `9178e46 Format research service modules`.

Next planned work:

1. Implement durable project bundle release review outcome signoff evidence records.
2. Add schema, routes, graph links, tool manifest entries, project bundle metadata/artifacts, Workbench controls, tests, smoke coverage, README, and docs.
3. Verify with ruff, pytest, and smoke.
4. Commit and push the completed feature.

## 2026-06-12 - Release Review Outcome Signoff Evidence

Implemented in progress:

- Added release review outcome signoff schema, API routes, tool manifest entries, graph linkage, project bundle metadata/Markdown artifacts, Workbench controls, pytest coverage, smoke coverage, README, and requirements/design documentation.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff check backend/research/routes.py backend/research/schemas.py backend/research/services/artifact_graph_service.py tests/test_app.py scripts/smoke_api.py` passed.
- `.venv/bin/ruff format --check backend/research/routes.py backend/research/schemas.py backend/research/services/artifact_graph_service.py tests/test_app.py scripts/smoke_api.py` passed after formatting touched Python files.
- Focused pytest passed: `5 passed in 474.12s`.
- Full pytest passed: `43 passed in 752.08s`.
- Smoke API passed with `tool_manifest_count=118`, `tool_bridge_count=118`, `project_bundle_file_count=166`, and deferred release review outcome signoff evidence in the project bundle summary.

Committed and pushed:

- `d2e0741 Add release review outcome signoff evidence`.

## 2026-06-12 - Workbench Pilot Launch Status

Implemented in progress:

- Added a read-only Workbench Pilot Launch panel that aggregates onboarding readiness, onboarding progress, and project cockpit state.
- Added static tests and documentation for the customer-pilot first screen.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `git --no-pager diff --check` passed.
- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_workbench_static_assets_are_served` passed: `1 passed in 3.55s`.

## 2026-06-12 - Handoff TODO Refresh

Documentation maintenance completed:

- Marked release review outcome signoff evidence as completed in `codex_handoff/03_TODO.md`.
- Recorded the first completed P3 slice and split remaining customer-pilot hardening into narrower follow-up tasks.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

## 2026-06-12 - Workbench First-Run State Helpers

Implemented in progress:

- Added Workbench helpers for API-key, network, and generic API errors.
- Routed repeated Workbench error rendering through the helper so first-run failures show actionable retry guidance.
- Added empty-state rendering for missing paper uploads and missing pilot report snapshots.
- Added static tests and documentation for the customer-pilot first-run state behavior.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `git --no-pager diff --check` passed.
- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_workbench_static_assets_are_served` passed: `1 passed in 3.56s`.

## 2026-06-12 - Pilot Deployment Checklist

Documentation maintenance completed:

- Added a customer-pilot deployment checklist covering remote git state, `.env` handling, API-key protection, persistent storage, backups, health checks, Workbench verification, MCP bridge checks, and operator approval for state-changing commands.
- Linked the checklist from README deployment notes.
- Updated handoff TODO so the next P3 slices focus on write-operation audit design and later Workbench delivery empty states.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `git --no-pager diff --check` passed.
- Documentation-only change; no service start, dependency install, or business-code test was required.


## 2026-06-12 - Write Operation Audit Design

Documentation maintenance completed:

- Added `docs/write_operation_audit_design.md` to define purpose, non-goals, event shape, capture points, JSONL-first storage, redaction rules, acceptance criteria, and open questions.
- Linked the audit design from README, requirements, technical design, and handoff TODO.
- Kept this as design-only work; no middleware, persistence, route, deployment, or service behavior changed.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `git --no-pager diff --check` passed.
- Reviewed `docs/write_operation_audit_design.md` for secret-safe redaction guidance and design-only scope.
- Documentation-only change; no service start, dependency install, or business-code test was required.

## 2026-06-12 - Workbench Delivery Empty States

Implemented in progress:

- Reused `renderWorkbenchEmpty` for workflow preconditions that require an upstream idea, proposal, task board, experiment run, evidence ledger, release note, feedback record, acceptance snapshot, review outcome, signoff evidence, bundle readiness snapshot, triage snapshot, or research plan.
- Preserved loading/creating/recording progress states on `renderResult(..., "warn")` so empty states remain distinct from in-flight work.
- Added static Workbench assertions for delivery empty-state copy.
- Updated README, requirements, technical design, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- Confirmed no old-style precondition `renderResult(..., "warn")` calls remain for `first`/`before`/`at least` workflow empty states.
- `git --no-pager diff --check` passed.
- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_workbench_static_assets_are_served` passed: `1 passed in 3.38s`.

## 2026-06-12 - Data Backup And Restore Notes

Documentation maintenance completed:

- Added `/app/data` backup/restore operator notes to `docs/deployment.md` for the compose service and Docker volume.
- Documented what the backup must include, what secrets must stay outside git/public bundles, and why cold backup is the preferred first-pilot path.
- Added restore guardrails: do not restore over a live service volume, back up current data first, and verify health/readiness/Workbench after restore.
- Linked the backup/restore notes from README and updated handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `git --no-pager diff --check` passed.
- Reviewed backup/restore examples to avoid destructive restore-over-live-volume guidance.
- Documentation-only change; no service start, Docker command, dependency install, or business-code test was required.


## 2026-06-12 - JSONL Write Operation Audit Prototype

Implemented in progress:

- Added a disabled-by-default write-operation audit middleware for non-GET `/research/*` requests.
- Added `backend/research/services/write_audit_service.py` for JSONL append, operation/entity categorization, and metadata sanitization.
- Added non-secret config placeholders in `.env.example` and deployment docs.
- Added tests proving JSONL records are written when enabled, default-disabled behavior is preserved, and API keys/request bodies are not serialized.
- Updated README, technical design, audit design, status capability, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `git --no-pager diff --check` passed.
- `.venv/bin/ruff check backend/app.py backend/research/config.py backend/research/routes.py backend/research/services/write_audit_service.py tests/test_app.py` passed.
- `.venv/bin/ruff format backend/app.py backend/research/config.py backend/research/routes.py backend/research/services/write_audit_service.py tests/test_app.py` reformatted two files.
- `.venv/bin/ruff format --check backend/app.py backend/research/config.py backend/research/routes.py backend/research/services/write_audit_service.py tests/test_app.py` passed.
- Focused pytest passed: `5 passed in 4.68s`.
- Full `tests/test_app.py` passed: `37 passed in 749.43s (0:12:29)`.


## 2026-06-12 - Workbench Delivery Control Grouping

Implemented in progress:

- Grouped the Workbench dossier controls into idea loop, task board, project delivery, and project operations action groups.
- Preserved existing element ids and JavaScript bindings while making the long delivery workflow easier to scan.
- Added responsive CSS so action groups collapse cleanly on narrow screens.
- Added static Workbench assertions for the new grouping labels.
- Updated README, technical design, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `git --no-pager diff --check` passed.
- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_workbench_static_assets_are_served` passed: `1 passed in 3.50s`.


## 2026-06-12 - Database Migration Strategy

Documentation maintenance completed:

- Added `docs/database_migration_strategy.md` to document the current SQLAlchemy `create_all` state, first-pilot schema-change policy, future Alembic direction, pre-migration checklist, SQLite constraints, acceptance criteria, and open questions.
- Linked the strategy from README, deployment checklist, technical design, and handoff TODO.
- Kept this as documentation-only work; no dependencies, migration directories, database commands, or service behavior changed.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `git --no-pager diff --check` passed.
- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format tests/test_app.py` reformatted the touched test file.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_deployment_artifacts_document_customer_runtime` passed: `1 passed in 3.12s`.

## 2026-06-12 - Upload Size And Extension Guardrails

Implemented in progress:

- Added upload extension validation before writing paper files to disk, defaulting to `.txt`, `.md`, and `.pdf`.
- Added `PAPER_UPLOAD_MAX_BYTES` with a 10 MiB default and rejection before writing oversized uploads to disk.
- Added runtime env support for `PAPER_UPLOAD_DIR`, `PAPER_UPLOAD_ALLOWED_EXTENSIONS`, and `PAPER_UPLOAD_MAX_BYTES` so pilot deployments can tune upload policy without code changes.
- Added tests for unsupported extension rejection and oversized upload rejection.
- Updated `.env.example`, deployment docs, technical design, status capability, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `git --no-pager diff --check` passed.
- `.venv/bin/ruff format backend/research/config.py backend/research/routes.py backend/research/services/document_ingestion.py tests/test_app.py` reformatted one file.
- `.venv/bin/ruff check backend/research/config.py backend/research/routes.py backend/research/services/document_ingestion.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/research/config.py backend/research/routes.py backend/research/services/document_ingestion.py tests/test_app.py` passed.
- Focused pytest passed: `5 passed in 4.85s`.
- Full `tests/test_app.py` passed: `39 passed in 737.83s (0:12:17)`.


## 2026-06-12 - API Key Fingerprints In Write Audit

Implemented in progress:

- Added short SHA-256 API-key fingerprint prefixes to write-operation audit metadata when an API key is supplied.
- Preserved secret safety by never serializing API key values, request bodies, or payload text into audit JSONL records.
- Added tests for successful authenticated writes and failed 401 writes to prove fingerprints are recorded without key disclosure.
- Updated deployment docs, audit design, technical design, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format backend/app.py tests/test_app.py` left files unchanged.
- `.venv/bin/ruff check backend/app.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/app.py tests/test_app.py` passed.
- Focused pytest passed: `4 passed in 4.27s`.
- Full `tests/test_app.py` passed: `40 passed in 750.26s (0:12:30)`.


## 2026-06-12 - Admin Authorization Policy

Implemented in progress:

- Added `docs/admin_authorization_policy.md` to define the operator-only boundary for future audit summary/export features.
- Clarified that the regular pilot API key is not admin authorization by itself because Workbench, scripts, and MCP clients may share it.
- Updated deployment, audit design, README, and handoff TODO references without adding endpoints or changing runtime behavior.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- Reviewed `docs/admin_authorization_policy.md` for secret-safe placeholder-only guidance.
- `git --no-pager diff --check` passed.
- No runtime code, dependencies, services, databases, or secret files were touched.


## 2026-06-12 - Admin-Gated Write Audit Summary

Implemented in progress:

- Added default-off `AUDIT_ADMIN_EXPORT_ENABLED` settings and `AUDIT_ADMIN_KEY_HEADER_NAME` placeholder documentation without adding real secrets.
- Added `GET /research/admin/write-audit/summary`, registered only when the admin export flag is enabled.
- Added sanitized JSONL aggregate summary logic that reports counts, status classes, routes, and recent request ids without actor labels, key fingerprints, request bodies, or raw events.
- Added tests for default-disabled behavior, normal API-key-only denial, wrong admin key denial, and successful sanitized summary output.
- Updated README, deployment notes, audit design, technical design, admin authorization policy, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format backend/app.py backend/research/config.py backend/research/routes.py backend/research/schemas.py backend/research/services/write_audit_service.py tests/test_app.py` reformatted one file, then left files unchanged on rerun.
- `.venv/bin/ruff check backend/app.py backend/research/config.py backend/research/routes.py backend/research/schemas.py backend/research/services/write_audit_service.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/app.py backend/research/config.py backend/research/routes.py backend/research/schemas.py backend/research/services/write_audit_service.py tests/test_app.py` passed.
- Focused pytest passed: `7 passed in 3.60s`.
- Full `tests/test_app.py` passed with verbose durations: `43 passed in 762.87s (0:12:42)`.


## 2026-06-12 - Upload Content Sniffing Guardrails

Implemented in progress:

- Added lightweight content sniffing before uploaded papers are written to disk.
- Rejected `.txt` and `.md` uploads that contain null bytes or are not UTF-8 text.
- Rejected `.pdf` uploads that do not start with a PDF header before invoking PDF parsing or writing the file.
- Added tests proving binary text and fake PDF uploads fail before files are persisted.
- Updated README, deployment notes, technical design, status capability, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format backend/research/services/document_ingestion.py backend/research/routes.py tests/test_app.py` reformatted one file.
- `.venv/bin/ruff check backend/research/services/document_ingestion.py backend/research/routes.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/research/services/document_ingestion.py backend/research/routes.py tests/test_app.py` passed.
- Focused pytest passed: `7 passed in 5.85s`.
- Full `tests/test_app.py` passed with verbose durations: `45 passed in 759.05s (0:12:39)`.


## 2026-06-12 - Write Audit Retention Policy

Implemented in progress:

- Added `docs/write_audit_retention_policy.md` to define first-pilot JSONL retention targets and operator raw-export workflow.
- Clarified that raw audit export remains unimplemented until the documented retention workflow is implemented in code.
- Updated README, deployment notes, audit design, admin authorization policy, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- Reviewed `docs/write_audit_retention_policy.md` for secret-safe placeholder-only guidance.
- `grep -R "write_audit_retention_policy" -n README.md docs codex_handoff/03_TODO.md` confirmed cross-document references.
- `git --no-pager diff --check` passed.
- No runtime code, dependencies, services, databases, raw audit exports, or secret files were touched.


## 2026-06-12 - Admin-Gated Write Audit Raw Export

Implemented in progress:

- Added `GET /research/admin/write-audit/export`, registered only when `AUDIT_ADMIN_EXPORT_ENABLED=true`.
- Reused the separate audit admin key gate and kept normal pilot API-key-only callers unauthorized.
- Added bounded export filters with `max_records`, `start_created_at`, and `end_created_at` query parameters.
- Re-sanitized exported events with the existing field allowlist plus metadata sensitive-key filtering before rendering JSONL.
- Added tests for default-disabled behavior, admin authorization, bounded export, time-window filtering, and secret/body/prompt exclusion.
- Updated README, deployment notes, audit design, retention policy, admin authorization policy, status capability, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format backend/app.py backend/research/routes.py backend/research/services/write_audit_service.py tests/test_app.py` reformatted one file after the export route and service changes.
- `.venv/bin/ruff check backend/app.py backend/research/routes.py backend/research/services/write_audit_service.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/app.py backend/research/routes.py backend/research/services/write_audit_service.py tests/test_app.py` passed.
- Focused pytest passed: `6 passed in 3.16s`.
- Full `tests/test_app.py` passed with verbose durations: `46 passed in 796.39s (0:13:16)`.


## 2026-06-12 - User Project Scoping Design

Implemented in progress:

- Added `docs/user_project_scoping_design.md` to define the target user, project, and membership model before migrations.
- Clarified that current `created_by`, `owner_type`, and artifact `scope` values are not authorization boundaries.
- Defined default-project compatibility, request scope resolution, API behavior, Workbench/MCP forwarding, migration sequencing, and future acceptance criteria.
- Updated README, technical design, database migration strategy, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- Reviewed `docs/user_project_scoping_design.md` for migration-safe, secret-free scoping guidance.
- `grep -R "user_project_scoping_design" -n README.md docs codex_handoff/03_TODO.md` confirmed cross-document references.
- `git --no-pager diff --check` passed.
- No runtime code, dependencies, services, databases, schema migrations, or secret files were touched.


## 2026-06-12 - Write Audit Readiness Check

Implemented in progress:

- Added `write_audit_dir` to `/health/ready` so deployments report audit persistence readiness.
- Kept audit readiness non-blocking when `WRITE_AUDIT_ENABLED=false` and checked directory creation/writability when enabled.
- Added tests for disabled and enabled audit readiness states plus the status capability flag.
- Updated README, deployment notes, technical design, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format backend/app.py backend/research/routes.py tests/test_app.py` left files unchanged.
- `.venv/bin/ruff check backend/app.py backend/research/routes.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/app.py backend/research/routes.py tests/test_app.py` passed.
- Focused pytest passed: `4 passed in 4.48s`.
- Full `tests/test_app.py` passed with verbose durations: `47 passed in 771.24s (0:12:51)`.

## 2026-06-12 - Durable Workflow Queue Design

Documentation maintenance completed:

- Added `docs/workflow_queue_design.md` to document the current FastAPI `BackgroundTasks` + `jobs` table contract and the future durable queue migration path.
- Compared DB-backed worker leasing, RQ/Redis, Celery/Dramatiq, and Temporal without adding dependencies or changing runtime behavior.
- Documented API compatibility requirements for async workflow queueing, job polling, artifact hydration, cancel, and retry.
- Recorded future job leasing, heartbeat, retry, and idempotency fields as migration-gated work.
- Updated README, technical design, and handoff TODO references.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `grep -R "workflow_queue_design" -n README.md docs/research_assistant_technical_design.md codex_handoff/03_TODO.md` confirmed cross-document references.
- Reviewed `docs/workflow_queue_design.md` for design-only scope and secret-safe operator guidance.
- `git --no-pager diff --check` passed.
- Documentation-only change; no dependency install, service start, worker start, migration, or business-code test was required.

## 2026-06-12 - Handoff TODO Consistency Refresh

Documentation maintenance completed:

- Updated Priority 3 handoff TODO to reflect that admin-gated write-audit summary and bounded raw JSONL export endpoints are already complete.
- Replaced the stale audit summary/export next slice with audit rotation/cleanup guidance gated on backup and retention decisions.
- Clarified that a checked `/data` backup script still waits for operator confirmation of deployment host and volume naming.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- Reviewed `codex_handoff/03_TODO.md` Priority 3 and Priority 4 sections for stale completed work.
- `git --no-pager diff --check` passed.
- Documentation-only change; no dependency install, service start, migration, backup command, or business-code test was required.

## 2026-06-12 - GraphRAG LangGraph DeerFlow Revisit

Documentation maintenance completed:

- Added `docs/graphrag_langgraph_deerflow_evaluation.md` to record the P6 evaluation of heavier graph retrieval and orchestration options.
- Documented current implementation boundaries: relational GraphRAG-lite nodes/edges, lexical/vector/context search, graph neighbor expansion, service-layer workflows, and placeholder LangGraph modules.
- Recommended keeping GraphRAG-lite and service-layer workflows for now, while treating full GraphRAG, deeper LangGraph runtime use, and DeerFlow as trigger-gated future options.
- Updated README, technical design, and handoff TODO references.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- Reviewed `graph_service.py`, `retrieval_service.py`, `models.py`, graph/search routes, tests, smoke coverage, and technical design references.
- `grep -R "graphrag_langgraph_deerflow_evaluation" -n README.md docs codex_handoff/03_TODO.md` confirmed cross-document references.
- `git --no-pager diff --check` passed.
- Documentation-only change; no dependency install, service start, migration, queue worker, or business-code test was required.

## 2026-06-12 - GraphRAG-Lite Stats Endpoint

Implemented in progress:

- Added `GET /research/graph/stats` for read-only GraphRAG-lite observability.
- Reported total node/edge counts, node type counts, edge type counts, orphan edge count, and duplicate edge group count.
- Added the endpoint to the stable tool manifest as `get_graph_stats` without side effects.
- Added focused test coverage and smoke API coverage for the stats endpoint.
- Updated README, technical design, P6 evaluation notes, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format backend/research/services/graph_service.py backend/research/schemas.py backend/research/routes.py tests/test_app.py scripts/smoke_api.py` left files unchanged.
- `.venv/bin/ruff check backend/research/services/graph_service.py backend/research/schemas.py backend/research/routes.py tests/test_app.py scripts/smoke_api.py` passed.
- `.venv/bin/ruff format --check backend/research/services/graph_service.py backend/research/schemas.py backend/research/routes.py tests/test_app.py scripts/smoke_api.py` passed.
- Focused pytest passed: `2 passed in 2.91s`.

## 2026-06-12 - Context Search Graph Edge Filters

Implemented in progress:

- Added optional `graph_edge_types` to `ContextSearchRequest` and `RetrievalService.search_context`.
- Kept default context search behavior unchanged when no edge type filter is supplied.
- Filtered only GraphRAG-lite neighbor expansion edges, leaving evidence, gap, idea, and vector retrieval behavior unchanged.
- Added focused test coverage for filtering context search graph edges to `paper_has_evidence`.
- Updated README, technical design, P6 evaluation notes, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format backend/research/services/retrieval_service.py backend/research/schemas.py backend/research/routes.py tests/test_app.py` reformatted two files.
- `.venv/bin/ruff check backend/research/services/retrieval_service.py backend/research/schemas.py backend/research/routes.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/research/services/retrieval_service.py backend/research/schemas.py backend/research/routes.py tests/test_app.py` passed.
- Focused pytest passed: `2 passed in 45.65s`.

## 2026-06-13 - GraphRAG-Lite Duplicate Edge Reuse

Implemented in progress:

- Updated `GraphService.create_edge` to reuse an existing edge with the same source node, target node, and edge type.
- Merged evidence ids without duplicates, merged payload metadata, and retained the higher edge weight when a duplicate write is requested.
- Added service-level test coverage proving duplicate edge writes return the same edge and do not increase row count for that source/target/type.
- Updated README, technical design, P6 evaluation notes, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format backend/research/services/graph_service.py tests/test_app.py` left files unchanged.
- `.venv/bin/ruff check backend/research/services/graph_service.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/research/services/graph_service.py tests/test_app.py` passed.
- Service-level focused pytest passed: `1 passed in 3.41s`.
- Existing GraphRAG-lite workflow link pytest passed: `1 passed in 2.58s`.

## 2026-06-13 - Context Search Ranking Tie-Breaks

Implemented in progress:

- Added stable tie-break ranking for context search results after lexical and vector scoring.
- Reused the same ranking helper for lexical-only hits and vector-merged hits.
- Same-score results now prefer more matched terms, then newer artifacts, then stable ids.
- Added focused unit coverage for the tie-break order and reran the context search graph/filter regression test.
- Updated README, technical design, P6 evaluation notes, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format backend/research/services/retrieval_service.py tests/test_app.py` left files unchanged.
- `.venv/bin/ruff check backend/research/services/retrieval_service.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/research/services/retrieval_service.py tests/test_app.py` passed.
- Focused pytest passed: `2 passed in 47.13s`.

## 2026-06-13 - Context Search Score Breakdowns

Implemented in progress:

- Added `score_breakdown` to scored evidence, gap, and idea context-search results.
- Split scores into lexical, bonus, phrase, and vector contributions.
- Reused score breakdowns for lexical-only hits and vector-merged hits.
- Added focused test coverage proving vector-backed evidence includes a positive vector contribution.
- Updated README, technical design, P6 evaluation notes, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format backend/research/services/retrieval_service.py backend/research/schemas.py backend/research/routes.py tests/test_app.py` left files unchanged.
- `.venv/bin/ruff check backend/research/services/retrieval_service.py backend/research/schemas.py backend/research/routes.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/research/services/retrieval_service.py backend/research/schemas.py backend/research/routes.py tests/test_app.py` passed.
- Focused pytest passed: `2 passed in 43.69s`.

## 2026-06-13 - Context Search Evaluation Plan

Documentation maintenance completed:

- Added `docs/context_search_evaluation_plan.md` to define retrieval calibration questions, fixture shape, metrics, scoring-change rules, and guardrails.
- Documented hit@k, MRR, graph edge hit rate, graph noise rate, score breakdown coverage, and empty-query guard checks as initial metrics.
- Clarified that future scoring changes should be evidence-led and should not use private customer data or secrets in committed fixtures.
- Updated README, technical design, and handoff TODO references.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- Reviewed `docs/context_search_evaluation_plan.md` for design-only scope and secret-safe evaluation guidance.
- `grep -R "context_search_evaluation_plan" -n README.md docs codex_handoff/03_TODO.md` confirmed cross-document references.
- `git --no-pager diff --check` passed.
- Documentation-only change; no dependency install, service start, migration, evaluation job, or business-code test was required.

## 2026-06-13 - Context Search Evaluation Fixture

Implemented in progress:

- Extended the deterministic context-search pytest fixture with retrieval evaluation metrics.
- Added helper checks for evidence hit@k, mean reciprocal rank, score breakdown coverage, graph edge hit rate, and graph noise rate.
- Verified the synthetic context-search fixture keeps expected evidence at hit@1/hit@3/hit@5 with MRR 1.0.
- Verified `paper_has_evidence` graph edge hits and zero graph noise under an edge-type filter.
- Updated README, context-search evaluation plan, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` reformatted one file.
- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- Focused pytest passed: `1 passed in 56.37s`.

## 2026-06-13 - Context Search Empty Query Guard Fixture

Implemented in progress:

- Added an `empty_query_guard_rate` helper for deterministic context-search evaluation.
- Added a fast fixture covering empty, too-short, and punctuation-only queries.
- Verified each invalid query returns HTTP 400 with the stable searchable-term error message.
- Updated README, context-search evaluation plan, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` reformatted one file.
- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- Focused pytest passed: `1 passed in 1.93s`.

## 2026-06-13 - Context Search Score Breakdown Consistency Fixture

Implemented in progress:

- Added a `score_breakdown_total_match_rate` helper for deterministic context-search evaluation.
- Extended the context-search graph fixture so every evidence/gap/idea result must have score breakdown totals matching the visible score within rounding tolerance.
- Updated README, context-search evaluation plan, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` left the file unchanged.
- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- Focused pytest passed: `1 passed in 46.22s`.

## 2026-06-13 - Context Search Graph Noise Assertion

Implemented in progress:

- Reused the existing `graph_noise_rate` helper in the filtered graph context-search fixture.
- Required filtered graph edges to report zero unrelated edge types when `graph_edge_types` is restricted to `paper_has_evidence`.
- Updated handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` left the file unchanged.
- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- Focused pytest passed: `1 passed in 47.86s`.

## 2026-06-13 - Context Search Paper Filter Fixture

Implemented in progress:

- Added an API-level `paper_filter_leak_rate` evaluation helper for context-search evidence.
- Added a deterministic two-paper fixture that proves unfiltered search can find paper A while a `paper_ids=[paper B]` search does not leak paper A evidence.
- Verified `include_graph=false` returns no graph nodes or edges in the scoped fixture.
- Updated README, context-search evaluation plan, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` left the file unchanged.
- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- Focused pytest passed: `1 passed in 25.41s`.

## 2026-06-13 - Remote Agent Handoff Index

Implemented in progress:

- Added root `AGENTS.md` with remote source-of-truth rules, safety constraints, secret handling, prohibited commands, and verification guidance.
- Added root `TODO.md` as a stable index over the detailed handoff queue and current approval-gated work.
- Linked AGENTS, TODO, `codex_handoff/03_TODO.md`, and `docs/progress_log.md` from README.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- Confirmed the known password literal is absent from `AGENTS.md`, `TODO.md`, `README.md`, and `docs/progress_log.md`.
- `git --no-pager diff --cached --check` passed with no whitespace errors.

## 2026-06-13 - Context Search Evaluation Check Script

Implemented in progress:

- Added `scripts/check_context_search_evaluations.sh` as a focused remote check for context-search evaluation fixtures.
- The script runs `.venv/bin/ruff check`, `.venv/bin/ruff format --check`, and the empty-query, paper-filter, and graph-context pytest fixtures.
- Linked the script from README repository layout and verification instructions.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- First script attempt was interrupted by an SSH connection timeout; reconnect confirmed no lingering `pytest`, `ruff`, or script process.
- Rerun `bash scripts/check_context_search_evaluations.sh` passed: `3 passed in 66.85s`.

## 2026-06-13 - Context Search Evaluation Script Coverage

Implemented in progress:

- Added the fast context-search ranking tie-break unit test to `scripts/check_context_search_evaluations.sh`.
- Kept the script scoped to existing `.venv` tools and focused pytest targets; it still does not install dependencies or start services.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_context_search_evaluations.sh` passed with the expanded target list: `4 passed in 66.02s`.

## 2026-06-13 - Context Search Evaluation Handoff Sync

Implemented in progress:

- Updated handoff TODO to make `scripts/check_context_search_evaluations.sh` the default focused check before scoring or graph-expansion changes.
- Updated the top-level TODO and context-search evaluation plan with the same script guidance.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- Reviewed the documentation diff for `TODO.md`, `codex_handoff/03_TODO.md`, and `docs/context_search_evaluation_plan.md`.
- `git --no-pager diff --check` passed with no whitespace errors.

## 2026-06-13 - Context Search Unknown Edge Filter Fixture

Implemented in progress:

- Extended the context-search graph fixture with an unknown `graph_edge_types` allowlist value.
- Verified scoped retrieval still returns evidence but graph edges stay empty instead of falling back to unrelated edge types.
- Updated the context-search evaluation plan and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_context_search_evaluations.sh` passed: `4 passed in 69.73s`.

## 2026-06-13 - Context Search Paper Filter Artifact Coverage

Implemented in progress:

- Extended the paper-filter evaluation fixture so scoped searches check gaps and ideas in addition to evidence.
- Added gap and idea paper-filter leak-rate helpers based on `source_paper_ids` and `related_paper_ids`.
- Updated the context-search evaluation plan and handoff TODO to describe artifact-level paper-filter coverage.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- First script run exposed an under-specified fixture: paper B lacked limitation/future-work evidence for gap mining.
- Added explicit `Limitations` and `Future Work` sections to the fixture paper.
- Rerun `bash scripts/check_context_search_evaluations.sh` passed: `4 passed in 68.22s`.

## 2026-06-13 - GraphRAG-Lite Check Script

Implemented in progress:

- Added `scripts/check_graph_rag_lite.sh` as a focused remote check for GraphRAG-lite duplicate-edge reuse and graph link/stat fixtures.
- Linked the script from README verification instructions and handoff TODO.
- Kept the script scoped to existing `.venv` tools and focused pytest targets; it does not install dependencies or start services.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_graph_rag_lite.sh` passed: `2 passed in 2.87s`.

## 2026-06-13 - Pilot Readiness Check Script

Implemented in progress:

- Added `scripts/check_pilot_readiness.sh` as a focused remote check for health/readiness, optional API-key guard behavior, upload guardrails, Workbench static assets, onboarding readiness, and pilot status report behavior.
- Linked the script from README verification instructions, top-level TODO, and handoff TODO.
- Kept the script scoped to existing `.venv` tools and in-process pytest targets; it does not install dependencies or start services.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_pilot_readiness.sh` passed: `13 passed in 21.89s`.

## 2026-06-13 - Remote Safe Suite Check Script

Implemented in progress:

- Added `scripts/check_remote_safe_suite.sh` as an aggregate no-service verification entrypoint.
- The suite runs pilot-readiness, GraphRAG-lite, and context-search focused checks in sequence.
- Linked the aggregate script from README verification instructions and top-level TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_remote_safe_suite.sh` passed all three focused suites: pilot readiness `13 passed in 22.48s`, GraphRAG-lite `2 passed in 2.39s`, and context search `4 passed in 67.51s`.

## 2026-06-13 - Write Audit Guardrail Check Script

Implemented in progress:

- Added `scripts/check_write_audit_guardrails.sh` as a focused remote check for JSONL write-audit sanitization, failed-key fingerprinting, default-off behavior, admin gating, sanitized summary, and bounded raw export behavior.
- Added the write-audit guardrail script to `scripts/check_remote_safe_suite.sh`.
- Linked the script from README verification instructions, top-level TODO, and handoff TODO.
- Kept the script scoped to existing `.venv` tools and in-process pytest targets; it does not read production audit logs, install dependencies, or start services.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_write_audit_guardrails.sh` passed: `7 passed in 3.81s`.
- `bash scripts/check_remote_safe_suite.sh` passed all four focused suites: pilot readiness `13 passed in 23.30s`, write audit `7 passed in 3.88s`, GraphRAG-lite `2 passed in 2.84s`, and context search `4 passed in 68.06s`.

## 2026-06-13 - Workflow Job Controls Check Script

Implemented in progress:

- Added `scripts/check_workflow_job_controls.sh` as a focused remote check for synchronous literature-to-ideas workflow artifacts, async job traces, and cancel/retry controls.
- Added the workflow job controls script to `scripts/check_remote_safe_suite.sh`.
- Linked the script from README verification instructions, top-level TODO, and handoff TODO.
- Kept the script scoped to existing `.venv` tools and in-process pytest targets; it does not install dependencies or start services.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_workflow_job_controls.sh` passed: `3 passed in 85.05s`.
- `bash scripts/check_remote_safe_suite.sh` passed all five focused suites: pilot readiness `13 passed in 22.05s`, write audit `7 passed in 3.68s`, workflow job controls `3 passed in 86.43s`, GraphRAG-lite `2 passed in 2.86s`, and context search `4 passed in 66.83s`.

## 2026-06-13 - Pilot Upload Happy-Path Check

Implemented in progress:

- Added `test_upload_text_paper` to `scripts/check_pilot_readiness.sh` so pilot-readiness checks cover both upload rejection guardrails and the valid text-upload happy path.
- Updated handoff TODO to describe the expanded upload coverage.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_pilot_readiness.sh` passed: `14 passed in 22.13s`.
- `bash scripts/check_remote_safe_suite.sh` passed all five focused suites: pilot readiness `14 passed in 21.76s`, write audit `7 passed in 3.81s`, workflow job controls `3 passed in 87.02s`, GraphRAG-lite `2 passed in 2.87s`, and context search `4 passed in 68.41s`.

## 2026-06-13 - Tool Bridge Contract Check Script

Implemented in progress:

- Added `scripts/check_tool_bridge_contracts.sh` as a focused remote check for `/research/tools/manifest`, `/research/tools/mcp-spec`, and the dependency-light MCP HTTP bridge helpers.
- Added the tool bridge contract script to `scripts/check_remote_safe_suite.sh`.
- Linked the script from README verification instructions, top-level TODO, and handoff TODO.
- Kept the script scoped to existing `.venv` tools and in-process/unit pytest targets; it does not install dependencies or start services.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_tool_bridge_contracts.sh` passed: `10 passed in 2.21s`.
- `bash scripts/check_remote_safe_suite.sh` passed all six focused suites: pilot readiness `14 passed in 24.31s`, write audit `7 passed in 3.91s`, workflow job controls `3 passed in 85.40s`, tool bridge contracts `10 passed in 2.04s`, GraphRAG-lite `2 passed in 2.85s`, and context search `4 passed in 67.07s`.

## 2026-06-13 - Deployment Contract Check Script

Implemented in progress:

- Added `scripts/check_deployment_contracts.sh` as a focused remote check for Dockerfile, docker-compose, deployment docs, migration/admin policy docs, and `.env.example` customer-runtime placeholders.
- Added the deployment contract script to `scripts/check_remote_safe_suite.sh`.
- Linked the script from README verification instructions, top-level TODO, and handoff TODO.
- Kept the script scoped to existing `.venv` tools and in-process pytest targets; it does not install dependencies, read real `.env` values, or start services.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_deployment_contracts.sh` passed: `1 passed in 1.64s`.
- `bash scripts/check_remote_safe_suite.sh` passed all seven focused suites: pilot readiness `14 passed in 25.04s`, deployment contracts `1 passed in 1.69s`, write audit `7 passed in 3.87s`, workflow job controls `3 passed in 86.54s`, tool bridge contracts `10 passed in 2.31s`, GraphRAG-lite `2 passed in 2.83s`, and context search `4 passed in 67.54s`.
