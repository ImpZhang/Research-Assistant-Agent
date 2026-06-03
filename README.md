# Research Assistant Agent

Research Assistant Agent is a backend-first research workflow system rebuilt from the lessons of SuperMew. It is not a plain RAG chatbot: the goal is to turn literature evidence into research gaps, testable ideas, novelty checks, related-work matrices, proposal drafts, reviewer critiques, experiment plans, graph context, and exportable proposal dossiers.

## Current Workflow

```text
paper upload
  -> evidence extraction
  -> structured paper card
  -> research gap mining
  -> structured idea generation
  -> novelty/collision screening
  -> reviewer simulation
  -> experiment planning
  -> Markdown research dossier
  -> GraphRAG-lite context retrieval
```

The main product entrypoint is:

```http
POST /research/workflows/literature-to-ideas
```

It runs the full synchronous workflow and writes a job trace that can be fetched from:

```http
GET /research/jobs/{job_id}
GET /research/jobs/{job_id}/artifacts
GET /research/jobs
```

For long-running clients, use the async workflow entrypoint:

```http
POST /research/workflows/literature-to-ideas/async
```

It returns a `pending` job immediately and executes the workflow in the background.

## Implemented Capabilities

- FastAPI API layer with OpenAPI docs.
- SQLite/SQLAlchemy research database.
- Research profile for durable domains, goals, constraints, risk tolerance, target venues, and ranking weights.
- Upload and ingest `.txt`, `.md`, and `.pdf` papers.
- Section, chunk, and evidence extraction.
- Heuristic paper card extraction.
- OpenAI-compatible structured paper card extraction with safe heuristic fallback.
- Research gap mining from evidence records.
- OpenAI-compatible structured idea generation with deterministic fallback.
- Novelty/collision checks against existing evidence, gaps, ideas, and literature search results.
- Persisted related-work matrices that compare an idea with local evidence, gaps, nearby ideas, and literature search rows.
- Persisted proposal drafts that bundle an idea, related-work positioning, experiment plan, risks, milestones, and evidence IDs.
- Proposal readiness reviews with advisor-style scores, concerns, required revisions, and missing evidence.
- Proposal revision artifacts that turn readiness-review actions into a revised proposal checkpoint.
- Research task backlog generation from proposal revisions, with task listing, status updates, and workbench task-board controls.
- Research task event logs for created/updated/progress/blocker notes and execution history.
- Experiment run tracking that links an experiment plan to task events, metrics, conclusions, artifacts, and Markdown run reports.
- Experiment result analysis that turns run metrics into a decision, concerns, next actions, task events, and Markdown analysis reports.
- Follow-up task generation from experiment analysis next actions.
- Persisted task board snapshots for progress summaries, blocker tracking, and next-action exports.
- GraphRAG-lite links for proposal drafts, reviews, revisions, experiment runs, experiment analyses, decision memos, assumption audits, evidence ledgers, claim/evidence support edges, generated follow-up tasks, evidence-ledger follow-up tasks, decision follow-up tasks, project cockpit tasks, and task board snapshots.
- Idea lineage endpoint that hydrates matrices, proposal artifacts, experiment runs, experiment analyses, decision memos, assumption audits, evidence ledgers, tasks, task snapshots, and graph edge summaries.
- Idea activity timeline that turns proposal, experiment, decision, audit, evidence ledger, plan, and task events into a chronological handoff log.
- Traceable idea refinement from reviewer feedback, novelty risk, and experiment plans.
- Idea progress summaries that aggregate proposal, experiment, analysis, evidence-ledger follow-up, task, blocker, and recommended-next-step state.
- Idea research packets that bundle the latest artifacts, open tasks, graph edge summary, and Markdown context for a single idea.
- Idea readiness scoring that combines evidence, novelty, proposal review, experiment evidence, decision memo, assumptions, task health, and claim validation result impact.
- Idea quality gate that combines novelty, readiness, proposal review, experiment evidence, decision memo, task health, and claim validation result impact into a go/no-go decision.
- Task generation from idea quality-gate actions so go/no-go decisions become concrete de-risking work.
- Task generation from idea readiness blockers so readiness gaps become trackable follow-up work.
- Configurable novelty refresh for rerunning local and optional external literature collision checks on an idea.
- Task generation from novelty check recommended actions so collision-screening concerns become follow-up work.
- Project readiness overview for comparing recent ideas by readiness decision and blockers.
- Project quality gate overview for deciding which ideas to advance, de-risk, revise, park, or reject.
- Task generation from project quality-gate candidates for portfolio-level triage.
- Zip bundle export for a single idea's dossier, lineage, progress, packet, readiness, artifact Markdown, and JSON metadata.
- Idea decision memos that record pursue/revise/park/reject rationale, risks, evidence, next commitments, and graph links.
- Follow-up task generation from idea decision memo commitments.
- Idea assumption audits that expose falsifiable assumptions, validation signals, risk levels, and source artifacts.
- Idea evidence ledgers that map claims to supporting evidence, counterevidence, missing evidence, risks, coverage scores, Markdown exports, claim/evidence graph links, follow-up task generation, per-claim validation packets, project-level claim validation queues, queue-driven validation task generation, validation result reporting, and validation-result impact signals for readiness and quality gates.
- Project progress overview that aggregates all ideas, open tasks, blockers, recent analyses, and recommended actions.
- Project cockpit dashboard that compresses setup state, workflow stages, metrics, readiness, quality gates, opportunity radar, risks, highlights, quick actions, and Markdown export into one customer-facing entry point.
- Task generation from project cockpit primary action, next actions, risks, and highlights so the customer-facing entry point can drive the task board directly.
- Advisor chat endpoint that answers project-level questions from cockpit state, retrieved evidence, gaps, ideas, and GraphRAG-lite context, with Markdown output, citations, recommended actions, and tool suggestions.
- Project triage brief that combines progress, readiness, quality gates, and opportunity radar into one daily decision view.
- Task generation from project triage brief next actions and risks for daily execution.
- Persisted project triage snapshots that freeze daily decision state, source task ids, and Markdown exports for later review.
- Project triage snapshot comparison for tracking focus, risk, next-action, and metric changes across decision rounds.
- Task generation from triage snapshot comparison changes so newly added risks and actions enter the task board.
- Research opportunity radar that fuses portfolio ranking, readiness, blockers, and open tasks into a prioritized next-action view.
- Task generation from opportunity radar next actions so project-level prioritization enters the task board.
- Project handoff bundle export that packages triage brief, saved triage snapshots, latest triage comparison, project overviews, readiness, quality gates, opportunity radar, claim validation queue, task board state, briefs, and research plans.
- Persisted advisor research briefs for group-meeting or supervisor-ready Markdown summaries, including profile, tasks, experiment decisions, plan progress, readiness signals, evidence ledger signals, claim validation queue/task/result signals, triage signals, and latest triage snapshot comparison.
- Persisted research execution plans that turn profile, ranked ideas, and open tasks into 7/14+ day action plans.
- Task generation from research execution plans so plan actions enter the task board, idea progress, lineage, research packets, and bundle exports.
- Research plan progress reports that summarize generated plan tasks, completion ratio, blockers, phases, and next plan actions.
- MCP/tool-ready manifest for stable research workflow APIs.
- MCP-ready HTTP tool bridge spec generated from the stable tool manifest.
- Lightweight stdio MCP-to-HTTP bridge script for exposing the stable HTTP tools to MCP clients without extra SDK dependencies.
- MCP bridge policy controls for read-only mode, allow/deny tool filters, and deployment health checks.
- Research idea portfolio ranking with profile-aware weighting, lineage deduplication, claim validation result adjustments, and weighted score breakdowns.
- Human feedback capture for idea shortlist/accept/revise/reject decisions and ranking adjustments.
- Markdown export for ranked idea portfolio reports.
- Persisted idea portfolio snapshots for saved shortlist/ranking review states.
- Portfolio snapshot comparison for tracking shortlist/ranking changes over time.
- 30/60/90-day execution agenda export for saved idea portfolios.
- Local literature search with optional OpenAlex, arXiv, and Semantic Scholar external-search adapters.
- Reviewer simulation for generated ideas.
- Experiment plan generation.
- Local hashed embedding index for evidence, gaps, and ideas.
- Markdown export for paper cards and idea dossiers.
- GraphRAG-lite node and edge persistence.
- Query-time lexical/vector context retrieval over evidence, gaps, ideas, and graph neighborhoods.
- Synchronous workflow job trace with input, output, status, progress, and errors.
- Async literature-to-ideas workflow launch for frontend and MCP clients.
- Job artifact snapshots that hydrate workflow outputs into full papers, cards, gaps, ideas, checks, reviews, plans, and dossier Markdown.
- Job cancellation and retry controls for failed or interrupted workflow runs.
- Browser workbench for profile editing, upload, workflow launch, job tracking/cancel/retry, search, advisor chat, cockpit, readiness, quality gates, decision, audit, bundle export, and dossier preview.
- End-to-end smoke test covering the current research workflow.

