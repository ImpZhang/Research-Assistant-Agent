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

## 2026-06-13 - Pilot First-Run Readiness Coverage

Implemented in progress:

- Expanded `scripts/check_pilot_readiness.sh` from 14 to 18 pytest targets.
- Added existing first-run setup wizard, onboarding task creation, onboarding progress, and pilot report snapshot/export/comparison coverage to the focused pilot-readiness check.
- Updated README, top-level TODO, and handoff TODO so the script is the default check before changing setup wizard, onboarding, pilot report, upload, API-key, or Workbench first-run behavior.
- Kept the work scoped to existing `.venv` tools and in-process pytest targets; it does not install dependencies or start services.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_pilot_readiness.sh` passed: `18 passed in 56.48s`.
- `bash scripts/check_remote_safe_suite.sh` passed all seven focused suites: pilot readiness `18 passed in 55.80s`, deployment contracts `1 passed in 1.65s`, write audit `7 passed in 3.97s`, workflow job controls `3 passed in 85.72s`, tool bridge contracts `10 passed in 2.17s`, GraphRAG-lite `2 passed in 2.93s`, and context search `4 passed in 68.14s`.

## 2026-06-13 - Research Workflow Primitive Check Script

Implemented in progress:

- Added `scripts/check_research_workflow_primitives.sh` as a focused remote check for deterministic local literature search, provider parsers, paper-card extraction, gap mining, idea generation, review/experiment planning, novelty screening, related-work matrices, and Markdown dossier exports.
- Added the research workflow primitive script to `scripts/check_remote_safe_suite.sh`.
- Linked the script from README verification instructions, top-level TODO, and handoff TODO.
- Kept the script scoped to existing `.venv` tools and in-process pytest targets; it does not install dependencies, start services, or require external API access.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_research_workflow_primitives.sh` passed: `10 passed in 65.83s`.
- `bash scripts/check_remote_safe_suite.sh` passed all eight focused suites: pilot readiness `18 passed in 57.19s`, deployment contracts `1 passed in 1.71s`, research workflow primitives `10 passed in 67.80s`, write audit `7 passed in 4.18s`, workflow job controls `3 passed in 86.09s`, tool bridge contracts `10 passed in 2.19s`, GraphRAG-lite `2 passed in 2.91s`, and context search `4 passed in 63.99s`.

## 2026-06-13 - Research Planning Contract Check Script

Implemented in progress:

- Added `scripts/check_research_planning_contracts.sh` as a focused remote check for research profiles, profile-aware advisor briefs, research plans, plan tasks/progress, idea refinement, ranking, portfolios, agenda exports, and lineage/bundle planning metadata.
- Added the research planning contract script to `scripts/check_remote_safe_suite.sh`.
- Linked the script from README verification instructions, top-level TODO, and handoff TODO.
- Kept the script scoped to existing `.venv` tools and in-process pytest targets; it does not install dependencies, start services, or require external API access.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_research_planning_contracts.sh` passed: `3 passed in 68.06s`.
- `bash scripts/check_remote_safe_suite.sh` passed all nine focused suites: pilot readiness `18 passed in 57.17s`, deployment contracts `1 passed in 1.39s`, research workflow primitives `10 passed in 67.82s`, research planning contracts `3 passed in 68.48s`, write audit `7 passed in 3.96s`, workflow job controls `3 passed in 85.59s`, tool bridge contracts `10 passed in 2.20s`, GraphRAG-lite `2 passed in 2.93s`, and context search `4 passed in 68.69s`.

## 2026-06-13 - Proposal Contract Check And Scoped Vector Search

Implemented in progress:

- Added `scripts/check_research_proposal_contracts.sh` as a focused remote check for proposal drafts, readiness reviews, proposal revisions, revision follow-up tasks, and proposal Markdown exports.
- Kept the proposal check separate from `scripts/check_remote_safe_suite.sh` because the current deep proposal chain is long-running.
- Fixed scoped context search so vector hits are filtered by `paper_ids` before scoring instead of taking a small global vector top-k and filtering afterward.
- Expanded `scripts/check_context_search_evaluations.sh` ruff coverage to include `backend/research/services/retrieval_service.py` and `backend/research/services/embedding_service.py`.
- Updated README, top-level TODO, and handoff TODO with the proposal check entry.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_research_proposal_contracts.sh` passed: `1 passed in 486.71s`.
- `bash scripts/check_context_search_evaluations.sh` passed after the scoped vector-search fix: `4 passed in 73.68s`.
- `bash scripts/check_remote_safe_suite.sh` passed all nine default focused suites without the long proposal check: pilot readiness `18 passed in 58.56s`, deployment contracts `1 passed in 1.76s`, research workflow primitives `10 passed in 67.91s`, research planning contracts `3 passed in 66.68s`, write audit `7 passed in 3.29s`, workflow job controls `3 passed in 86.69s`, tool bridge contracts `10 passed in 2.20s`, GraphRAG-lite `2 passed in 2.91s`, and context search `4 passed in 70.95s`.

## 2026-06-13 - Structured Extraction Fallback Coverage

Implemented in progress:

- Added `test_structured_card_extraction_falls_back_without_model_config` to `scripts/check_research_workflow_primitives.sh` so the default remote-safe suite covers deterministic structured paper-card fallback when model credentials are absent.
- Updated README, top-level TODO, and handoff TODO so workflow primitive changes call out structured extraction fallback alongside local literature search, paper cards, gap/idea generation, novelty, related work, and dossier exports.
- Kept the change scoped to existing `.venv` tools and in-process pytest targets; it does not install dependencies, start services, or require external API access.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_research_workflow_primitives.sh` passed: `11 passed in 68.16s`.
- `bash scripts/check_remote_safe_suite.sh` passed all nine default focused suites: pilot readiness `18 passed in 56.23s`, deployment contracts `1 passed in 1.64s`, research workflow primitives `11 passed in 67.50s`, research planning contracts `3 passed in 68.42s`, write audit `7 passed in 3.98s`, workflow job controls `3 passed in 85.95s`, tool bridge contracts `10 passed in 2.17s`, GraphRAG-lite `2 passed in 2.83s`, and context search `4 passed in 66.84s`.

## 2026-06-13 - Research Status Capability Coverage

Implemented in progress:

- Added `test_research_status` to `scripts/check_pilot_readiness.sh` so the default remote-safe suite covers the `/research/status` capability contract.
- Updated README, top-level TODO, and handoff TODO so pilot-readiness changes call out status capability coverage alongside health/readiness, upload/API-key guardrails, first-run onboarding, and pilot reports.
- Kept the change scoped to existing `.venv` tools and in-process pytest targets; it does not install dependencies, start services, or require external API access.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_pilot_readiness.sh` passed: `19 passed in 59.05s`.
- `bash scripts/check_remote_safe_suite.sh` passed all nine default focused suites: pilot readiness `19 passed in 57.65s`, deployment contracts `1 passed in 1.70s`, research workflow primitives `11 passed in 69.16s`, research planning contracts `3 passed in 69.01s`, write audit `7 passed in 3.82s`, workflow job controls `3 passed in 87.72s`, tool bridge contracts `10 passed in 2.16s`, GraphRAG-lite `2 passed in 2.88s`, and context search `4 passed in 70.42s`.

## 2026-06-13 - Focused Test Coverage Guard

Implemented in progress:

- Added `scripts/check_focused_test_coverage.sh` as a fast guard that parses pytest tests and focused check scripts to ensure every pytest test target is assigned to a focused check.
- Added the coverage guard to the start of `scripts/check_remote_safe_suite.sh` so missing focused-check assignment fails before slower suites run.
- Linked the guard from README verification instructions, top-level TODO, and handoff TODO.
- Kept the script read-only over `tests/` and `scripts/check_*.sh`; it does not install dependencies, start services, or inspect secrets.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_remote_safe_suite.sh` passed the focused coverage guard plus all nine default focused suites: pilot readiness `19 passed in 58.79s`, deployment contracts `1 passed in 1.74s`, research workflow primitives `11 passed in 71.29s`, research planning contracts `3 passed in 67.87s`, write audit `7 passed in 3.59s`, workflow job controls `3 passed in 88.50s`, tool bridge contracts `10 passed in 2.19s`, GraphRAG-lite `2 passed in 2.81s`, and context search `4 passed in 77.04s`.

## 2026-06-13 - Remote Long Focused Suite

Implemented in progress:

- Added `scripts/check_remote_long_suite.sh` as the explicit aggregate for long focused checks that should stay out of the default remote-safe suite.
- Seeded the long suite with the focused-test coverage guard and the proposal contract check.
- Linked the long suite from README verification instructions, top-level TODO, and handoff TODO.
- Kept `scripts/check_remote_safe_suite.sh` focused on default no-service checks while preserving a clear command for longer release-style verification.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_remote_long_suite.sh` passed: focused coverage guard reported `All pytest tests are covered by focused check scripts`, and proposal contracts passed `1 passed in 489.28s`.

## 2026-06-13 - Focused Suite Contract Guard

Implemented in progress:

