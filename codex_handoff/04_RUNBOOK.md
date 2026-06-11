# Runbook

This runbook is for a new Mac Codex session.

## Path Mapping

### Windows Path Used During Previous Work

```text
D:\super-mew改进科研助手\Research-Assistant-Agent
```

### Remote Linux Path

```text
/home/zhangwz/Research-Assistant-Agent
```

### Suggested Mac Path

```text
~/Projects/Research-Assistant-Agent
```

If a command in old notes uses the Windows path, replace it with the Mac path.

## Clone On Mac

```bash
mkdir -p ~/Projects
cd ~/Projects
git clone https://github.com/ImpZhang/Research-Assistant-Agent.git
cd Research-Assistant-Agent
```

Check state:

```bash
git status --short
git log --oneline -5
```

## Python And uv

The project requires Python 3.12+.

Install `uv` on Mac if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then install dependencies:

```bash
uv sync --extra dev
```

## Environment File

Create a local `.env` from `.env.example`:

```bash
cp .env.example .env
```

Do not commit `.env`.

Important variables:

```env
APP_NAME=Research Assistant Agent
APP_ENV=development
HOST=0.0.0.0
PORT=8000

RESEARCH_DB_URL=sqlite:///./data/research/research_assistant.db
PAPER_UPLOAD_DIR=./data/papers

MAIN_MODEL=
MAIN_BASE_URL=
MAIN_API_KEY=

EXTRACTION_MODEL=
EXTRACTION_BASE_URL=
EXTRACTION_API_KEY=

JUDGE_MODEL=
JUDGE_BASE_URL=
JUDGE_API_KEY=

EMBEDDER=
EMBEDDER_BASE_URL=
EMBEDDER_API_KEY=

RERANK_MODEL=
RERANK_BINDING_HOST=
RERANK_API_KEY=

GRAPH_RAG_LITE_ENABLED=true
MCP_ENABLED=false
EXTERNAL_LITERATURE_SEARCH_ENABLED=false
EXTERNAL_LITERATURE_PROVIDERS=openalex,arxiv,semantic_scholar
OPENALEX_BASE_URL=https://api.openalex.org
ARXIV_BASE_URL=https://export.arxiv.org/api/query
SEMANTIC_SCHOLAR_BASE_URL=https://api.semanticscholar.org/graph/v1/paper/search

API_KEY_AUTH_ENABLED=false
API_KEY=
API_KEY_HEADER_NAME=X-Research-Assistant-Key
```

Secrets:

- Do not write real API keys in Markdown.
- Do not commit `.env`.
- If API protection is enabled, provide the key through the local `.env` or deployment secret manager.

## Start Development Server

```bash
uv run uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

URLs:

- API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`
- Ready check: `http://127.0.0.1:8000/health/ready`
- Workbench: `http://127.0.0.1:8000/workbench`

## Test Commands

Run all tests:

```bash
uv run pytest -q
```

Run smoke workflow in-process:

```bash
uv run python scripts/smoke_api.py
```

Run smoke workflow against a live server:

```bash
uv run python scripts/smoke_api.py --base-url http://127.0.0.1:8000
```

Run lint:

```bash
uv run ruff check .
```

Run format check:

```bash
uv run ruff format --check .
```

Apply formatting:

```bash
uv run ruff format .
```

## Common Development Flow

```bash
git pull --ff-only
uv sync --extra dev
uv run ruff check .
uv run pytest -q
```

After a scoped implementation:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run python scripts/smoke_api.py
git status --short
git add <changed-files>
git commit -m "<concise message>"
git push origin main
```

## Docker Compose Pilot

Create `.env` with a real API key locally, then:

```bash
docker compose up --build
```

Service:

- `http://127.0.0.1:8000`
- data volume: `research_assistant_data`
- container DB path: `/app/data/research/research_assistant.db`
- container upload path: `/app/data/papers`

Do not commit production `.env`.

## MCP Bridge

Start backend first.

Inspect MCP-ready spec:

```bash
curl http://127.0.0.1:8000/research/tools/mcp-spec
```

Run bridge health check:

```bash
uv run python scripts/mcp_http_bridge.py --base-url http://127.0.0.1:8000 --health-check
```

Run read-only bridge:

```bash
uv run python scripts/mcp_http_bridge.py --base-url http://127.0.0.1:8000 --read-only
```

If API key protection is enabled, pass a key via a local environment variable or CLI flag. Do not write the actual key in this document.

## Useful API Endpoints

Core:

```http
GET  /health
GET  /health/ready
GET  /research/status
GET  /research/tools/manifest
GET  /research/tools/mcp-spec
```

Papers and workflow:

```http
POST /research/papers/upload
GET  /research/papers
POST /research/workflows/literature-to-ideas
POST /research/workflows/literature-to-ideas/async
GET  /research/jobs
GET  /research/jobs/{job_id}
GET  /research/jobs/{job_id}/artifacts
```

Project:

```http
GET  /research/profile
PUT  /research/profile
GET  /research/onboarding/readiness
POST /research/onboarding/setup
POST /research/onboarding/tasks
GET  /research/cockpit
GET  /research/cockpit/export/markdown
POST /research/advisor/chat
GET  /research/triage
```

Project bundle/release:

```http
GET  /research/export/project-bundle
GET  /research/export/project-bundle/readiness
POST /research/export/project-bundle/readiness/tasks
POST /research/export/project-bundle/releases
GET  /research/export/project-bundle/releases/{release_id}/progress
POST /research/export/project-bundle/releases/{release_id}/feedback
GET  /research/export/project-bundle/releases/{release_id}/closeout
GET  /research/export/project-bundle/releases/{release_id}/acceptance-packet
POST /research/export/project-bundle/releases/{release_id}/acceptance-packet/snapshots
GET  /research/export/project-bundle/releases/{release_id}/review-session
POST /research/export/project-bundle/releases/{release_id}/review-session/tasks
POST /research/export/project-bundle/releases/{release_id}/review-session/outcomes
POST /research/export/project-bundle/releases/{release_id}/review-session/outcomes/{outcome_id}/tasks
GET  /research/export/project-bundle/releases/{release_id}/review-session/outcomes/{outcome_id}/progress
```

## Remote Linux Notes

The prior workflow often validated and pushed from the remote Linux directory:

```text
/home/zhangwz/Research-Assistant-Agent
```

If Mac Codex needs to compare with remote:

- Use SSH credentials from the user's secure source.
- Do not write passwords in docs or commits.
- Prefer GitHub as the portable source of truth.

## Files To Avoid Committing

Do not commit:

- `.env`
- `data/`
- uploaded papers
- generated SQLite DB files
- virtual environments
- local logs
- secrets, tokens, cookies, private keys