## Repository Layout

```text
backend/
  app.py
  research/
    adapters/      OpenAI-compatible JSON client
    config.py
    db.py
    models.py      SQLAlchemy domain models
    routes.py      FastAPI routes
    schemas.py     Pydantic API schemas
    services/      Research workflow services
docs/
scripts/
  smoke_api.py
tests/
```

## Quick Start

This project is developed with `uv`.

```bash
uv sync --extra dev
uv run uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

API docs:

```text
http://127.0.0.1:8000/docs
```

Research workbench:

```text
http://127.0.0.1:8000/workbench
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Model Configuration

The system works without model credentials by falling back to deterministic local services. To enable model-backed structured extraction and idea generation, set OpenAI-compatible environment variables:

```env
MAIN_MODEL=
MAIN_BASE_URL=
MAIN_API_KEY=

EXTRACTION_MODEL=
EXTRACTION_BASE_URL=
EXTRACTION_API_KEY=

EXTERNAL_LITERATURE_SEARCH_ENABLED=false
OPENALEX_BASE_URL=https://api.openalex.org
```

If `EXTRACTION_*` is empty, paper card extraction falls back to the heuristic extractor. If `MAIN_*` is empty, idea generation falls back to the deterministic idea generator.

## Verification

Run unit tests:

```bash
uv run pytest -q
```