- Added `scripts/check_suite_contracts.sh` as a fast guard for the intended default remote-safe versus long focused suite boundary.
- Added the suite contract guard to the start of `scripts/check_remote_safe_suite.sh` so long checks cannot drift into the default suite unnoticed.
- The guard requires default remote-safe checks to include the fast coverage guard and default focused scripts, forbids proposal/long-suite commands in the default suite, and requires the long suite to include coverage and proposal contracts.
- Linked the guard from README verification instructions, top-level TODO, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_suite_contracts.sh` passed: `Focused suite contracts are valid.`
- `bash scripts/check_remote_safe_suite.sh` passed the suite contract guard, focused coverage guard, and all nine default focused suites: pilot readiness `19 passed in 57.30s`, deployment contracts `1 passed in 1.64s`, research workflow primitives `11 passed in 72.27s`, research planning contracts `3 passed in 70.45s`, write audit `7 passed in 3.99s`, workflow job controls `3 passed in 88.70s`, tool bridge contracts `10 passed in 2.19s`, GraphRAG-lite `2 passed in 2.90s`, and context search `4 passed in 70.72s`.

## 2026-06-13 - Check Script Catalog Guard

Implemented in progress:

- Added `scripts/check_script_catalog.sh` as a fast guard that ensures every `scripts/check_*.sh` file is listed in README and follows the standard bash/root-directory preamble.
- Added the catalog guard to `scripts/check_remote_safe_suite.sh` after the suite-boundary guard and before pytest coverage mapping.
- Updated `scripts/check_suite_contracts.sh` so the default suite must include the catalog guard.
- Linked the catalog guard from README verification instructions, top-level TODO, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_script_catalog.sh` passed: `Check script catalog is synchronized.`
- `bash scripts/check_suite_contracts.sh` passed: `Focused suite contracts are valid.`
- `bash scripts/check_remote_safe_suite.sh` passed the suite contract guard, script catalog guard, focused coverage guard, and all nine default focused suites: pilot readiness `19 passed in 58.91s`, deployment contracts `1 passed in 1.66s`, research workflow primitives `11 passed in 69.75s`, research planning contracts `3 passed in 71.07s`, write audit `7 passed in 4.12s`, workflow job controls `3 passed in 89.37s`, tool bridge contracts `10 passed in 2.22s`, GraphRAG-lite `2 passed in 2.92s`, and context search `4 passed in 70.65s`.

## 2026-06-13 - Secret File Guard

Implemented in progress:

- Added `scripts/check_secret_file_guard.sh` as a fast guard for sensitive-looking tracked filenames and required ignore patterns.
- The guard allows `.env.example`, rejects tracked `.env`, `.env.*`, private-key/archive key suffixes, and filenames containing token/cookie/credential/secret markers.
- Added `*.pem`, `*.key`, `*.p12`, and `*.pfx` to `.gitignore` without reading or printing any sensitive file contents.
- Added the secret-file guard to `scripts/check_remote_safe_suite.sh` and updated `scripts/check_suite_contracts.sh` so default-suite composition requires it.
- Linked the guard from README verification instructions, top-level TODO, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_secret_file_guard.sh` passed: `Secret file guard passed.`
- `bash scripts/check_script_catalog.sh` passed: `Check script catalog is synchronized.`
- `bash scripts/check_suite_contracts.sh` passed: `Focused suite contracts are valid.`
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, and coverage guards plus all nine default focused suites: pilot readiness `19 passed in 60.89s`, deployment contracts `1 passed in 1.67s`, research workflow primitives `11 passed in 68.26s`, research planning contracts `3 passed in 69.90s`, write audit `7 passed in 4.06s`, workflow job controls `3 passed in 90.04s`, tool bridge contracts `10 passed in 2.16s`, GraphRAG-lite `2 passed in 2.84s`, and context search `4 passed in 71.07s`.

## 2026-06-13 - Handoff Document Consistency Guard

Implemented in progress:

- Added `scripts/check_handoff_docs.sh` as a fast guard for remote-first handoff document consistency.
- Added the handoff-doc guard to `scripts/check_remote_safe_suite.sh` after secret-file checks and updated `scripts/check_suite_contracts.sh` so the default suite requires it.
- Linked the guard from README verification instructions, top-level TODO, and handoff TODO.
- Kept the guard limited to repository documentation and did not read secrets, install dependencies, start services, or modify business code.
- Allowed `scripts/check_secret_file_guard.sh` in the secret-file guard whitelist so the filename guard does not flag its own checking script.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `bash scripts/check_secret_file_guard.sh` passed: `Secret file guard passed.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_suite_contracts.sh` passed: `Focused suite contracts are valid.`
- `bash scripts/check_script_catalog.sh` passed: `Check script catalog is synchronized.`
- `git --no-pager diff --check` passed with no whitespace errors.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, and coverage guards plus all nine default focused suites: pilot readiness `19 passed in 60.71s`, deployment contracts `1 passed in 1.63s`, research workflow primitives `11 passed in 70.63s`, research planning contracts `3 passed in 70.48s`, write audit `7 passed in 3.90s`, workflow job controls `3 passed in 88.35s`, tool bridge contracts `10 passed in 1.73s`, GraphRAG-lite `2 passed in 2.51s`, and context search `4 passed in 71.22s`.

## 2026-06-13 - Generated File Guard

Implemented in progress:

- Added `scripts/check_generated_file_guard.sh` as a fast guard against tracked generated artifacts, caches, virtualenvs, dependency folders, and build/coverage outputs.
- Added `node_modules/`, `.coverage`, `coverage.xml`, and `htmlcov/` to `.gitignore` alongside existing Python cache/build patterns.
- Added the generated-file guard to `scripts/check_remote_safe_suite.sh` and updated `scripts/check_suite_contracts.sh` so the default suite requires it.
- Linked the guard from README verification instructions, top-level TODO, and handoff TODO.
- Did not remove generated files from the working tree, read secrets, install dependencies, start services, or modify business code.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `bash scripts/check_generated_file_guard.sh` passed: `Generated file guard passed.`
- `bash scripts/check_suite_contracts.sh` passed: `Focused suite contracts are valid.`
- `bash scripts/check_script_catalog.sh` passed: `Check script catalog is synchronized.`
- `bash scripts/check_secret_file_guard.sh` passed: `Secret file guard passed.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `git --no-pager diff --check` passed with no whitespace errors.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `19 passed in 57.17s`, deployment contracts `1 passed in 1.65s`, research workflow primitives `11 passed in 69.78s`, research planning contracts `3 passed in 71.05s`, write audit `7 passed in 4.10s`, workflow job controls `3 passed in 90.21s`, tool bridge contracts `10 passed in 2.20s`, GraphRAG-lite `2 passed in 2.90s`, and context search `4 passed in 72.55s`.

## 2026-06-13 - Upload Filename Sanitization Test

Implemented in progress:

- Added a focused upload guardrail test that posts a text paper with a path-traversal filename and verifies only the basename is persisted under `PAPER_UPLOAD_DIR`.
- Added the new test to `scripts/check_pilot_readiness.sh` so upload filename sanitization stays in the no-service pilot-readiness suite.
- Did not change upload implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_upload_sanitizes_path_traversal_filename` passed: `1 passed in 3.64s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_pilot_readiness.sh` passed: `20 passed in 57.76s`.
- `git --no-pager diff --check` passed with no whitespace errors.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `20 passed in 58.26s`, deployment contracts `1 passed in 1.67s`, research workflow primitives `11 passed in 71.08s`, research planning contracts `3 passed in 69.64s`, write audit `7 passed in 3.91s`, workflow job controls `3 passed in 90.72s`, tool bridge contracts `10 passed in 2.23s`, GraphRAG-lite `2 passed in 3.11s`, and context search `4 passed in 68.99s`.

## 2026-06-13 - Upload UTF-8 Guardrail Test

Implemented in progress:

- Added a focused upload guardrail test that posts non-UTF-8 text bytes and verifies the API rejects the upload before writing the file.
- Added the new test to `scripts/check_pilot_readiness.sh` so text encoding validation stays in the no-service pilot-readiness suite.
- Updated `codex_handoff/03_TODO.md` to keep the completed pilot-readiness upload guardrail coverage synchronized.
- Did not change upload implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_upload_rejects_non_utf8_text_before_writing` passed: `1 passed in 3.56s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_pilot_readiness.sh` passed: `21 passed in 59.79s`.
- `git --no-pager diff --check` passed with no whitespace errors.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `21 passed in 60.03s`, deployment contracts `1 passed in 1.64s`, research workflow primitives `11 passed in 71.29s`, research planning contracts `3 passed in 86.16s`, write audit `7 passed in 3.84s`, workflow job controls `3 passed in 89.62s`, tool bridge contracts `10 passed in 2.18s`, GraphRAG-lite `2 passed in 3.08s`, and context search `4 passed in 72.29s`.

## 2026-06-13 - Markdown Upload Default Extension Test

Implemented in progress:

- Added a focused upload happy-path test that posts a Markdown paper and verifies the documented default `.md` extension is accepted, indexed, and produces evidence.
- Added the new test to `scripts/check_pilot_readiness.sh` so Markdown upload coverage stays in the no-service pilot-readiness suite.
- Updated `codex_handoff/03_TODO.md` to keep the completed pilot-readiness upload coverage synchronized.
- Did not change upload implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_upload_markdown_paper_uses_default_allowed_extension` passed: `1 passed in 3.75s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_pilot_readiness.sh` passed: `22 passed in 62.22s`.
- `git --no-pager diff --check` passed with no whitespace errors.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `22 passed in 60.20s`, deployment contracts `1 passed in 1.75s`, research workflow primitives `11 passed in 71.68s`, research planning contracts `3 passed in 70.26s`, write audit `7 passed in 3.98s`, workflow job controls `3 passed in 100.07s`, tool bridge contracts `10 passed in 2.19s`, GraphRAG-lite `2 passed in 2.92s`, and context search `4 passed in 70.19s`.

## 2026-06-13 - Empty Upload Guardrail Test

Implemented in progress:

- Added a focused upload guardrail test that posts an empty text file and verifies the API rejects it before writing the file.
- Added the new test to `scripts/check_pilot_readiness.sh` so empty-upload rejection stays in the no-service pilot-readiness suite.
- Updated `codex_handoff/03_TODO.md` to keep completed pilot-readiness upload coverage synchronized.
- Did not change upload implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_upload_rejects_empty_file_before_writing` passed: `1 passed in 3.67s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_pilot_readiness.sh` passed: `23 passed in 61.51s`.
- `git --no-pager diff --check` passed with no whitespace errors.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `23 passed in 62.67s`, deployment contracts `1 passed in 1.32s`, research workflow primitives `11 passed in 72.46s`, research planning contracts `3 passed in 72.41s`, write audit `7 passed in 3.95s`, workflow job controls `3 passed in 92.71s`, tool bridge contracts `10 passed in 2.28s`, GraphRAG-lite `2 passed in 2.90s`, and context search `4 passed in 73.22s`.

