# Local Isolation Runbook

This checkout is the Mac-local deployable copy of `ImpZhang/Research-Assistant-Agent`.

## Project Root

`/Users/zwz/Documents/super-mew改进科研助手/Research-Assistant-Agent-local`

## Local Artifacts

- Python environment: `.venv/`
- Tool caches: `.cache/`
- SQLite database and uploaded papers: `data/`
- Benchmark ground-truth datasets: `data/benchmarks/`
- Model weights or manually downloaded local models: `models/`
- Generated exports and experiment outputs: `outputs/`
- Benchmark prediction files: `outputs/predictions/`
- Benchmark command-runner stdout/stderr/metrics artifacts: `outputs/benchmark-runs/`
- Runtime logs: `logs/`
- Docker project metadata: `.docker/`

Real secrets belong only in untracked `.env` files. Commit only `.env.example` or other placeholder examples. Machine-specific benchmark profile overrides belong in the ignored `configs/benchmark_profiles.json`; commit only `configs/benchmark_profiles.example.json`.

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

Before changing optional Docker packaging, run the static contract check. It reads committed templates and docs only; it does not start Docker or read `.env` values:

```bash
python3 scripts/check_single_user_docker_deployment.py
```

## Cleanup

Before backing up or moving local data, build an aggregate manifest:

```bash
python3 scripts/build_local_backup_manifest.py
```

The manifest is read-only. It reports backup-set counts and sizes without listing private paper filenames or including `.env` secrets.

Run the synthetic local backup/restore rehearsal before changing backup or restore behavior:

```bash
python3 scripts/rehearse_local_backup_restore.py
python3 scripts/rehearse_local_backup_restore.py --markdown --write-markdown outputs/restore-rehearsals/rehearsal.md
```

The rehearsal uses temporary synthetic data under project-local scratch space, archives the configured backup sets, restores into a temporary project root, compares aggregate manifests, and confirms secret-like files are not copied. It does not copy live local papers, live SQLite data, `.env` files, API keys, cookies, or provider credentials.

Before SQLite troubleshooting or approved maintenance, build a read-only maintenance report:

```bash
python3 scripts/check_sqlite_maintenance.py
python3 scripts/check_sqlite_maintenance.py --markdown --write-markdown outputs/maintenance/sqlite-report.md
```

The report inspects only aggregate database metadata: storage size, sidecars, table counts, vector-index counts, trace counts, and `PRAGMA quick_check`. It does not read `.env`, API keys, provider credentials, private paper content, or run cleanup actions. By default, it refuses to inspect a database outside the project root.

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
