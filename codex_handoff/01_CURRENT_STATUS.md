# Current Status

This file separates stable, pushed work from local draft work.

## Stable Source Of Truth

The stable source of truth is the remote Linux project and GitHub repository:

- Remote path: `/home/zhangwz/Research-Assistant-Agent`
- GitHub: `https://github.com/ImpZhang/Research-Assistant-Agent.git`
- Last known stable pushed commit before this handoff pack: `b3baf94 Add release review outcome progress`

On Mac, start from GitHub unless the user explicitly provides a newer archive or remote diff.

## What Is Already Completed

### Project Foundation

- New project directory created independently from the old `super-mew` project.
- FastAPI application scaffolded.
- SQLAlchemy models and SQLite persistence implemented.
- `uv` development flow established.
- Unit tests and a large smoke workflow exist.
- Docker and docker-compose pilot deployment files exist.
- Optional API key protection exists for `/research/*`.
- `/health` and `/health/ready` exist.
- Static Workbench exists at `/workbench`.

### Literature And RAG Foundation

Completed capabilities:

- upload `.txt`, `.md`, and `.pdf` papers;
- parse and store paper records;
- chunk papers and extract evidence;
- build deterministic paper cards;
- use OpenAI-compatible structured extraction when configured;
- fall back to heuristic extraction when no model credentials are provided;
- search local literature context;
- optional external literature search adapters for OpenAlex, arXiv, and Semantic Scholar;
- local hashed embedding index;
- lexical/vector retrieval;
- GraphRAG-lite context retrieval.

### Idea Generation And Evaluation

Completed capabilities:

- research gap mining;
- structured idea generation;
- novelty/collision checks against local evidence, gaps, ideas, and optional external search;
- configurable novelty refresh;
- reviewer simulation;
- related-work matrix generation;
- proposal draft generation;
- proposal readiness review;
- proposal revision;
- idea lineage;
- idea activity timeline;
- idea progress summary;
- idea research packet;
- idea readiness score;
- idea quality gate;
- idea decision memo;
- idea assumption audit;
- idea evidence ledger;
- per-claim validation packets;
- project-level claim validation queue;
- claim validation result tracking/reporting/decision signals;
- idea portfolio ranking, saved snapshots, comparison, feedback, and 30/60/90-day agenda export.

### Experiment And Task Execution

Completed capabilities:

- experiment plan generation;
- experiment run tracking;
- experiment result analysis;
- task generation from proposal revision, novelty checks, readiness blockers, quality gates, experiment analysis, decision memos, evidence ledger actions, claim validation queue, project cockpit, advisor chat, triage, bundle readiness, release steps, review outcomes, etc.;
- task status updates;
- task event logs;
- task board snapshots;
- Workbench task-board controls.

### Project-Level Workflow

Completed capabilities:

- research profile storage and Markdown export;
- project progress overview;
- project readiness overview;
- project quality gate overview;
- project onboarding readiness;
- project setup wizard;
- project onboarding tasks;
- project onboarding progress;
- customer-facing pilot status report;
- persisted pilot report snapshots;
- pilot report snapshot comparison;
- pilot report snapshot task generation;
- project cockpit dashboard;
- project cockpit Markdown export;
- project advisor chat;
- advisor chat task generation;
- advisor action session;
- project triage brief;
- triage task generation;
- persisted triage snapshots;
- triage snapshot comparison;
- triage comparison task generation;
- research opportunity radar;
- opportunity radar task generation;
- advisor research briefs;
- research execution plans;
- plan task generation;
- plan progress reports;
- plan-aware advisor brief/progress/packet/bundle checks.

### Handoff And Delivery Workflow

The project has moved deeply into delivery/handoff features. Completed:

- idea bundle export;
- project handoff bundle export;
- project bundle readiness check;
- bundle readiness task generation;
- persisted bundle readiness snapshots;
- bundle readiness snapshot comparison;
- bundle readiness comparison task generation;
- project bundle release notes;
- release note task generation;
- project bundle release progress tracking;
- release feedback records;
- release feedback task generation;
- release closeout reports;
- release closeout task generation;
- release acceptance packets;
- persisted release acceptance packet snapshots;
- release acceptance snapshot comparison;
- release acceptance comparison task generation;
- release review sessions;
- release review session task generation;
- persisted release review outcomes;
- release review outcome task generation;
- release review outcome progress reports.

Latest stable pushed feature:

- `project_bundle_release_review_outcome_progress_tracking`
- route: `GET /research/export/project-bundle/releases/{release_id}/review-session/outcomes/{outcome_id}/progress`
- tool manifest name: `get_project_bundle_release_review_outcome_progress`
- project bundle artifacts:
  - `metadata/project-bundle-release-review-outcome-progress.json`
  - `artifacts/releases/latest-project-bundle-release-review-outcome-progress.md`
