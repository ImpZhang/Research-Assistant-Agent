# TODO

This is the prioritized continuation list for Mac Codex.

## Priority 0: Start From A Clean Mac Clone

Goal:

- Make sure Mac Codex starts from a clean and current repository.

Commands:

```bash
mkdir -p ~/Projects
cd ~/Projects
git clone https://github.com/ImpZhang/Research-Assistant-Agent.git
cd Research-Assistant-Agent
git status --short
git log --oneline -5
```

Files to inspect:

- `README.md`
- `codex_handoff/00_PROJECT_CONTEXT.md`
- `codex_handoff/01_CURRENT_STATUS.md`
- `codex_handoff/02_DECISIONS.md`
- `docs/research_assistant_requirements.md`
- `docs/research_assistant_technical_design.md`

Expected:

- Clean Git worktree.
- Latest commit at least `b3baf94 Add release review outcome progress`, or newer if handoff docs were pushed.

## Priority 1: Re-Run Baseline Verification On Mac

Goal:

- Confirm the Mac environment can run the existing project before adding features.

Files to inspect:

- `pyproject.toml`
- `.env.example`
- `README.md`
- `scripts/smoke_api.py`
- `tests/test_app.py`

Commands:

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run python scripts/smoke_api.py
```

If full smoke is too slow, first run:

```bash
uv run pytest -q tests/test_app.py
```

Notes:

- The project should pass without model credentials because deterministic fallbacks exist.
- If `.env` is needed, create it from `.env.example` and fill local values outside this handoff documentation.

## Completed: Review Outcome Signoff Evidence Records

Status:

- Completed remotely and pushed in `d2e0741 Add release review outcome signoff evidence`.
- Verification completed with focused pytest, full pytest, and smoke API.

Original goal:

- Add durable signoff evidence for project bundle release review outcomes.

Why:

- The current delivery chain has review outcome and outcome progress.
- It still needs a durable record of signoff/defer/decline decisions, approver, conditions, accepted artifacts, and evidence links.

Primary files:

- `backend/research/schemas.py`
- `backend/research/routes.py`
- `backend/research/services/artifact_graph_service.py`
- `backend/static/workbench/app.js`
- `backend/static/workbench/index.html`
- `tests/test_app.py`
- `scripts/smoke_api.py`
- `README.md`
- `docs/research_assistant_requirements.md`
- `docs/research_assistant_technical_design.md`

Expected backend shape:

- Schema:
  - `ProjectBundleReleaseReviewOutcomeSignoffCreate`
- Brief scope:
  - `project_bundle_release_review_outcome_signoff`
- Graph node type:
  - `project_bundle_release_review_outcome_signoff`
- Graph edge:
  - `project_bundle_release_review_outcome_has_signoff`
- Routes:
  - `POST /research/export/project-bundle/releases/{release_id}/review-session/outcomes/{outcome_id}/signoffs`
  - `GET /research/export/project-bundle/releases/{release_id}/review-session/outcomes/{outcome_id}/signoffs`
  - `GET /research/export/project-bundle/releases/{release_id}/review-session/outcomes/{outcome_id}/signoffs/{signoff_id}`
  - `GET /research/export/project-bundle/releases/{release_id}/review-session/outcomes/{outcome_id}/signoffs/{signoff_id}/export/markdown`
- Tool manifest names:
  - `record_project_bundle_release_review_outcome_signoff`
  - `list_project_bundle_release_review_outcome_signoffs`
  - `get_project_bundle_release_review_outcome_signoff`
  - `export_project_bundle_release_review_outcome_signoff_markdown`

Expected bundle additions:

- `metadata/project-bundle-release-review-outcome-signoffs.json`
- `artifacts/releases/project-bundle-release-review-outcome-signoff-{signoff_id}.md`
- `artifacts/releases/latest-project-bundle-release-review-outcome-signoff.md`
- manifest fields:
  - `project_bundle_release_review_outcome_signoff_count`
  - `latest_project_bundle_release_review_outcome_signoff_id`
  - `latest_project_bundle_release_review_outcome_signoff_release_id`
  - `latest_project_bundle_release_review_outcome_signoff_outcome_id`
  - `latest_project_bundle_release_review_outcome_signoff_decision`
  - `latest_project_bundle_release_review_outcome_signoff_confirmed`
  - `latest_project_bundle_release_review_outcome_signoff_approver`
  - `latest_project_bundle_release_review_outcome_signoff_progress_completion_ratio`
  - `latest_project_bundle_release_review_outcome_signoff_progress_open_task_count`

Expected Workbench additions:

- Record signoff button near review outcome progress.
- List signoffs button near review outcome progress.
- Save latest signoff id in Workbench state.
- Render returned Markdown/dossier preview.

Expected test additions:

- capability in `/research/status`;
- tool manifest entries;
- MCP spec entries with read-only/write annotations;
- route create/list/detail/export;
- graph edge assertion;
- project bundle file and manifest assertions;
- Workbench static assertions;
- smoke workflow coverage.

Validation:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run python scripts/smoke_api.py
```

Commit suggestion:

```bash
git add README.md docs backend tests scripts
git commit -m "Add release review outcome signoffs"
git push origin main
```

## Priority 3: Harden Customer-Facing Pilot Readiness

Goal:

- Move from "developer pilot" to "early customer pilot".

Completed slices:

- Added a read-only Workbench Pilot Launch panel in `298f187 Add Workbench pilot launch status`.
- The panel aggregates onboarding readiness, onboarding progress, and cockpit state without writing data.
- Added Workbench empty/error state helpers for API-key, network, and missing-input first-run failures.
- Added a pilot deployment checklist to `docs/deployment.md` and linked it from README.
- Designed write-operation audit logging in `docs/write_operation_audit_design.md` before persistence changes.
- Extended Workbench empty states to delivery workflows such as bundle releases, review outcomes, snapshots, and research plans.
- Added `/app/data` backup/restore operator notes to `docs/deployment.md`.
- Added a disabled-by-default JSONL write-operation audit helper and middleware prototype.
- Grouped Workbench dossier controls into idea loop, task board, project delivery, and project operations sections.
- Added admin-gated write-operation audit summary and bounded raw JSONL export endpoints after documenting admin authorization and retention/export policy.

Next likely work:

- Decide whether backup/restore should become a checked script after deployment target details are fixed.
- Decide whether write-operation audit should graduate from JSONL to database persistence after migration strategy is settled.
- Decide whether write-operation audit rotation/cleanup should be implemented after backup/retention decisions are settled.
- Run a remote smoke workflow against the current main branch when the operator approves service startup.

Suggested next narrow slices:

1. Add a checked backup script only after the operator confirms the deployment host/volume naming convention.
2. Add audit rotation/cleanup only after the backup workflow and retention policy are confirmed.
3. Run a remote smoke workflow against the current main branch when the operator approves service startup.

Files:

- `backend/static/workbench/app.js`
- `backend/static/workbench/index.html`
- `backend/static/workbench/styles.css`
- `backend/research/routes.py`
- `docs/deployment.md`
- `README.md`
- `tests/test_app.py`

## Priority 4: Add Production Data And Auth Hardening

Goal:

- Make the project safer for real pilot usage.

Completed slices:

- Documented the database migration strategy in `docs/database_migration_strategy.md` without adding migration tooling or changing production data.
- Added upload extension and size validation before writing uploaded papers to disk.
- Added secret-safe API key fingerprint metadata to JSONL write-operation audit records.
- Documented the admin authorization boundary for future audit summary/export access.
- Added a default-off, admin-gated write-operation audit summary endpoint.
- Added lightweight upload content sniffing before uploaded papers are written to disk.
- Documented write-operation audit retention and operator export workflow before raw export code.
- Added a default-off, admin-gated, bounded raw JSONL write-audit export endpoint.
- Documented the user/project scoping model in `docs/user_project_scoping_design.md` before adding schema migrations.
- Added write-operation audit directory readiness checks for pilot deployments.

Likely work:

- Introduce migration tooling only after operator approval and dependency sync approval.
- Implement user/project scoping only after migration tooling and auth identity are explicit.
- Add write-operation audit rotation/cleanup hardening only after backup workflow approval.
- Add deeper write-operation audit log persistence hardening after rotation/backup decisions.
- Add backup/restore script for `/data` only after the operator confirms the deployment host/volume naming convention.
- Consider antivirus scanning or deeper MIME inspection for stricter customer environments.

Files:

- `backend/research/models.py`
- `backend/research/db.py`
- `backend/app.py`
- `backend/research/config.py`
- `docs/deployment.md`
- `docker-compose.yml`

## Priority 5: Upgrade Long-Running Workflow Execution

Goal:

- Replace in-process background execution with a more durable queue when needed.

Candidate options:

- RQ/Redis for simple queued jobs.
- Celery for broader queue ecosystem.
- Dramatiq for lighter background jobs.
- Temporal only if workflow durability and visibility become central.

Completed so far:

- Documented the durable workflow queue design in `docs/workflow_queue_design.md` before adding dependencies, services, migrations, or changing runtime behavior.

Likely work:

- Confirm the deployment queue backend and worker process policy before adding Redis, RQ, Celery, Dramatiq, or Temporal.
- Keep `/research/workflows/literature-to-ideas/async`, `/research/jobs/{job_id}`, retry, cancel, and artifact routes backward compatible during any migration.
- Add queue/worker readiness checks only after the operator confirms the deployment topology.
- Add job leasing, heartbeat, retry, and idempotency fields only after the database migration path is approved.

Files:

- `backend/research/services/workflow_service.py`
- `backend/research/routes.py`
- `backend/research/models.py`
- `docker-compose.yml`
- `docs/research_assistant_technical_design.md`
- `docs/workflow_queue_design.md`

Do not do this before customer-facing flow gaps unless the user explicitly prioritizes reliability over feature completion.

## Priority 6: Revisit Full GraphRAG / LangGraph / DeerFlow

Goal:

- Evaluate heavier orchestration and graph retrieval only after service boundaries stabilize.

When to revisit:

- Many workflows need resumable DAG state.
- Agent tasks run for minutes/hours.
- Knowledge graph scale exceeds simple relational node/edge traversal.
- Users ask for automatic deep research reports across many tools and sources.

Completed so far:

- Documented the P6 GraphRAG/LangGraph/DeerFlow evaluation in `docs/graphrag_langgraph_deerflow_evaluation.md`; current recommendation is to keep GraphRAG-lite and service-layer workflows until explicit scale/durability/tool-sandbox triggers appear.

Likely work:

- Strengthen GraphRAG-lite edge quality, retrieval ranking, and graph observability before adding a full GraphRAG indexing/community-summary pipeline.
- Use LangGraph only for a new isolated workflow once resumable DAG state, checkpointing, or human-in-the-loop control is required.
- Treat DeerFlow as a future external planner/tool consumer through the stable tool manifest and MCP bridge, not as the core runtime.

Files:

- `docs/research_assistant_technical_design.md`
- `backend/research/services/graph_service.py`
- `backend/research/services/retrieval_service.py`
- `backend/research/services/workflow_service.py`
- `docs/graphrag_langgraph_deerflow_evaluation.md`

Default:

- Keep GraphRAG-lite and current service workflows for now.