## 2026-06-13 - Upload Allowed Extension Override Test

Implemented in progress:

- Added a focused upload guardrail test that sets `PAPER_UPLOAD_ALLOWED_EXTENSIONS=txt`, posts a Markdown file, and verifies the API rejects it before writing the file.
- Added the new test to `scripts/check_pilot_readiness.sh` so extension override validation stays in the no-service pilot-readiness suite.
- Updated `codex_handoff/03_TODO.md` to keep completed pilot-readiness upload coverage synchronized.
- Did not change upload implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_upload_respects_allowed_extensions_override_before_writing` passed: `1 passed in 3.33s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_pilot_readiness.sh` passed: `24 passed in 60.07s`.
- `git --no-pager diff --check` passed with no whitespace errors.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `24 passed in 60.59s`, deployment contracts `1 passed in 1.67s`, research workflow primitives `11 passed in 73.84s`, research planning contracts `3 passed in 72.05s`, write audit `7 passed in 3.96s`, workflow job controls `3 passed in 91.74s`, tool bridge contracts `10 passed in 2.18s`, GraphRAG-lite `2 passed in 2.88s`, and context search `4 passed in 73.36s`.

## 2026-06-13 - Upload Extension Case Test

Implemented in progress:

- Added a focused upload happy-path test that posts an uppercase `.TXT` file and verifies extension matching remains case-insensitive while preserving the submitted filename.
- Added the new test to `scripts/check_pilot_readiness.sh` so extension case handling stays in the no-service pilot-readiness suite.
- Updated `codex_handoff/03_TODO.md` to keep completed pilot-readiness upload coverage synchronized.
- Did not change upload implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_upload_accepts_uppercase_allowed_extension` passed: `1 passed in 3.77s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_pilot_readiness.sh` passed: `25 passed in 67.85s`.
- `git --no-pager diff --check` passed with no whitespace errors.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 61.33s`, deployment contracts `1 passed in 1.71s`, research workflow primitives `11 passed in 73.96s`, research planning contracts `3 passed in 72.19s`, write audit `7 passed in 3.35s`, workflow job controls `3 passed in 91.99s`, tool bridge contracts `10 passed in 2.19s`, GraphRAG-lite `2 passed in 3.03s`, and context search `4 passed in 73.17s`.

## 2026-06-13 - Context Search Query Dedup Fixture

Implemented in progress:

- Added a deterministic context-search evaluation that repeats the same query marker three times and verifies retrieval reports the matched term once with a single lexical contribution.
- Added the new test to `scripts/check_context_search_evaluations.sh` so query-term deduplication stays covered before changing scoring weights.
- Updated `codex_handoff/03_TODO.md` to keep context-search evaluation coverage synchronized.
- Did not change retrieval implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_deduplicates_repeated_query_terms` passed: `1 passed in 4.77s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `5 passed in 74.38s`.
- `git --no-pager diff --check` passed with no whitespace errors.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 63.58s`, deployment contracts `1 passed in 1.65s`, research workflow primitives `11 passed in 74.20s`, research planning contracts `3 passed in 73.82s`, write audit `7 passed in 3.94s`, workflow job controls `3 passed in 94.36s`, tool bridge contracts `10 passed in 2.20s`, GraphRAG-lite `2 passed in 2.94s`, and context search `5 passed in 76.33s`.

## 2026-06-13 - Context Search Limit Clamp Fixture

Implemented in progress:

- Added a deterministic context-search evaluation that posts `limit: 0` and verifies the service clamps the request to one bounded result instead of returning zero or unbounded evidence.
- Added the new test to `scripts/check_context_search_evaluations.sh` so non-positive limit handling stays covered before changing scoring weights or graph expansion.
- Updated `codex_handoff/03_TODO.md` to keep context-search evaluation coverage synchronized.
- Did not change retrieval implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_clamps_non_positive_limit` passed: `1 passed in 4.50s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_context_search_evaluations.sh` passed: `6 passed in 76.41s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 61.00s`, deployment contracts `1 passed in 1.68s`, research workflow primitives `11 passed in 72.95s`, research planning contracts `3 passed in 73.64s`, write audit `7 passed in 4.11s`, workflow job controls `3 passed in 93.67s`, tool bridge contracts `10 passed in 2.18s`, GraphRAG-lite `2 passed in 3.08s`, and context search `6 passed in 76.39s`.

## 2026-06-13 - Context Search Large Limit Clamp Fixture

Implemented in progress:

- Added a deterministic context-search evaluation that creates 30 synthetic evidence rows and posts `limit: 99` to verify the service clamps large requests to 25 bounded evidence results.
- Added the new test to `scripts/check_context_search_evaluations.sh` so upper-limit handling stays covered before changing scoring weights or graph expansion.
- Updated `codex_handoff/03_TODO.md` to describe lower/upper limit-clamping coverage in the focused context-search check.
- Did not change retrieval implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_clamps_large_limit` passed: `1 passed in 4.86s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `7 passed in 78.88s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 66.54s`, deployment contracts `1 passed in 1.67s`, research workflow primitives `11 passed in 73.35s`, research planning contracts `3 passed in 72.78s`, write audit `7 passed in 3.74s`, workflow job controls `3 passed in 95.53s`, tool bridge contracts `10 passed in 2.18s`, GraphRAG-lite `2 passed in 2.90s`, and context search `7 passed in 79.46s`.

## 2026-06-13 - Context Search Graph Filter Normalization Fixture

Implemented in progress:

- Extended the deterministic graph-context search fixture to pass duplicate and blank `graph_edge_types` values and verify filtered graph expansion still returns only `paper_has_evidence` edges with zero graph noise.
- Updated `codex_handoff/03_TODO.md` to describe filter-normalization coverage in the focused context-search check.
- Did not change retrieval implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_returns_evidence_and_graph_context` passed: `1 passed in 53.19s`.
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `7 passed in 81.24s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 66.95s`, deployment contracts `1 passed in 1.81s`, research workflow primitives `11 passed in 74.41s`, research planning contracts `3 passed in 72.65s`, write audit `7 passed in 4.39s`, workflow job controls `3 passed in 95.37s`, tool bridge contracts `10 passed in 2.39s`, GraphRAG-lite `2 passed in 2.72s`, and context search `7 passed in 80.36s`.

## 2026-06-13 - Context Search No-Match Fixture

Implemented in progress:

- Added a deterministic no-match context-search evaluation that creates a scoped synthetic paper without evidence, gaps, or ideas and verifies the API returns empty context plus the stable no-match answer brief.
- Added the new test to `scripts/check_context_search_evaluations.sh` so negative scoped queries stay covered before changing scoring weights or graph expansion.
- Updated `docs/context_search_evaluation_plan.md` and `codex_handoff/03_TODO.md` to keep committed context-search evaluation coverage synchronized.
- Did not change retrieval implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_no_match_fixture` passed: `1 passed in 5.63s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `8 passed in 81.61s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 63.44s`, deployment contracts `1 passed in 1.68s`, research workflow primitives `11 passed in 75.05s`, research planning contracts `3 passed in 73.90s`, write audit `7 passed in 3.81s`, workflow job controls `3 passed in 95.88s`, tool bridge contracts `10 passed in 2.36s`, GraphRAG-lite `2 passed in 3.07s`, and context search `8 passed in 82.68s`.

## 2026-06-13 - Context Search Vector Rescue Fixture

Implemented in progress:

- Added a deterministic lexical-miss/vector-hit context-search evaluation that finds a stable local hash-vector collision token, creates evidence that does not contain the query term, and verifies vector retrieval still returns it with lexical/bonus/phrase contributions at zero.
- Added the new test to `scripts/check_context_search_evaluations.sh` so vector rescue behavior stays covered before changing scoring weights or embedding behavior.
- Updated `docs/context_search_evaluation_plan.md` and `codex_handoff/03_TODO.md` to keep committed context-search evaluation coverage synchronized.
- Did not change retrieval or embedding implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_vector_hit_rescues_lexical_miss` passed: `1 passed in 4.92s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `9 passed in 81.95s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 63.02s`, deployment contracts `1 passed in 1.66s`, research workflow primitives `11 passed in 75.26s`, research planning contracts `3 passed in 74.88s`, write audit `7 passed in 3.93s`, workflow job controls `3 passed in 97.58s`, tool bridge contracts `10 passed in 2.70s`, GraphRAG-lite `2 passed in 2.86s`, and context search `9 passed in 85.58s`.

## 2026-06-13 - Context Search Phrase Bonus Fixture

Implemented in progress:

- Added a deterministic exact-phrase context-search evaluation that creates evidence containing an ordered two-term query phrase and verifies lexical, bonus, phrase, and vector score-breakdown components remain visible and internally consistent.
- Added the new test to `scripts/check_context_search_evaluations.sh` so phrase bonus behavior stays covered before changing scoring weights.
- Updated `docs/context_search_evaluation_plan.md` and `codex_handoff/03_TODO.md` to keep committed context-search evaluation coverage synchronized.
- Did not change retrieval or embedding implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_exact_phrase_bonus_breakdown` passed: `1 passed in 4.97s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `10 passed in 84.47s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 64.31s`, deployment contracts `1 passed in 1.67s`, research workflow primitives `11 passed in 75.76s`, research planning contracts `3 passed in 73.99s`, write audit `7 passed in 3.92s`, workflow job controls `3 passed in 99.52s`, tool bridge contracts `10 passed in 2.20s`, GraphRAG-lite `2 passed in 2.89s`, and context search `10 passed in 85.44s`.

## 2026-06-13 - Context Search Evidence Bonus Fixture

Implemented in progress:

