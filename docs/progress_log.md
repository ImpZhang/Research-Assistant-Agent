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