Run the full in-process API smoke workflow:

```bash
uv run python scripts/smoke_api.py
```

Run the same smoke workflow against a live server:

```bash
uv run python scripts/smoke_api.py --base-url http://127.0.0.1:8000
```

The smoke workflow uploads a paper, validates the research profile, tool manifest, MCP-ready bridge spec, and task execution controls, runs the literature-to-ideas workflow, fetches the workflow job trace, builds a related-work matrix, proposal draft, readiness review, proposal revision, task backlog, experiment run, experiment analysis, analysis follow-up tasks, decision memo, decision follow-up tasks, assumption audit, evidence ledger, evidence-ledger follow-up tasks, claim validation packet, claim validation queue, claim queue follow-up tasks, claim validation result tracking/reporting/decision signals, idea progress summary, idea research packet, idea timeline, readiness score, quality gate, quality-gate follow-up tasks, readiness follow-up tasks, idea bundle export, project readiness overview, project quality gate overview, project cockpit dashboard, project advisor chat, project cockpit tasks, project triage brief, project triage tasks, persisted project triage snapshots, triage snapshot comparison, triage comparison tasks, project quality-gate tasks, project overview, project bundle export with claim validation queue metadata, advisor brief, research execution plan, plan tasks, plan progress, plan-aware advisor brief, plan-aware progress/packet/bundle checks, and task board snapshot, performs context search, and checks graph endpoints.
It also validates the job artifact snapshot endpoint used by the workbench and future MCP tools.

## Useful Endpoints