- Added a deterministic evidence-confidence context-search evaluation that creates evidence with separated query terms, confidence `0.73`, and verifies lexical, bonus, phrase, and vector score-breakdown components remain visible and internally consistent.
- Added the new test to `scripts/check_context_search_evaluations.sh` so evidence confidence bonus behavior stays covered before changing scoring weights.
- Updated `docs/context_search_evaluation_plan.md` and `codex_handoff/03_TODO.md` to keep committed context-search evaluation coverage synchronized.
- Did not change retrieval or embedding implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_evidence_confidence_bonus_breakdown` passed: `1 passed in 5.07s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `11 passed in 86.39s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 67.65s`, deployment contracts `1 passed in 1.66s`, research workflow primitives `11 passed in 75.69s`, research planning contracts `3 passed in 75.46s`, write audit `7 passed in 4.02s`, workflow job controls `3 passed in 108.53s`, tool bridge contracts `10 passed in 2.21s`, GraphRAG-lite `2 passed in 3.00s`, and context search `11 passed in 87.79s`.

## 2026-06-13 - Context Search Gap Bonus Fixture

Implemented in progress:

- Added a deterministic gap-feasibility context-search evaluation that creates a scoped research gap with feasibility `8.4` and verifies lexical, bonus, phrase, and vector score-breakdown components remain visible and internally consistent.
- Added the new test to `scripts/check_context_search_evaluations.sh` so gap feasibility bonus behavior stays covered before changing scoring weights.
- Updated `docs/context_search_evaluation_plan.md` and `codex_handoff/03_TODO.md` to keep committed context-search evaluation coverage synchronized.
- Did not change retrieval or embedding implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_gap_feasibility_bonus_breakdown` passed: `1 passed in 5.19s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `12 passed in 88.75s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 69.15s`, deployment contracts `1 passed in 1.76s`, research workflow primitives `11 passed in 77.22s`, research planning contracts `3 passed in 76.61s`, write audit `7 passed in 3.63s`, workflow job controls `3 passed in 98.92s`, tool bridge contracts `10 passed in 2.18s`, GraphRAG-lite `2 passed in 2.92s`, and context search `12 passed in 89.56s`.

## 2026-06-13 - Context Search Idea Bonus Fixture

Implemented in progress:

- Added a deterministic idea-overall-score context-search evaluation that creates a scoped research idea with `overall_score` `7.6` and verifies lexical, bonus, phrase, and vector score-breakdown components remain visible and internally consistent.
- Added the new test to `scripts/check_context_search_evaluations.sh` so idea score bonus behavior stays covered before changing scoring weights.
- Updated `docs/context_search_evaluation_plan.md` and `codex_handoff/03_TODO.md` to keep committed context-search evaluation coverage synchronized.
- Did not change retrieval or embedding implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_idea_overall_score_bonus_breakdown` passed: `1 passed in 4.69s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `13 passed in 90.99s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 67.06s`, deployment contracts `1 passed in 1.73s`, research workflow primitives `11 passed in 77.00s`, research planning contracts `3 passed in 78.57s`, write audit `7 passed in 4.19s`, workflow job controls `3 passed in 98.52s`, tool bridge contracts `10 passed in 2.22s`, GraphRAG-lite `2 passed in 2.97s`, and context search `13 passed in 89.89s`.

## 2026-06-13 - GraphRAG Duplicate Stats Fixture

Implemented in progress:

- Added a deterministic GraphRAG-lite stats test that creates two direct duplicate edges for the same source, target, and edge type, then verifies `/research/graph/stats` reports the edge type count and at least one duplicate edge group.
- Added the new test to `scripts/check_graph_rag_lite.sh` so duplicate-edge stat reporting stays covered with duplicate-edge reuse and graph link/stat fixtures.
- Updated `codex_handoff/03_TODO.md` to keep GraphRAG-lite focused coverage synchronized.
- Did not change graph implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/graph_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/graph_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_graph_stats_reports_duplicate_edge_groups` passed: `1 passed in 4.19s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_graph_rag_lite.sh` passed: `3 passed in 3.65s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 69.27s`, deployment contracts `1 passed in 1.66s`, research workflow primitives `11 passed in 80.00s`, research planning contracts `3 passed in 75.46s`, write audit `7 passed in 3.92s`, workflow job controls `3 passed in 84.04s`, tool bridge contracts `10 passed in 2.33s`, GraphRAG-lite `3 passed in 3.70s`, and context search `13 passed in 92.82s`.

## 2026-06-13 - GraphRAG Orphan Stats Fixture

Implemented in progress:

- Added a deterministic GraphRAG-lite stats test that creates one temporary orphan edge pointing at a missing target node, verifies `/research/graph/stats` reports at least one orphan edge, and cleans up the edge and source node before later graph stats fixtures run.
- Added the new test to `scripts/check_graph_rag_lite.sh` so orphan-edge stat reporting stays covered with duplicate-edge reuse, duplicate-edge stats, and graph link/stat fixtures.
- Updated `codex_handoff/03_TODO.md` to keep GraphRAG-lite focused coverage synchronized.
- Did not change graph implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/graph_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/graph_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_graph_stats_reports_orphan_edges_without_persisting_fixture` passed: `1 passed in 4.49s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_graph_rag_lite.sh` passed: `4 passed in 4.03s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 62.89s`, deployment contracts `1 passed in 1.66s`, research workflow primitives `11 passed in 79.49s`, research planning contracts `3 passed in 78.37s`, write audit `7 passed in 4.06s`, workflow job controls `3 passed in 100.26s`, tool bridge contracts `10 passed in 1.76s`, GraphRAG-lite `4 passed in 4.17s`, and context search `13 passed in 109.32s`.

## 2026-06-13 - Context Search Graph Paper Filter Fixture

Implemented in progress:

- Added a deterministic context-search evaluation that uploads two synthetic papers sharing the same query term, scopes search to one paper with `include_graph=true`, and verifies GraphRAG-lite nodes and `paper_has_evidence` edges do not leak the excluded paper or its evidence ids.
- Added the new test to `scripts/check_context_search_evaluations.sh` so graph paper-filter behavior stays covered before changing graph expansion or retrieval scoring.
- Updated `docs/context_search_evaluation_plan.md` and `codex_handoff/03_TODO.md` to keep committed context-search evaluation coverage synchronized.
- Did not change retrieval, graph, or embedding implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_graph_context_respects_paper_filter` passed: `1 passed in 5.43s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `14 passed in 96.04s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 68.15s`, deployment contracts `1 passed in 1.79s`, research workflow primitives `11 passed in 81.73s`, research planning contracts `3 passed in 78.56s`, write audit `7 passed in 4.10s`, workflow job controls `3 passed in 99.58s`, tool bridge contracts `10 passed in 2.26s`, GraphRAG-lite `4 passed in 4.31s`, and context search `14 passed in 92.31s`.

## 2026-06-13 - Context Search Graph Expansion Recall

Implemented in progress:

- Updated GraphRAG-lite context expansion to query seed-node-connected edges before falling back to the recent-edge evidence-id scan, so relevant older graph edges are not hidden by many newer unrelated edges.
- Added a deterministic context-search regression with one relevant older `paper_has_evidence` edge and 805 newer unrelated edges, then verified scoped graph search still returns the relevant edge and paper node.
- Added the new test to `scripts/check_context_search_evaluations.sh` and updated `docs/context_search_evaluation_plan.md` plus `codex_handoff/03_TODO.md` to keep graph expansion recall coverage synchronized.
- Did not install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_graph_expansion_keeps_relevant_edge_after_recent_noise` passed: `1 passed in 5.31s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `15 passed in 94.02s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 66.58s`, deployment contracts `1 passed in 1.78s`, research workflow primitives `11 passed in 78.75s`, research planning contracts `3 passed in 79.87s`, write audit `7 passed in 4.30s`, workflow job controls `3 passed in 103.93s`, tool bridge contracts `10 passed in 2.30s`, GraphRAG-lite `4 passed in 4.35s`, and context search `15 passed in 94.27s`.

## 2026-06-13 - Context Search Multi Edge Filter Fixture

Implemented in progress:

- Extended the deterministic context-search graph-context fixture to request multiple GraphRAG-lite workflow edge types at once and verify the response includes the selected `paper_has_evidence` and `gap_supported_by_evidence` families without admitting unrelated edge types.
- Updated `docs/context_search_evaluation_plan.md` and `codex_handoff/03_TODO.md` so committed context-search evaluation coverage reflects multi-edge-type filter checks.
- Did not change retrieval implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_returns_evidence_and_graph_context` passed: `1 passed in 57.63s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `15 passed in 97.85s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 68.99s`, deployment contracts `1 passed in 1.64s`, research workflow primitives `11 passed in 80.94s`, research planning contracts `3 passed in 80.38s`, write audit `7 passed in 3.84s`, workflow job controls `3 passed in 100.63s`, tool bridge contracts `10 passed in 2.21s`, GraphRAG-lite `4 passed in 4.29s`, and context search `15 passed in 97.59s`.

## 2026-06-14 - Context Search Edge Filter Whitespace Normalization

Implemented in progress:

- Normalized GraphRAG-lite context-search `graph_edge_types` by trimming whitespace before applying edge-type filters, while still dropping blank values and duplicates.
- Extended the existing graph-context fixture to pass blank, whitespace-padded, and tab-padded `paper_has_evidence` filters and verify the selected edge family is still returned without unrelated edge types.
- Updated `docs/context_search_evaluation_plan.md` and `codex_handoff/03_TODO.md` so committed context-search evaluation coverage reflects blank, duplicate, and whitespace filter normalization.
- Did not change response schemas, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_returns_evidence_and_graph_context` passed: `1 passed in 58.83s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `15 passed in 96.56s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 67.25s`, deployment contracts `1 passed in 1.83s`, research workflow primitives `11 passed in 79.27s`, research planning contracts `3 passed in 77.88s`, write audit `7 passed in 4.09s`, workflow job controls `3 passed in 101.21s`, tool bridge contracts `10 passed in 2.38s`, GraphRAG-lite `4 passed in 4.29s`, and context search `15 passed in 95.21s`.

