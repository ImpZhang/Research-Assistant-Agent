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
- Traceable idea refinement from reviewer feedback, novelty risk, and experiment plans.
- Research idea portfolio ranking with lineage deduplication and weighted score breakdowns.
- Human feedback capture for idea shortlist/accept/revise/reject decisions and ranking adjustments.
- Markdown export for ranked idea portfolio reports.
- Persisted idea portfolio snapshots for saved shortlist/ranking review states.
- Portfolio snapshot comparison for tracking shortlist/ranking changes over time.
- 30/60/90-day execution agenda export for saved idea portfolios.
- Local literature search with an optional OpenAlex external-search adapter.
- Reviewer simulation for generated ideas.
- Experiment plan generation.
- Local hashed embedding index for evidence, gaps, and ideas.
- Markdown export for paper cards and idea dossiers.
- GraphRAG-lite node and edge persistence.
- Query-time lexical/vector context retrieval over evidence, gaps, ideas, and graph neighborhoods.
- Synchronous workflow job trace with input, output, status, progress, and errors.
- Async literature-to-ideas workflow launch for frontend and MCP clients.
- Job artifact snapshots that hydrate workflow outputs into full papers, cards, gaps, ideas, checks, reviews, plans, and dossier Markdown.
- Browser workbench for upload, workflow launch, job tracking, search, and dossier preview.
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

The smoke workflow uploads a paper, runs the literature-to-ideas workflow, fetches the workflow job trace, builds a related-work matrix, proposal draft, and readiness review, performs context search, and checks graph endpoints.
It also validates the job artifact snapshot endpoint used by the workbench and future MCP tools.

## Useful Endpoints

```http
POST /research/papers/upload
GET  /research/papers
GET  /research/papers/{paper_id}
GET  /research/papers/{paper_id}/evidence
POST /research/literature/search
POST /research/embeddings/rebuild

POST /research/papers/{paper_id}/card/extract-structured
GET  /research/papers/{paper_id}/card/export/markdown

POST /research/gaps/mine
POST /research/gaps/{gap_id}/ideas
POST /research/ideas/{idea_id}/novelty-check
POST /research/ideas/{idea_id}/review
POST /research/ideas/{idea_id}/experiment-plan
POST /research/ideas/{idea_id}/refine
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
GET  /research/jobs/{job_id}/artifacts
GET  /workbench
```

## Near-Term Roadmap

- Add external embedding providers and learned reranking.
- Add external novelty search through OpenAlex/Semantic Scholar/arXiv adapters.
- Add richer job cancellation and retry controls.
- Expand the research workbench into a full review/edit loop.
- Add MCP tools for paper ingestion, workflow runs, and dossier export.
- Introduce LangGraph/DeerFlow-style explicit workflow graphs once the service boundaries stabilize.

## Design Documents

- `docs/research_assistant_requirements.md`
- `docs/research_assistant_technical_design.md`