```http
POST /research/papers/upload
GET  /research/papers
GET  /research/papers/{paper_id}
GET  /research/papers/{paper_id}/evidence
POST /research/literature/search
POST /research/embeddings/rebuild
GET  /research/tools/manifest
GET  /research/tools/mcp-spec
GET  /research/profile
PUT  /research/profile
GET  /research/profile/export/markdown
GET  /research/progress/overview
GET  /research/cockpit
GET  /research/cockpit/export/markdown
POST /research/cockpit/tasks
POST /research/advisor/chat
GET  /research/triage/brief
GET  /research/triage/brief/export/markdown
POST /research/triage/brief/tasks
POST /research/triage/snapshots
GET  /research/triage/snapshots
POST /research/triage/snapshots/compare
POST /research/triage/snapshots/compare/export/markdown
POST /research/triage/snapshots/compare/tasks
GET  /research/triage/snapshots/{snapshot_id}
GET  /research/triage/snapshots/{snapshot_id}/export/markdown
GET  /research/opportunities/radar
POST /research/opportunities/radar/tasks
GET  /research/export/project-bundle
POST /research/briefs
GET  /research/briefs
GET  /research/briefs/{brief_id}
GET  /research/briefs/{brief_id}/export/markdown
POST /research/plans
GET  /research/plans
GET  /research/plans/{plan_id}
GET  /research/plans/{plan_id}/export/markdown
POST /research/plans/{plan_id}/tasks
GET  /research/plans/{plan_id}/progress

POST /research/papers/{paper_id}/card/extract-structured
GET  /research/papers/{paper_id}/card/export/markdown

POST /research/gaps/mine
POST /research/gaps/{gap_id}/ideas
POST /research/ideas/{idea_id}/novelty-check
POST /research/ideas/{idea_id}/novelty-refresh
POST /research/ideas/{idea_id}/novelty-checks/{check_id}/tasks
POST /research/ideas/{idea_id}/review
POST /research/ideas/{idea_id}/experiment-plan
GET  /research/ideas/{idea_id}/experiment-runs
POST /research/experiment-plans/{plan_id}/runs
GET  /research/experiment-plans/{plan_id}/runs
GET  /research/experiment-runs/{run_id}
PATCH /research/experiment-runs/{run_id}
GET  /research/experiment-runs/{run_id}/export/markdown
POST /research/experiment-runs/{run_id}/analysis
GET  /research/experiment-runs/{run_id}/analyses
GET  /research/ideas/{idea_id}/experiment-analyses
GET  /research/experiment-analyses/{analysis_id}
GET  /research/experiment-analyses/{analysis_id}/export/markdown
POST /research/experiment-analyses/{analysis_id}/tasks
POST /research/ideas/{idea_id}/refine
GET  /research/ideas/{idea_id}/progress
GET  /research/ideas/{idea_id}/research-packet
GET  /research/ideas/{idea_id}/timeline
GET  /research/ideas/{idea_id}/readiness
GET  /research/ideas/{idea_id}/quality-gate
POST /research/ideas/{idea_id}/quality-gate/tasks
POST /research/ideas/{idea_id}/readiness/tasks
GET  /research/ideas/{idea_id}/export/bundle
GET  /research/readiness/overview
GET  /research/quality/overview
POST /research/quality/overview/tasks
POST /research/ideas/{idea_id}/decision-memo
GET  /research/ideas/{idea_id}/decision-memos
GET  /research/ideas/{idea_id}/decision-memos/{memo_id}
GET  /research/ideas/{idea_id}/decision-memos/{memo_id}/export/markdown
POST /research/ideas/{idea_id}/decision-memos/{memo_id}/tasks
POST /research/ideas/{idea_id}/assumption-audit
GET  /research/ideas/{idea_id}/assumption-audits
GET  /research/ideas/{idea_id}/assumption-audits/{audit_id}
GET  /research/ideas/{idea_id}/assumption-audits/{audit_id}/export/markdown
POST /research/ideas/{idea_id}/evidence-ledger
GET  /research/ideas/{idea_id}/evidence-ledgers
GET  /research/ideas/{idea_id}/evidence-ledgers/{ledger_id}
GET  /research/ideas/{idea_id}/evidence-ledgers/{ledger_id}/export/markdown
POST /research/ideas/{idea_id}/evidence-ledgers/{ledger_id}/tasks
GET  /research/ideas/{idea_id}/evidence-ledgers/{ledger_id}/claims/{claim_id}/validation-packet
GET  /research/claims/validation-queue
POST /research/claims/validation-queue/tasks
POST /research/tasks/{task_id}/claim-validation-result
POST /research/ideas/{idea_id}/related-work-matrix
GET  /research/ideas/{idea_id}/related-work-matrices
GET  /research/ideas/{idea_id}/related-work-matrices/{matrix_id}
GET  /research/ideas/{idea_id}/related-work-matrices/{matrix_id}/export/markdown
POST /research/ideas/{idea_id}/proposal-draft
GET  /research/ideas/{idea_id}/proposal-drafts
GET  /research/ideas/{idea_id}/proposal-drafts/{draft_id}
GET  /research/ideas/{idea_id}/proposal-drafts/{draft_id}/export/markdown
POST /research/ideas/{idea_id}/proposal-drafts/{draft_id}/review
GET  /research/ideas/{idea_id}/proposal-drafts/{draft_id}/reviews
GET  /research/ideas/{idea_id}/proposal-drafts/{draft_id}/reviews/{review_id}
GET  /research/ideas/{idea_id}/proposal-drafts/{draft_id}/reviews/{review_id}/export/markdown
GET  /research/ideas/{idea_id}/lineage
POST /research/ideas/{idea_id}/proposal-drafts/{draft_id}/revise
GET  /research/ideas/{idea_id}/proposal-drafts/{draft_id}/revisions
GET  /research/ideas/{idea_id}/proposal-drafts/{draft_id}/revisions/{revision_id}
GET  /research/ideas/{idea_id}/proposal-drafts/{draft_id}/revisions/{revision_id}/export/markdown
POST /research/ideas/{idea_id}/proposal-drafts/{draft_id}/revisions/{revision_id}/tasks
GET  /research/tasks
GET  /research/tasks/{task_id}
PATCH /research/tasks/{task_id}
POST /research/tasks/{task_id}/events
GET  /research/tasks/{task_id}/events
POST /research/tasks/snapshots
GET  /research/tasks/snapshots
GET  /research/tasks/snapshots/{snapshot_id}
GET  /research/tasks/snapshots/{snapshot_id}/export/markdown
POST /research/ideas/rank
POST /research/ideas/rank/export/markdown
POST /research/ideas/portfolios
GET  /research/ideas/portfolios
POST /research/ideas/portfolios/compare
POST /research/ideas/portfolios/compare/export/markdown
GET  /research/ideas/portfolios/{portfolio_id}
GET  /research/ideas/portfolios/{portfolio_id}/export/markdown
GET  /research/ideas/portfolios/{portfolio_id}/agenda/markdown
POST /research/ideas/{idea_id}/feedback
GET  /research/ideas/{idea_id}/feedback
GET  /research/ideas/{idea_id}/export/markdown

POST /research/search/context
GET  /research/graph/nodes
GET  /research/graph/edges
POST /research/workflows/literature-to-ideas
POST /research/workflows/literature-to-ideas/async
GET  /research/jobs/{job_id}
POST /research/jobs/{job_id}/cancel
POST /research/jobs/{job_id}/retry
GET  /research/jobs/{job_id}/artifacts
GET  /workbench
```