## 2026-06-14 - Upload Allowed Extension Normalization Fixture

Implemented in progress:

- Added a deterministic pilot-readiness upload guardrail test for `PAPER_UPLOAD_ALLOWED_EXTENSIONS` values with whitespace, optional leading dots, and mixed case.
- Added the new test to `scripts/check_pilot_readiness.sh` so operator-friendly upload extension configuration stays covered before changing first-run upload behavior.
- Updated `codex_handoff/03_TODO.md` to keep upload guardrail coverage synchronized.
- Did not change upload implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/app.py backend/research/config.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/app.py backend/research/config.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_upload_allowed_extensions_override_normalizes_values` passed: `1 passed in 4.50s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_pilot_readiness.sh` passed: `26 passed in 67.89s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `26 passed in 67.89s`, deployment contracts `1 passed in 1.79s`, research workflow primitives `11 passed in 80.79s`, research planning contracts `3 passed in 78.75s`, write audit `7 passed in 3.87s`, workflow job controls `3 passed in 104.85s`, tool bridge contracts `10 passed in 2.27s`, GraphRAG-lite `4 passed in 4.38s`, and context search `15 passed in 97.23s`.

## 2026-06-14 - Upload Max Bytes Fallback Fixture

Implemented in progress:

- Added a deterministic pilot-readiness upload guardrail test for invalid `PAPER_UPLOAD_MAX_BYTES` values, verifying small Markdown uploads fall back to the default limit and still index successfully.
- Added the new test to `scripts/check_pilot_readiness.sh` so upload limit configuration fallback stays covered before changing first-run upload behavior.
- Updated `codex_handoff/03_TODO.md` to keep upload guardrail coverage synchronized.
- Did not change upload implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/app.py backend/research/config.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/app.py backend/research/config.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_upload_invalid_max_bytes_falls_back_to_default_limit` passed: `1 passed in 3.63s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_pilot_readiness.sh` passed: `27 passed in 66.28s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `27 passed in 70.28s`, deployment contracts `1 passed in 1.60s`, research workflow primitives `11 passed in 80.67s`, research planning contracts `3 passed in 80.00s`, write audit `7 passed in 3.99s`, workflow job controls `3 passed in 100.43s`, tool bridge contracts `10 passed in 2.14s`, GraphRAG-lite `4 passed in 3.83s`, and context search `15 passed in 97.97s`.

## 2026-06-14 - Upload Non-Positive Max Bytes Fallback

Implemented in progress:

- Hardened upload size configuration so non-positive `PAPER_UPLOAD_MAX_BYTES` values fall back to the default upload limit instead of disabling size validation.
- Added a deterministic pilot-readiness upload guardrail test that temporarily lowers the default limit, sets `PAPER_UPLOAD_MAX_BYTES=-1`, and verifies an oversized text upload is rejected before writing.
- Added the new test to `scripts/check_pilot_readiness.sh` so upload limit fallback stays covered before changing first-run upload behavior.
- Updated `codex_handoff/03_TODO.md` to keep upload guardrail coverage synchronized.
- Did not install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/app.py backend/research/config.py backend/research/services/document_ingestion.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/app.py backend/research/config.py backend/research/services/document_ingestion.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_upload_non_positive_max_bytes_falls_back_to_default_limit` passed: `1 passed in 4.39s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_pilot_readiness.sh` passed: `28 passed in 70.30s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `28 passed in 70.34s`, deployment contracts `1 passed in 1.85s`, research workflow primitives `11 passed in 81.66s`, research planning contracts `3 passed in 79.99s`, write audit `7 passed in 3.99s`, workflow job controls `3 passed in 106.26s`, tool bridge contracts `10 passed in 2.39s`, GraphRAG-lite `4 passed in 4.46s`, and context search `15 passed in 100.23s`.

## 2026-06-14 - OpenAlex Literature Parser Fixture

Implemented in progress:

- Added a deterministic OpenAlex literature item parser fixture covering authorship extraction, venue, DOI URL preference, abstract reconstruction from `abstract_inverted_index`, score ordering, and metadata preservation.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so all configured external literature provider parsers have no-network contract coverage before changing literature search behavior.
- Updated `codex_handoff/03_TODO.md` to keep workflow primitive coverage synchronized.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_openalex_literature_item_parser` passed: `1 passed in 3.69s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `12 passed in 82.10s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `28 passed in 69.53s`, deployment contracts `1 passed in 1.75s`, research workflow primitives `12 passed in 81.44s`, research planning contracts `3 passed in 79.75s`, write audit `7 passed in 4.11s`, workflow job controls `3 passed in 104.80s`, tool bridge contracts `10 passed in 2.36s`, GraphRAG-lite `4 passed in 4.44s`, and context search `15 passed in 102.07s`.

## 2026-06-14 - Literature Provider Config Normalization Fixture

Implemented in progress:

- Added a deterministic no-network literature provider config fixture covering OpenAlex/arXiv/Semantic Scholar aliases, duplicate removal, and unknown provider filtering.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so external provider configuration stays covered before changing literature search behavior.
- Updated `codex_handoff/03_TODO.md` to keep workflow primitive coverage synchronized.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_external_literature_provider_config_normalization` passed: `1 passed in 3.21s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `13 passed in 82.86s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `28 passed in 69.23s`, deployment contracts `1 passed in 1.64s`, research workflow primitives `13 passed in 82.38s`, research planning contracts `3 passed in 81.42s`, write audit `7 passed in 3.86s`, workflow job controls `3 passed in 105.75s`, tool bridge contracts `10 passed in 2.21s`, GraphRAG-lite `4 passed in 4.57s`, and context search `15 passed in 99.00s`.

## 2026-06-14 - Literature Provider Partial Status Fixture

Implemented in progress:

- Added a deterministic no-network external literature search fixture covering mixed provider outcomes: OpenAlex and Semantic Scholar return results while arXiv raises a request timeout.
- Verified partial external search keeps successful provider results and reports the failed provider in the status string.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so external provider status aggregation stays covered before changing literature search behavior.
- Updated `codex_handoff/03_TODO.md` to keep workflow primitive coverage synchronized.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_external_literature_search_returns_partial_status` passed: `1 passed in 3.62s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `14 passed in 81.99s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `28 passed in 70.97s`, deployment contracts `1 passed in 1.77s`, research workflow primitives `14 passed in 82.62s`, research planning contracts `3 passed in 81.75s`, write audit `7 passed in 3.89s`, workflow job controls `3 passed in 104.39s`, tool bridge contracts `10 passed in 2.35s`, GraphRAG-lite `4 passed in 4.25s`, and context search `15 passed in 97.27s`.

## 2026-06-14 - Literature Provider Failed Status Fixture

Implemented in progress:

- Added a deterministic no-network external literature search fixture covering the all-provider-failed path: OpenAlex raises a connection error and arXiv raises an XML parse error.
- Verified failed external search returns no items and reports each provider failure in the status string.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so external provider failure status aggregation stays covered before changing literature search behavior.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_external_literature_search_reports_failed_status` passed: `1 passed in 4.02s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `15 passed in 83.22s`.
- The remote safe suite was completed as its documented component scripts after the first aggregate run lost the SSH connection during a long no-output window: suite contracts passed, script catalog passed, secret file guard passed, handoff docs passed, generated file guard passed, focused coverage passed, pilot readiness `28 passed in 69.40s`, deployment contracts `1 passed in 1.67s`, research workflow primitives `15 passed in 83.22s`, research planning contracts `3 passed in 82.15s`, write audit `7 passed in 3.88s`, workflow job controls `3 passed in 104.83s`, tool bridge contracts `10 passed in 2.16s`, GraphRAG-lite `4 passed in 4.31s`, and context search `15 passed in 99.31s`.

## 2026-06-14 - Literature Provider Completed And Not Configured Status Fixtures

Implemented in progress:

- Added deterministic no-network external literature search fixtures for `not_configured` and all-provider-success `completed` status aggregation.
- Verified unknown/unsupported provider configuration returns no external items with `not_configured` status.
- Verified OpenAlex, arXiv, and Semantic Scholar success paths keep provider results and report `completed` status without calling external APIs.
- Added the new tests to `scripts/check_research_workflow_primitives.sh` so external provider status aggregation stays covered before changing literature search behavior.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_external_literature_search_reports_not_configured_status tests/test_app.py::test_external_literature_search_reports_completed_status` passed: `2 passed in 3.05s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `17 passed in 82.29s`.
- The remote safe suite was completed as its documented component scripts: suite contracts passed, script catalog passed, secret file guard passed, handoff docs passed, generated file guard passed, focused coverage passed, pilot readiness `28 passed in 69.93s`, deployment contracts `1 passed in 1.63s`, research workflow primitives `17 passed in 82.29s`, research planning contracts `3 passed in 80.49s`, write audit `7 passed in 3.95s`, workflow job controls `3 passed in 107.41s`, tool bridge contracts `10 passed in 2.21s`, GraphRAG-lite `4 passed in 3.98s`, and context search `15 passed in 101.39s`.

## 2026-06-14 - Literature Search Empty Query Guard Fixture

Implemented in progress:

- Added a deterministic API-level literature search guard fixture for empty/punctuation-only queries.
- Verified `/research/literature/search` returns HTTP 400 with `Query must contain at least one searchable term` instead of running local or external search.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so literature search input validation stays covered before changing search behavior.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py backend/research/routes.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py backend/research/routes.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_literature_search_rejects_empty_query` passed: `1 passed in 4.15s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `18 passed in 83.32s`.
- The remote safe suite was completed as its documented component scripts: suite contracts passed, script catalog passed, secret file guard passed, handoff docs passed, generated file guard passed, focused coverage passed, pilot readiness `28 passed in 74.67s`, deployment contracts `1 passed in 1.77s`, research planning contracts `3 passed in 82.51s`, write audit `7 passed in 4.13s`, workflow job controls `3 passed in 106.66s`, tool bridge contracts `10 passed in 2.30s`, GraphRAG-lite `4 passed in 4.26s`, and context search `15 passed in 101.18s`.

## 2026-06-14 - Literature Search Limit And Ranking Fixture

Implemented in progress:

- Added a deterministic no-network literature search service fixture covering query-term deduplication, high-limit clamping, original query forwarding to external search, and combined local/external result ranking by score.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so literature search limit/ranking behavior stays covered before changing search behavior.
- Updated `codex_handoff/03_TODO.md` to keep workflow primitive coverage synchronized.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_literature_search_clamps_limit_and_sorts_combined_results` passed: `1 passed in 3.50s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `19 passed in 81.95s`.
- The remote safe suite was completed as its documented component scripts: suite contracts passed, script catalog passed, secret file guard passed, handoff docs passed, generated file guard passed, focused coverage passed, pilot readiness `28 passed in 69.70s`, deployment contracts `1 passed in 1.65s`, research planning contracts `3 passed in 85.58s`, write audit `7 passed in 3.53s`, workflow job controls `3 passed in 113.36s`, tool bridge contracts `10 passed in 2.15s`, GraphRAG-lite `4 passed in 4.26s`, and context search `15 passed in 102.36s`.

## 2026-06-14 - Literature Search Low Limit Truncation Fixture

Implemented in progress:

- Added a deterministic no-network literature search service fixture covering non-positive limit clamping to one result, final result truncation, score ordering, and the `not_requested` external status when external search is not requested.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so literature search lower-bound limit behavior stays covered before changing search behavior.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_literature_search_clamps_low_limit_and_truncates_results` passed: `1 passed in 3.72s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `20 passed in 83.47s`.
- The remote safe suite was completed as its documented component scripts: suite contracts passed, script catalog passed, secret file guard passed, generated file guard passed, pilot readiness `28 passed in 72.47s`, deployment contracts `1 passed in 1.72s`, research planning contracts `3 passed in 84.26s`, write audit `7 passed in 4.11s`, workflow job controls `3 passed in 108.24s`, tool bridge contracts `10 passed in 2.31s`, GraphRAG-lite `4 passed in 4.32s`, and context search `15 passed in 101.26s`.

## 2026-06-14 - Semantic Scholar Parser Fallback Fixture

Implemented in progress:

- Added a deterministic no-network Semantic Scholar parser fixture covering missing `paperId`, DOI fallback source ids, untitled paper fallback, empty-author filtering, missing venue/url defaults, abstract truncation, score offset, and metadata preservation.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so Semantic Scholar parser fallback behavior stays covered before changing external literature parsing.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_semantic_scholar_literature_item_parser_fallbacks` passed: `1 passed in 3.71s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `21 passed in 83.90s`.
- The remote safe suite was completed as its documented component scripts: suite contracts passed, script catalog passed, secret file guard passed, generated file guard passed, pilot readiness `28 passed in 68.46s`, deployment contracts `1 passed in 1.76s`, research planning contracts `3 passed in 85.30s`, write audit `7 passed in 4.13s`, workflow job controls `3 passed in 106.83s`, tool bridge contracts `10 passed in 2.20s`, GraphRAG-lite `4 passed in 4.42s`, and context search `15 passed in 101.68s`.

## 2026-06-14 - OpenAlex Parser Fallback Fixture

Implemented in progress:

- Added a deterministic no-network OpenAlex parser fixture covering display-name title fallback, id URL fallback, empty-author filtering, missing venue/year/abstract defaults, score floor behavior, and metadata preservation.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so OpenAlex parser fallback behavior stays covered before changing external literature parsing.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_openalex_literature_item_parser_fallbacks` passed: `1 passed in 3.57s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `22 passed in 85.58s`.
- The remote safe suite was completed as its documented component scripts: suite contracts passed, script catalog passed, secret file guard passed, generated file guard passed, pilot readiness `28 passed in 70.65s`, deployment contracts `1 passed in 1.77s`, research planning contracts `3 passed in 83.58s`, write audit `7 passed in 4.19s`, workflow job controls `3 passed in 107.55s`, tool bridge contracts `10 passed in 2.43s`, GraphRAG-lite `4 passed in 4.56s`, and context search `15 passed in 104.92s`.

## 2026-06-14 - arXiv Parser Fallback Fixture

Implemented in progress:

- Added a deterministic no-network arXiv parser fixture covering untitled preprint fallback, invalid published-date year handling, empty-author filtering, empty category handling, abstract normalization/truncation, score floor behavior, and metadata preservation.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so arXiv parser fallback behavior stays covered before changing external literature parsing.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_arxiv_literature_item_parser_fallbacks` passed: `1 passed in 4.00s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `23 passed in 90.12s`.
- The remote safe suite was completed as its documented component scripts: suite contracts passed, script catalog passed, secret file guard passed, generated file guard passed, pilot readiness `28 passed in 72.47s`, deployment contracts `1 passed in 1.63s`, research planning contracts `3 passed in 85.05s`, write audit `7 passed in 3.88s`, workflow job controls `3 passed in 105.60s`, tool bridge contracts `10 passed in 2.21s`, GraphRAG-lite `4 passed in 4.23s`, and context search `15 passed in 104.00s`.

## 2026-06-14 - OpenAlex Inverted Index Abstract Fixture

Implemented in progress:

- Added a deterministic no-network OpenAlex inverted-index abstract reconstruction fixture covering position ordering, duplicate-position overwrite behavior, and 1200-character truncation.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so OpenAlex abstract reconstruction stays covered before changing external literature parsing.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_openalex_inverted_index_abstract_reconstruction_edges` passed: `1 passed in 3.61s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `24 passed in 85.33s`.
- The remote safe suite was completed as its documented component scripts: suite contracts passed, script catalog passed, secret file guard passed, generated file guard passed, pilot readiness `28 passed in 69.38s`, deployment contracts `1 passed in 1.72s`, research planning contracts `3 passed in 83.73s`, write audit `7 passed in 4.03s`, workflow job controls `3 passed in 108.64s`, tool bridge contracts `10 passed in 2.20s`, GraphRAG-lite `4 passed in 4.24s`, and context search `15 passed in 103.31s`.

## 2026-06-14 - Related Work Service Contract Coverage

Implemented in progress:

- Added no-network service-level contract tests for related-work query cleaning, default query fallback, query length clamping, missing external-search actions, row sorting/truncation, and literature metadata preservation.
- Added the new tests and `backend/research/services/related_work_service.py` lint coverage to `scripts/check_research_workflow_primitives.sh`.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` passed after formatting the new tests.
- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py` passed.
- Focused related-work service pytest passed: `3 passed in 3.25s`.
- `bash scripts/check_research_workflow_primitives.sh` passed: `27 passed in 85.49s`.
- Fast guards passed: focused test coverage, suite contracts, script catalog, handoff docs, secret file guard, generated file guard, and `git --no-pager diff --check`.
- The remote safe suite was completed as its documented component scripts: pilot readiness `28 passed in 76.87s`, deployment contracts `1 passed in 1.79s`, research planning contracts `3 passed in 85.29s`, write audit `7 passed in 4.00s`, workflow job controls `3 passed in 111.31s`, tool bridge contracts `10 passed in 2.43s`, GraphRAG-lite `4 passed in 4.31s`, and context search `15 passed in 102.34s`.

## 2026-06-14 - Novelty Service Contract Coverage

Implemented in progress:

- Added no-network service-level contract tests for novelty overlap scoring, external overlap status handling, missing-search actions, risk levels, and recommended actions.
- Added the new tests and `backend/research/services/novelty_service.py` lint coverage to `scripts/check_research_workflow_primitives.sh`.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` passed after formatting the new tests.
- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py` passed.
- Focused novelty service pytest passed after fixture correction: `3 passed in 3.62s`.
- `bash scripts/check_research_workflow_primitives.sh` passed: `30 passed in 89.98s`.
- Fast guards passed: focused test coverage, suite contracts, script catalog, handoff docs, secret file guard, generated file guard, and `git --no-pager diff --check`.
- The remote safe suite was completed as its documented component scripts: pilot readiness `28 passed in 70.82s`, deployment contracts `1 passed in 1.65s`, research planning contracts `3 passed in 86.70s`, write audit `7 passed in 3.65s`, workflow job controls `3 passed in 109.64s`, tool bridge contracts `10 passed in 2.35s`, GraphRAG-lite `4 passed in 4.17s`, and context search `15 passed in 106.07s`.

## 2026-06-15 - Structured Extraction Prompt Contract Coverage

Implemented in progress:

- Added a no-network prompt-construction contract test for structured paper-card extraction evidence limits, per-evidence text truncation, and schema hint presence.
- Added the new test and `backend/research/services/structured_extraction_service.py` lint coverage to `scripts/check_research_workflow_primitives.sh`.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` passed.
- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py backend/research/services/structured_extraction_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py backend/research/services/structured_extraction_service.py` passed.
- Focused structured-extraction prompt pytest passed: `1 passed in 4.27s`.
- `bash scripts/check_research_workflow_primitives.sh` passed: `31 passed in 88.24s`.
- Fast guards passed: focused test coverage, suite contracts, script catalog, handoff docs, secret file guard, generated file guard, and `git --no-pager diff --check`.
- The remote safe suite was completed as its documented component scripts: pilot readiness `28 passed in 77.03s`, deployment contracts `1 passed in 1.72s`, research planning contracts `3 passed in 87.89s`, write audit `7 passed in 4.07s`, workflow job controls `3 passed in 131.51s`, tool bridge contracts `10 passed in 2.17s`, GraphRAG-lite `4 passed in 4.53s`, and context search `15 passed in 100.64s`.

## 2026-06-15 - Gap And Idea Service Contract Coverage

Implemented in progress:

- Added no-network service-level contract tests for gap title building, importance/unsolved explanations, possible approaches, idea variant generation, text shortening, and gap/evidence lineage preservation.
- Added the new tests and `backend/research/services/gap_service.py` plus `backend/research/services/idea_service.py` lint coverage to `scripts/check_research_workflow_primitives.sh`.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` passed.
- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py backend/research/services/structured_extraction_service.py backend/research/services/gap_service.py backend/research/services/idea_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py backend/research/services/structured_extraction_service.py backend/research/services/gap_service.py backend/research/services/idea_service.py` passed.
- Focused gap/idea service pytest passed: `2 passed in 4.29s`.
- `bash scripts/check_research_workflow_primitives.sh` passed: `33 passed in 87.57s`.
- Fast guards passed: focused test coverage, suite contracts, script catalog, handoff docs, secret file guard, generated file guard, and `git --no-pager diff --check`.
- The remote safe suite was completed as its documented component scripts: pilot readiness `28 passed in 76.30s`, deployment contracts `1 passed in 1.63s`, research planning contracts `3 passed in 86.28s`, write audit `7 passed in 3.92s`, workflow job controls `3 passed in 116.21s`, tool bridge contracts `10 passed in 2.42s`, GraphRAG-lite `4 passed in 4.50s`, and context search `15 passed in 107.65s`.

## 2026-06-15 - Paper Card Heuristic Contract Coverage

Implemented in progress:

- Added service-level contract tests for paper-card heuristic evidence-field mapping, problem fallback behavior, keyword collection, and missing input errors.
- Added the new tests and `backend/research/services/paper_card_service.py` lint coverage to `scripts/check_research_workflow_primitives.sh`.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` passed after formatting the new tests.
- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py backend/research/services/structured_extraction_service.py backend/research/services/gap_service.py backend/research/services/idea_service.py backend/research/services/paper_card_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py backend/research/services/structured_extraction_service.py backend/research/services/gap_service.py backend/research/services/idea_service.py backend/research/services/paper_card_service.py` passed.
- Focused paper-card service pytest passed: `2 passed in 4.91s`.
- `bash scripts/check_research_workflow_primitives.sh` passed: `35 passed in 87.53s`.
- Fast guards passed: focused test coverage, suite contracts, script catalog, handoff docs, secret file guard, generated file guard, and `git --no-pager diff --check`.
- The remote safe suite was completed as its documented component scripts: pilot readiness `28 passed in 66.84s`, deployment contracts `1 passed in 1.68s`, research planning contracts `3 passed in 84.31s`, write audit `7 passed in 3.79s`, workflow job controls `3 passed in 110.86s`, tool bridge contracts `10 passed in 2.52s`, GraphRAG-lite `4 passed in 4.30s`, and context search `15 passed in 114.28s`.

## 2026-06-15 - Review And Experiment Service Contract Coverage

Implemented in progress:

- Added a service-level contract test for review and experiment-plan creation, missing idea errors, idea status progression, copied experiment fields, and list retrieval.
- Added the new test and `backend/research/services/review_service.py` plus `backend/research/services/experiment_service.py` lint coverage to `scripts/check_research_workflow_primitives.sh`.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` passed.
- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py backend/research/services/structured_extraction_service.py backend/research/services/gap_service.py backend/research/services/idea_service.py backend/research/services/paper_card_service.py backend/research/services/review_service.py backend/research/services/experiment_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py backend/research/services/structured_extraction_service.py backend/research/services/gap_service.py backend/research/services/idea_service.py backend/research/services/paper_card_service.py backend/research/services/review_service.py backend/research/services/experiment_service.py` passed.
- Focused review/experiment service pytest passed: `1 passed in 3.96s`.
- `bash scripts/check_research_workflow_primitives.sh` passed: `36 passed in 88.61s`.
- Fast guards passed: focused test coverage, suite contracts, script catalog, handoff docs, secret file guard, generated file guard, and `git --no-pager diff --check`.
- The remote safe suite was completed as its documented component scripts: pilot readiness `28 passed in 74.61s`, deployment contracts `1 passed in 1.79s`, research planning contracts `3 passed in 90.20s`, write audit `7 passed in 4.09s`, workflow job controls `3 passed in 114.38s`, tool bridge contracts `10 passed in 2.17s`, GraphRAG-lite `4 passed in 4.01s`, and context search `15 passed in 107.17s`.

## 2026-06-15 - Proposal Service Contract Coverage

Implemented in progress:

- Added no-network service-level contract tests for proposal draft section synthesis, proposal readiness scoring/missing-evidence decisions, and proposal revision action generation.
- Added the new tests and proposal service lint coverage to `scripts/check_research_proposal_contracts.sh`.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` passed after formatting the new tests.
- `.venv/bin/ruff check tests/test_app.py backend/research/routes.py backend/research/services/proposal_service.py backend/research/services/proposal_review_service.py backend/research/services/proposal_revision_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/routes.py backend/research/services/proposal_service.py backend/research/services/proposal_review_service.py backend/research/services/proposal_revision_service.py` passed.
- Focused proposal service pytest passed: `3 passed in 3.68s`.
- `bash scripts/check_research_proposal_contracts.sh` passed: `4 passed in 623.39s`; the original proposal end-to-end test is the dominant long-suite bottleneck.
- `bash scripts/check_remote_long_suite.sh` passed: focused coverage plus proposal contracts, `4 passed in 592.72s`.
- `bash scripts/check_remote_safe_suite.sh` passed. Pytest metrics inside the remote-safe suite: pilot readiness `28 passed in 73.73s`, deployment contracts `1 passed in 1.66s`, research workflow primitives `36 passed in 87.63s`, research planning contracts `3 passed in 87.88s`, write audit `7 passed in 3.12s`, workflow job controls `3 passed in 110.76s`, tool bridge contracts `10 passed in 2.20s`, GraphRAG-lite `4 passed in 4.34s`, and context search `15 passed in 104.03s`.
- Test-effect metrics for this slice: 3 new no-network proposal service contract tests, proposal focused suite increased from 1 to 4 tests, and default remote-safe pytest coverage remained green across 107 selected tests.

