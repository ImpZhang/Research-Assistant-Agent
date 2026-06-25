# Local Isolation Runbook

This checkout is the Mac-local deployable copy of `ImpZhang/Research-Assistant-Agent`.

## Project Root

`/Users/zwz/Documents/super-mew改进科研助手/Research-Assistant-Agent-local`

## Local Artifacts

- Python environment: `.venv/`
- Tool caches: `.cache/`
- SQLite database and uploaded papers: `data/`
- Model weights or manually downloaded local models: `models/`
- Generated exports and experiment outputs: `outputs/`
- Benchmark command-runner stdout/stderr/metrics artifacts: `outputs/benchmark-runs/`
- Runtime logs: `logs/`
- Docker project metadata: `.docker/`

Real secrets belong only in untracked `.env` files. Commit only `.env.example` or other placeholder examples.

## Setup

Use Python 3.12 or newer.
The setup script prefers the repository `uv.lock` for reproducible local dependencies.

```bash
cd /Users/zwz/Documents/super-mew改进科研助手/Research-Assistant-Agent-local
PYTHON_BIN=/path/to/python3.12 ./scripts/setup-local.sh
source scripts/env.sh
```

In this Codex desktop environment, a compatible Python is available at:

```bash
PYTHON_BIN=/Users/zwz/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 ./scripts/setup-local.sh
```

## Run Locally

```bash
source scripts/env.sh
uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Or use the wrapper:

```bash
./scripts/run-local.sh
```

Open `http://127.0.0.1:8000/workbench`.

## Docker

The compose project is scoped as `research-assistant-agent-local`; when using `scripts/env.sh`, `COMPOSE_PROJECT_NAME` is set to `research_assistant_agent_local`.

```bash
source scripts/env.sh
docker compose up --build
```

For production-like compose runs, create an untracked `.env` with a long `API_KEY`.

## Cleanup

```bash
./scripts/clean.sh
```

Removes rebuildable dependencies, caches, logs, and generated outputs. It keeps `data/` and `models/`.

```bash
./scripts/deep-clean.sh
```

Asks for confirmation, then removes uploaded papers, SQLite data, datasets, model weights, and outputs.

```bash
./scripts/docker-clean.sh
```

Asks for confirmation, then removes project containers and volumes with `docker compose down -v --remove-orphans`.
