# Important Files

This file maps the codebase for a new Codex.

## Root Files

### `README.md`

Primary user/developer overview. It lists implemented capabilities, quick start, verification, useful endpoints, MCP bridge, deployment pointer, and future work.

Update this whenever a user-visible capability is added.

### `pyproject.toml`

Python package metadata, dependencies, dev dependencies, pytest config, and ruff config.

Be careful changing dependency versions because the remote environment and smoke workflow rely on `uv`.

### `.env.example`

Template for local environment variables.

Do not put real values here.

### `.gitignore`

Should keep generated data, virtual environments, and secrets out of Git.

### `Dockerfile`

Single-container pilot runtime.

### `docker-compose.yml`

Production-ish pilot deployment with persistent volume and required `API_KEY` environment variable.

## Backend App

### `backend/app.py`

FastAPI app assembly, static file mounting, health endpoints, API-key middleware/guard behavior.

Touch this for:

- app-level middleware;
- health/readiness checks;
- deployment/runtime concerns;
- Workbench static mount.

### `backend/research/config.py`

Settings and environment variable loading.

Touch this when adding feature flags or runtime config.

### `backend/research/db.py`

Database engine/session setup.

Be careful changing this without a migration plan.

### `backend/research/models.py`

SQLAlchemy domain models.

Important model families:

- `Paper`
- `Evidence`
- `Idea`
- workflow/job artifacts
- `ResearchTask`
- `ResearchBrief`
- graph nodes/edges
- research plans and snapshots

Do not casually add tables if existing generic artifact models such as `ResearchBrief` are enough.

### `backend/research/schemas.py`

Pydantic request/response models.

Most new endpoints require schema additions here. Keep schemas explicit and stable because tool manifest/MCP spec depend on them.

### `backend/research/routes.py`

Main FastAPI route file and many helper functions.

This is the largest and most central file. It includes:

- status/capability reporting;
- tool manifest;
- MCP spec entry source;
- route handlers;
- project bundle builder;
- Markdown renderers;
- manifest metadata functions;
- many helper functions for current-state views.

Be careful:

- Keep edits scoped.
- Update tool manifest when adding stable APIs.
- Update project bundle context/zip/manifest when adding handoff artifacts.
- Keep deterministic behavior in routes used by tests and smoke.

## Backend Services

### `backend/research/services/workflow_service.py`

Literature-to-ideas workflow execution.

Touch this for main workflow changes, job trace updates, or async workflow behavior.

### `backend/research/services/retrieval_service.py`

Lexical/vector/GraphRAG-lite context retrieval.

Touch this for retrieval behavior.

### `backend/research/services/graph_service.py`

Low-level graph node/edge persistence and list/query helpers.

Touch this for generic graph storage behavior.

### `backend/research/services/artifact_graph_service.py`

High-level artifact-to-graph link writer.

When a new artifact is persisted, add graph linkage here if it needs lineage or GraphRAG-lite traceability.

### `backend/research/services/task_service.py`

Task creation from artifacts and project states.

Touch this when a feature should generate actionable tasks.

### `backend/research/services/tool_bridge_service.py`

Converts tool manifest entries into MCP-ready HTTP bridge spec.

Usually do not hardcode tools here; update the manifest source in routes.

### Other Domain Services

Files such as:

- `paper_service.py`
- `gap_service.py`
- `idea_service.py`
- `novelty_service.py`
- `related_work_service.py`
- `proposal_service.py`
- `proposal_review_service.py`
- `proposal_revision_service.py`
- `experiment_service.py`
- `experiment_run_service.py`
- `experiment_analysis_service.py`
- `decision_memo_service.py`
- `assumption_audit_service.py`
- `evidence_ledger_service.py`
- `research_plan_service.py`
- `triage_snapshot_service.py`

These hold domain-specific logic. Prefer extending the relevant service instead of bloating routes when logic is reusable.

## Frontend Workbench

### `backend/static/workbench/index.html`

Workbench markup and button/control placement.

Add controls here when exposing a route to the pilot UI.

### `backend/static/workbench/app.js`

Workbench behavior.

Important patterns:

- use existing `api()` helper;
- keep state in the central state object;
- route calls should go through backend APIs;
- render Markdown/dossier previews rather than duplicating backend business logic.

### `backend/static/workbench/styles.css`

Workbench styling.

Do not spend too much time polishing before the backend flow is stable, but avoid broken/overlapping UI.

## Tests And Smoke

### `tests/test_app.py`

Large integration-style test suite using FastAPI TestClient.

Update this for:

- new status capabilities;
- tool manifest entries;
- MCP spec entries;
- endpoint behavior;
- graph edge checks;
- project bundle metadata/artifacts;
- Workbench static references.

### `scripts/smoke_api.py`

End-to-end smoke workflow covering the current research workflow.

Update this when adding user-visible capabilities in the main project flow. It is long but crucial because it validates realistic route chaining and project bundle contents.

### `scripts/mcp_http_bridge.py`

Lightweight stdio MCP-to-HTTP bridge.

Only update if the bridge behavior itself changes. Normal tool additions should flow from `/research/tools/mcp-spec`.

## Docs

### `docs/research_assistant_requirements.md`

Detailed requirements and product rationale in Chinese.

Update when adding a new requirement or closing a planned requirement.

### `docs/research_assistant_technical_design.md`

Architecture, technical decisions, endpoint design, ADRs, and implementation notes.

Update when adding a new capability or changing architecture.

### `docs/deployment.md`

Deployment/runtime notes, API-key usage, Docker, MCP bridge with API key, Workbench API key.

Update when deployment behavior changes.

### `codex_handoff/*.md`

Migration handoff pack for new Codex sessions. These files are context, not executable code.

Update these when the project changes enough that a fresh Codex would otherwise be confused.

## Files Not To Casually Modify

Avoid touching unless required:

- `.env` if it exists locally: may contain secrets and should not be committed.
- `data/` if it exists: generated DB/uploads.
- remote root historical untracked files:
  - `/home/zhangwz/Research-Assistant-Agent/research_assistant_requirements.md`
  - `/home/zhangwz/Research-Assistant-Agent/research_assistant_technical_design.md`
- generated `__pycache__` directories.
- virtual environments such as `.venv`.

## High-Risk Files

### `backend/research/routes.py`

Risk:

- Very large central file.
- Easy to break imports, route order, helper order, or manifest context.

Best practice:

- Use `rg` before editing.
- Make small patches.
- Run ruff and targeted tests.

### `tests/test_app.py`

Risk:

- Long test depends on chained state.
- A small variable-name mistake can break later assertions.

Best practice:

- Add assertions near existing related flow.
- Keep names explicit.

### `scripts/smoke_api.py`

Risk:

- Very long smoke workflow.
- It validates many side effects and project bundle files.

Best practice:

- Add smoke checks adjacent to existing related capability.
- Use existing helper functions such as `require_ok`.