## 2026-06-15 - Proposal And Delivery Loop Test Split

Implemented in progress:

- Renamed the long proposal end-to-end test to `test_project_delivery_loop_bundles_proposal_to_pilot_handoff` so its project-delivery scope is explicit.
- Kept `scripts/check_research_proposal_contracts.sh` focused on proposal service contracts and added `scripts/check_project_delivery_loop.sh` for the long end-to-end delivery loop.
- Added the new long check to `scripts/check_remote_long_suite.sh`, `scripts/check_suite_contracts.sh`, and the README check-script catalog.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` passed.
- `.venv/bin/ruff check tests/test_app.py backend/research/routes.py backend/research/services/proposal_service.py backend/research/services/proposal_review_service.py backend/research/services/proposal_revision_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/routes.py backend/research/services/proposal_service.py backend/research/services/proposal_review_service.py backend/research/services/proposal_revision_service.py` passed.
- Split proposal-focused checks from the full delivery loop: `bash scripts/check_research_proposal_contracts.sh` passed with `3 passed in 3.27s`, compared with the prior proposal suite runtime of `4 passed in 623.39s`.
- Added and verified `bash scripts/check_project_delivery_loop.sh`: `1 passed in 639.78s`, preserving the full proposal-to-pilot handoff coverage as an explicit long check.
- `bash scripts/check_remote_long_suite.sh` passed with focused coverage, proposal contracts `3 passed in 1.69s`, and delivery loop `1 passed in 627.79s`.
- `bash scripts/check_remote_safe_suite.sh` passed. Pytest metrics inside the remote-safe suite: pilot readiness `28 passed in 76.37s`, deployment contracts `1 passed in 1.70s`, research workflow primitives `36 passed in 91.14s`, research planning contracts `3 passed in 84.67s`, write audit `7 passed in 4.02s`, workflow job controls `3 passed in 113.52s`, tool bridge contracts `10 passed in 2.15s`, GraphRAG-lite `4 passed in 4.28s`, and context search `15 passed in 107.51s`.
- Test-effect metrics for this slice: proposal-focused feedback now runs in seconds, full delivery-loop coverage remains available in the long suite, and default remote-safe pytest coverage remained green across 107 selected tests.


## 2026-06-15 - Isolated Project Delivery Loop Test Data

Implemented in progress:

- Made `scripts/check_project_delivery_loop.sh` use a per-run ignored test data directory for `RESEARCH_DB_URL` and `PAPER_UPLOAD_DIR` instead of the accumulated remote development database.
- Forced `EXTERNAL_LITERATURE_SEARCH_ENABLED=false` for the delivery-loop check so `.env` or remote runtime settings cannot turn the test into a network-dependent run.
- Added a research execution plan setup step inside `test_project_delivery_loop_bundles_proposal_to_pilot_handoff`, removing its hidden dependency on historical database state.
- Changed the delivery-loop and long-suite tail calls to `exec` so nested shell wrappers do not leave pytest hanging after the test process completes.
- Preserved the two pre-existing untracked root documents and did not read or print any `.env` or secret values.

Verification completed:

- Historical default database scale that explained the old project-level scan cost: 5123 papers, 18898 evidences, 5999 gaps, 6888 ideas, 3555 experiment plans, 17975 research tasks, and 60007 graph edges.
- Before isolation, `bash scripts/check_project_delivery_loop.sh` passed in `1 passed in 639.78s`; the long suite delivery-loop segment passed in `1 passed in 627.79s`.
- During isolation, the test failed fast on a clean database with `readiness_level=nearly_ready` and missing `Research execution plan`, proving the old pass depended on historical remote data.
- After adding the research plan setup, the isolated direct pytest run passed: `1 passed in 10.03s`.
- `PROJECT_DELIVERY_LOOP_TIMEOUT_SECONDS=60 bash scripts/check_project_delivery_loop.sh` passed: `1 passed in 7.99s`.
- `bash scripts/check_research_proposal_contracts.sh` passed: `3 passed in 1.71s`.
- `bash scripts/check_remote_long_suite.sh` passed with focused coverage, proposal contracts `3 passed in 1.81s`, and delivery loop `1 passed in 8.43s`.
- `bash scripts/check_remote_safe_suite.sh` passed. Pytest metrics inside the remote-safe suite: pilot readiness `28 passed in 11.99s`, deployment contracts `1 passed in 1.78s`, research workflow primitives `36 passed in 7.25s`, research planning contracts `3 passed in 4.25s`, write audit `7 passed in 3.91s`, workflow job controls `3 passed in 3.81s`, tool bridge contracts `10 passed in 2.27s`, GraphRAG-lite `4 passed in 3.22s`, and context search `15 passed in 8.42s`.
- Test-effect metrics for this slice: delivery-loop check dropped from about 10.7 minutes to under 10 seconds, long-suite delivery-loop coverage is now isolated and repeatable, and default remote-safe pytest coverage remained green across 107 selected tests.


## 2026-06-15 - Bundle Readiness Transition Contract

Implemented in progress:

- Added an explicit project-bundle readiness transition assertion inside `test_project_delivery_loop_bundles_proposal_to_pilot_handoff`.
- The delivery loop now verifies that a fully prepared handoff without a research execution plan reports `nearly_ready`, a readiness score below 1.0, `Research execution plan` in `missing_required`, and a `research_plan` quick action before the plan is created.
- The same test then creates the research plan and verifies the final `delivery_ready` state, keeping the hidden historical-data dependency closed.
- Preserved the two pre-existing untracked root documents and did not read or print any `.env` or secret values.

Verification completed:

- `PROJECT_DELIVERY_LOOP_TIMEOUT_SECONDS=60 bash scripts/check_project_delivery_loop.sh` passed: `1 passed in 10.16s`.
- `bash scripts/check_remote_long_suite.sh` passed with focused coverage, proposal contracts `3 passed in 1.67s`, and delivery loop `1 passed in 8.36s`.
- `bash scripts/check_remote_safe_suite.sh` passed. Pytest metrics inside the remote-safe suite: pilot readiness `28 passed in 14.51s`, deployment contracts `1 passed in 1.72s`, research workflow primitives `36 passed in 7.75s`, research planning contracts `3 passed in 4.90s`, write audit `7 passed in 4.02s`, workflow job controls `3 passed in 4.77s`, tool bridge contracts `10 passed in 2.22s`, GraphRAG-lite `4 passed in 3.01s`, and context search `15 passed in 9.01s`.
- Test-effect metrics for this slice: one more user-visible readiness transition is covered in the isolated delivery-loop check, and default remote-safe pytest coverage remained green across 107 selected tests.


## 2026-06-15 - Product Effect Smoke Evaluation

Implemented in progress:

- Ran the existing end-to-end smoke workflow in an isolated in-process mode to evaluate product-level behavior rather than only unit-test coverage.
- Ran the same smoke workflow against a temporary real HTTP `uvicorn` service on `127.0.0.1:18081`, using isolated SQLite and upload directories under `data/test-runs/`.
- Added `docs/product_effect_report.md` to summarize current product target, smoke metrics, strengths, gaps, readiness estimate, and recommended next steps.
- Did not read or print `.env`, token, cookie, password, private key, or credential files; the temporary HTTP service was closed by `timeout` and no service process was left running.

Verification completed:

- In-process smoke passed with service readiness `ready`, Workbench available, `119` tool-manifest entries, `119` MCP bridge tools, `3` gaps, `6` ideas, proposal review `ready_for_advisor_review` at score `0.92`, experiment analysis `supports_hypothesis`, project bundle `71` files, project-bundle readiness `delivery_ready` at score `1.0`, and `100` graph nodes / `100` graph edges in the final summary.
- Real HTTP smoke passed against temporary `uvicorn` with the same key metrics: service readiness `ready`, Workbench available, `3` gaps, `6` ideas, proposal review `ready_for_advisor_review`, readiness decision `needs_targeted_work`, quality-gate decision `de_risk_novelty`, advisor chat intent `risk_review`, project bundle `71` files, project-bundle readiness `delivery_ready` at score `1.0`, and `100` graph nodes / `100` graph edges.
- The temporary HTTP server shut down cleanly after `timeout`; `pgrep` found no remaining `uvicorn`, `smoke_api`, pytest, or check-suite processes.
- Test-effect metrics for this slice: the product is now verified in both TestClient and real HTTP modes with isolated data, moving the project from pure engineering validation toward demo-readiness validation.


## 2026-06-15 - Product Smoke Runbook

Implemented in progress:

- Added `scripts/check_product_effect_smoke.sh`, an isolated product-effect smoke entrypoint that defaults to a per-run SQLite database and upload directory under `data/test-runs/`.
- Added `docs/demo_runbook.md` with safe in-process and temporary HTTP smoke workflows, expected indicators, baseline metrics, and demo-readiness interpretation.
- Updated the README check-script catalog and verification section so the product-effect smoke is discoverable.
- Preserved the two pre-existing untracked root documents and did not read or print any `.env` or secret values.

Verification completed:

- `PRODUCT_EFFECT_SMOKE_TIMEOUT_SECONDS=300 bash scripts/check_product_effect_smoke.sh` passed with isolated test data and external literature search disabled by default.
- Key metrics from the new script: service readiness `ready`, Workbench available, `119` tool-manifest entries, `119` MCP bridge tools, `3` gaps, `6` ideas, proposal review `ready_for_advisor_review` at score `0.92`, experiment analysis `supports_hypothesis`, project bundle `71` files, project-bundle readiness `delivery_ready` at score `1.0`, and `100` graph nodes / `100` graph edges.
- Test-effect metrics for this slice: product-effect smoke is now a repeatable check script and demo runbook entry instead of an ad hoc command sequence.


## 2026-06-15 - Workbench Product Surface Contract

Implemented in progress:

- Extended `test_workbench_static_assets_are_served` to verify the Workbench main product path exposes stable navigation sections from Pilot Launch through Dossier.
- Added CSS surface assertions for the Workbench shell, grid layout, controls grid, and responsive breakpoint so the static product entrypoint keeps a desktop/mobile layout contract.
- Preserved the two pre-existing untracked root documents and did not read or print any `.env` or secret values.

Verification completed:

- `bash scripts/check_pilot_readiness.sh` passed: `28 passed in 79.36s`.
- `bash scripts/check_remote_safe_suite.sh` passed. Pytest metrics inside the remote-safe suite: pilot readiness `28 passed in 78.48s`, deployment contracts `1 passed in 1.68s`, research workflow primitives `36 passed in 100.98s`, research planning contracts `3 passed in 100.35s`, write audit `7 passed in 3.59s`, workflow job controls `3 passed in 122.56s`, tool bridge contracts `10 passed in 2.22s`, GraphRAG-lite `4 passed in 4.45s`, and context search `15 passed in 111.76s`.
- Test-effect metrics for this slice: the user-visible Workbench shell now has a focused product-surface contract, and default remote-safe pytest coverage remained green across 107 selected tests.


## 2026-06-15 - Representative Markdown Product Smoke

Implemented in progress:

- Added representative paper fixture support to `scripts/smoke_api.py` through `--paper-file` and exposed it in `scripts/check_product_effect_smoke.sh` as `PRODUCT_EFFECT_SMOKE_PAPER_FILE=/path/to/paper.md`.
- Updated README and `docs/demo_runbook.md` so the product-effect smoke can be run against a realistic local paper fixture, not only the built-in deterministic smoke paper.
- Improved Markdown ingestion so ATX headings such as `## Limitations` are normalized before section detection.
- Added `Future Work` / `Future Directions` / `Next Steps` as explicit section patterns that map to `future_work` evidence and application-gap mining.
- Added `test_markdown_gap_sections_are_mined_from_headings` and registered it in `scripts/check_research_workflow_primitives.sh`, including ruff coverage for `document_ingestion.py`.
- Preserved the two pre-existing untracked root documents and did not read or print any `.env`, token, cookie, password, private key, or credential values.