## MCP Bridge

Run the backend first, then start the stdio bridge for MCP-capable clients:

```bash
uv run python scripts/mcp_http_bridge.py --base-url http://127.0.0.1:8000
```

The bridge loads `/research/tools/mcp-spec`, exposes `tools/list` and `tools/call`, and forwards tool calls to the FastAPI routes.
For safer client onboarding, narrow the exposed tools before connecting a client:

```bash
uv run python scripts/mcp_http_bridge.py --base-url http://127.0.0.1:8000 --read-only
uv run python scripts/mcp_http_bridge.py --base-url http://127.0.0.1:8000 --allow-tool get_project_progress --allow-tool get_idea_progress
uv run python scripts/mcp_http_bridge.py --base-url http://127.0.0.1:8000 --health-check
```

The same policy can be configured with `MCP_BRIDGE_READ_ONLY`, `MCP_BRIDGE_ALLOW_TOOLS`, and `MCP_BRIDGE_DENY_TOOLS`.

## Near-Term Roadmap

- Add external embedding providers and learned reranking.
- Add external novelty search through OpenAlex/Semantic Scholar/arXiv adapters.
- Add durable worker queues, richer retry policies, and resumable workflow state.
- Expand the research workbench into a full review/edit loop.
- Add auth, deployment packaging, and richer binary artifact handling around the lightweight MCP bridge.
- Introduce LangGraph/DeerFlow-style explicit workflow graphs once the service boundaries stabilize.

## Design Documents

- `docs/research_assistant_requirements.md`
- `docs/research_assistant_technical_design.md`
