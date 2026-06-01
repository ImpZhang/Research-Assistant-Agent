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
- Research task backlog generation from proposal revisions, with task listing and status updates.
- Research task event logs for created/updated/progress/blocker notes and execution history.
- Experiment run tracking that links an experiment plan to task events, metrics, conclusions, artifacts, and Markdown run reports.
- Experiment result analysis that turns run metrics into a decision, concerns, next actions, task events, and Markdown analysis reports.
- Follow-up task generation from experiment analysis next actions.
- Persisted task board snapshots for progress summaries, blocker tracking, and next-action exports.
- GraphRAG-lite links for proposal drafts, reviews, revisions, experiment runs, experiment analyses, decision memos, assumption audits, generated follow-up tasks, decision follow-up tasks, and task board snapshots.
- Idea lineage endpoint that hydrates matrices, proposal artifacts, experiment runs, experiment analyses, decision memos, assumption audits, tasks, task snapshots, and graph edge summaries.
- Traceable idea refinement from reviewer feedback, novelty risk, and experiment plans.
- Idea progress summaries that aggregate proposal, experiment, analysis, task, blocker, and recommended-next-step state.
- Idea research packets that bundle the latest artifacts, open tasks, graph edge summary, and Markdown context for a single idea.
- Idea readiness scoring that explains whether an idea is ready for deeper execution.
- Task generation from idea readiness blockers so readiness gaps become trackable follow-up work.
- Project readiness overview for comparing recent ideas by readiness decision and blockers.
- Zip bundle export for a single idea's dossier, lineage, progress, packet, readiness, artifact Markdown, and JSON metadata.
- Idea decision memos that record pursue/revise/park/reject rationale, risks, evidence, next commitments, and graph links.
- Follow-up task generation from idea decision memo commitments.
- Idea assumption audits that expose falsifiable assumptions, validation signals, risk levels, and source artifacts.
- Project progress overview that aggregates all ideas, open tasks, blockers, recent analyses, and recommended actions.
- Persisted advisor research briefs for group-meeting or supervisor-ready Markdown summaries.
- Persisted research execution plans that turn profile, ranked ideas, and open tasks into 7/14+ day action plans.
- Task generation from research execution plans so plan actions enter the task board, idea progress, lineage, research packets, and bundle exports.
- MCP/tool-ready manifest for stable research workflow APIs.
- MCP-ready HTTP tool bridge spec generated from the stable tool manifest.
- Research idea portfolio ranking with profile-aware weighting, lineage deduplication, and weighted score breakdowns.
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
- Browser workbench for profile editing, upload, workflow launch, job tracking/cancel/retry, search, readiness, decision, audit, bundle export, and dossier preview.
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

The smoke workflow uploads a paper, validates the research profile, tool manifest, and MCP-ready bridge spec, runs the literature-to-ideas workflow, fetches the workflow job trace, builds a related-work matrix, proposal draft, readiness review, proposal revision, task backlog, experiment run, experiment analysis, analysis follow-up tasks, decision memo, decision follow-up tasks, assumption audit, idea progress summary, idea research packet, readiness score, readiness follow-up tasks, idea bundle export, project readiness overview, project overview, advisor brief, research execution plan, plan tasks, plan-aware progress/packet/bundle checks, and task board snapshot, performs context search, and checks graph endpoints.
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
POST /research/briefs
GET  /research/briefs
GET  /research/briefs/{brief_id}
GET  /research/briefs/{brief_id}/export/markdown
POST /research/plans
GET  /research/plans
GET  /research/plans/{plan_id}
GET  /research/plans/{plan_id}/export/markdown
POST /research/plans/{plan_id}/tasks

POST /research/papers/{paper_id}/card/extract-structured
GET  /research/papers/{paper_id}/card/export/markdown

POST /research/gaps/mine
POST /research/gaps/{gap_id}/ideas
POST /research/ideas/{idea_id}/novelty-check
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
GET  /research/ideas/{idea_id}/readiness
POST /research/ideas/{idea_id}/readiness/tasks
GET  /research/ideas/{idea_id}/export/bundle
GET  /research/readiness/overview
POST /research/ideas/{idea_id}/decision-memo
GET  /research/ideas/{idea_id}/decision-memos
GET  /research/ideas/{idea_id}/decision-memos/{memo_id}
GET  /research/ideas/{idea_id}/decision-memos/{memo_id}/export/markdown
POST /research/ideas/{idea_id}/decision-memos/{memo_id}/tasks
POST /research/ideas/{idea_id}/assumption-audit
GET  /research/ideas/{idea_id}/assumption-audits
GET  /research/ideas/{idea_id}/assumption-audits/{audit_id}
GET  /research/ideas/{idea_id}/assumption-audits/{audit_id}/export/markdown
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

## Near-Term Roadmap

- Add external embedding providers and learned reranking.
- Add external novelty search through OpenAlex/Semantic Scholar/arXiv adapters.
- Add durable worker queues, richer retry policies, and resumable workflow state.
- Expand the research workbench into a full review/edit loop.
- Wrap the HTTP tool bridge spec in a lightweight MCP server for paper ingestion, workflow runs, and bundle export.
- Introduce LangGraph/DeerFlow-style explicit workflow graphs once the service boundaries stabilize.

## Design Documents

- `docs/research_assistant_requirements.md`
- `docs/research_assistant_technical_design.md`