Verification completed:

- Targeted regression test passed with isolated SQLite/upload directories: `tests/test_app.py::test_markdown_gap_sections_are_mined_from_headings` -> `1 passed in 4.29s`.
- Representative Markdown product-effect smoke passed with `PRODUCT_EFFECT_SMOKE_PAPER_FILE=/tmp/raa_gap_rich_paper.md`: service readiness `ready`, Workbench available, `119` tool-manifest entries, `119` bridge tools, `3` gaps, `6` ideas, proposal review `ready_for_advisor_review` at score `0.92`, experiment analysis `supports_hypothesis`, evidence ledger coverage `0.24`, project bundle `71` files, project-bundle readiness `delivery_ready` at score `1.0`, and `100` graph nodes / `100` graph edges.
- Default product-effect smoke still passed after the ingestion change: service readiness `ready`, Workbench available, `3` gaps, `6` ideas, proposal review score `0.92`, project bundle `71` files, project-bundle readiness score `1.0`, and `100` graph nodes / `100` graph edges.
- `bash scripts/check_script_catalog.sh` passed: check script catalog is synchronized.
- `bash scripts/check_research_workflow_primitives.sh` passed after registering the new test: `37 passed in 99.98s`.
- `bash scripts/check_remote_safe_suite.sh` passed. Pytest metrics inside the remote-safe suite: pilot readiness `28 passed in 99.28s`, deployment contracts `1 passed in 1.35s`, research workflow primitives `37 passed in 90.24s`, research planning contracts `3 passed in 95.83s`, write audit `7 passed in 4.72s`, workflow job controls `3 passed in 153.72s`, tool bridge contracts `10 passed in 2.25s`, GraphRAG-lite `4 passed in 4.44s`, and context search `15 passed in 110.32s`.
- Test-effect metrics for this slice: representative Markdown papers with explicit Limitations/Future Work sections now produce mined gaps in both a focused regression test and the full product smoke, raising the selected remote-safe pytest coverage from 107 to 108 tests.
