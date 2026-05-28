# Research Assistant Agent

Research Assistant Agent is the next-generation rewrite of SuperMew: a research workflow system that uses literature evidence to help users understand papers, mine research gaps, generate ideas, critique them like reviewers, and turn promising ideas into experiment plans.

## Product Direction

The project is not just a stronger RAG chatbot. The target workflow is:

```text
papers -> structured evidence -> research gaps -> ideas -> reviews -> experiment plans
```

The first implementation phase focuses on the backend foundation:

- FastAPI API layer.
- SQLAlchemy research database.
- Pydantic schemas.
- Paper, evidence, gap, idea, review, and experiment-plan data models.
- LangGraph-ready module boundaries.
- GraphRAG-lite node and edge tables.

## Repository Layout

```text
backend/
  app.py
  research/
    config.py
    db.py
    models.py
    routes.py
    schemas.py
    services/
    graphs/
    prompts/
    adapters/
    evaluators/
docs/
tests/
```

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

API docs:

```text
http://127.0.0.1:8000/docs
```

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

## Current Status

Phase 0 is being implemented: project foundation, database models, API skeleton, and technical documentation.

See:

- `docs/research_assistant_requirements.md`
- `docs/research_assistant_technical_design.md`