- manifest fields include latest progress availability, completion ratio, open task count, and blocked task count.

### MCP And External Tool Contract

Completed:

- `/research/tools/manifest`
- `/research/tools/mcp-spec`
- `scripts/mcp_http_bridge.py`
- read-only mode support;
- allow/deny tool filters;
- API key forwarding;
- health-check mode;
- binary zip bundle response handling as base64 text payloads.

Important: MCP is currently an adapter around stable HTTP tools. It is not the internal orchestration engine.

## What Is Determined

These decisions are settled unless the user explicitly changes strategy:

- Build the new project as `Research-Assistant-Agent`, not as a small patch to old `super-mew`.
- Keep FastAPI as the backend API layer.
- Keep SQLite for current pilot/dev, with production database migration as later hardening.
- Keep deterministic fallbacks so the system works without model credentials.
- Use GraphRAG-lite now, not full GraphRAG/Neo4j.
- Do not migrate DeerFlow now.
- Keep MCP as a bridge/spec layer for external tools, not core business logic.
- Every completed implementation round should be committed and pushed to GitHub.
- Use project bundle/release/review artifacts as the main path toward customer-facing value.

## What Is Not Completed

Major missing or incomplete areas:

- Full customer-grade SaaS frontend.
- Multi-user accounts, organizations, roles, permissions, invitation flows.
- Full audit log for all write operations.
- Durable background worker queue for long-running jobs.
- Production database migrations and production database choice.
- Full observability: structured logs, metrics, traces, alerts, error reporting.
- Robust file/object storage beyond local volume.
- Full external paper refresh monitoring and scheduled novelty refresh.
- Full GraphRAG indexing/community summarization.
- Full LangGraph/DeerFlow orchestration layer.
- Formal managed MCP server package; currently only lightweight bridge.
- Payment/billing/admin/customer management, if the product becomes SaaS.
- Polished customer-facing UX across every workflow.

## Current In-Progress Feature

The next planned feature before this handoff request was:

> Project bundle release review outcome signoff evidence records.

Purpose:

- After a release review outcome and its follow-up progress exist, the system should persist who signed/deferred/declined, under what conditions, with accepted artifacts and evidence links.
- This should be connected to the review outcome, progress snapshot, GraphRAG-lite, tool manifest, Workbench, project bundle metadata/artifacts, tests, smoke workflow, and docs.

Known local draft edits may exist in the Windows mirror for:

- `backend/research/schemas.py`
- `backend/research/routes.py`
- `backend/research/services/artifact_graph_service.py`

Treat these as partial WIP unless GitHub contains a later commit.

Expected feature shape:

- Create schema: `ProjectBundleReleaseReviewOutcomeSignoffCreate`
- New brief scope: `project_bundle_release_review_outcome_signoff`
- New graph edge: `project_bundle_release_review_outcome_has_signoff`
- New endpoints:
  - `POST /research/export/project-bundle/releases/{release_id}/review-session/outcomes/{outcome_id}/signoffs`
  - `GET /research/export/project-bundle/releases/{release_id}/review-session/outcomes/{outcome_id}/signoffs`
  - `GET /research/export/project-bundle/releases/{release_id}/review-session/outcomes/{outcome_id}/signoffs/{signoff_id}`
  - `GET /research/export/project-bundle/releases/{release_id}/review-session/outcomes/{outcome_id}/signoffs/{signoff_id}/export/markdown`
- New tool manifest entries.
- New bundle metadata/artifacts:
  - `metadata/project-bundle-release-review-outcome-signoffs.json`
  - `artifacts/releases/project-bundle-release-review-outcome-signoff-{id}.md`
  - `artifacts/releases/latest-project-bundle-release-review-outcome-signoff.md`
- New Workbench controls:
  - record signoff evidence;
  - list outcome signoffs.
- Tests and smoke workflow coverage.

## Current Blockers

No conceptual blocker.

Practical blockers for Mac continuation:

- Need a clean Mac clone from GitHub.
- Need Python 3.12 and `uv` installed.
- Need `.env` recreated on Mac from `.env.example`; do not copy secrets into docs.
- Need to know whether to continue from latest GitHub or from any unpushed Windows WIP. Default: continue from GitHub.
- Need to avoid editing historical untracked root docs on the remote Linux machine:
  - `/home/zhangwz/Research-Assistant-Agent/research_assistant_requirements.md`
  - `/home/zhangwz/Research-Assistant-Agent/research_assistant_technical_design.md`

## Last Known Verification

For commit `b3baf94 Add release review outcome progress`, the remote verification reportedly passed:

- `ruff check`
- touched-file `ruff format --check`
- targeted tests for project bundle release review outcome progress
- full pytest: `43/43`
- smoke workflow passed
- tool manifest count: `114`
- project bundle file count: `156`

When Mac Codex resumes, rerun current tests rather than assuming this still holds.

