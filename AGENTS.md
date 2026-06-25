# AGENTS.md

This repository is the local deployable clone of Research Assistant Agent.

It was cloned from GitHub for Mac-side local development and verification when the
remote server is unavailable or when the operator explicitly requests local work.

## Source Of Truth

- Historical authoritative remote path: `/home/zhangwz/Research-Assistant-Agent`.
- GitHub repository: `ImpZhang/Research-Assistant-Agent.git`.
- Upstream source-of-truth remains GitHub/latest remote state when reachable.
- This local clone is runnable and currently tracks GitHub `main`.
- Prefer GitHub/latest remote state for upstream truth when the remote server is reachable.
- When the operator asks for local development, use this repository and keep all artifacts project-local.

## Default Work Location

- For local development, run inspection and tests in this repository first.
- Use `scripts/env.sh` before local work so caches, data, logs, models, and outputs stay inside this project.
- Do not install dependencies globally.
- Do not start services in the background unless the operator explicitly asks for a persistent local service.
- Do not start or restart remote services unless the operator explicitly approves that action.
- Prefer small, reviewable changes with focused tests and progress-log updates.

## Before Modifying Code

Always inspect local state first:

```bash
git status --short
git branch --show-current
git --no-pager log --oneline -5
```

If the remote server is reachable and the task is intended to be pushed upstream, also inspect the remote state before editing:

```bash
ssh -i ~/.ssh/id_ed25519_geoloc -p 8502 -o BatchMode=yes zhangwz@39.97.171.237 \
  'cd /home/zhangwz/Research-Assistant-Agent && git status --short && git branch --show-current && git --no-pager log --oneline -5'
```

If unexpected tracked changes or new untracked files are present, stop and ask the operator before editing, staging, or committing. Historical remote-only untracked root documents may exist:

- `research_assistant_requirements.md`
- `research_assistant_technical_design.md`

Do not stage or modify those two files unless the operator explicitly asks.

## Secrets And Sensitive Files

Never read, print, copy, summarize, commit, or paste real secret values from:

- `.env` or `.env.*` except safe templates such as `.env.example`
- `*.key`, `*.pem`, private keys, certificates, or SSH keys
- token, cookie, credential, secret, session, or auth-cache files
- production database dumps or private customer papers unless the operator explicitly confirms the data is safe for the task

It is acceptable to report that a sensitive file exists. It is not acceptable to display its contents.

## Prohibited Commands Without Explicit Approval

Do not run destructive, deployment, or dependency-changing commands unless the operator explicitly approves the exact action:

- `rm`, broad `mv`, or overwrite `cp`
- `git reset`, `git clean`, destructive `git checkout`, or force push
- `pip install`, `uv sync`, `npm install`, `pnpm install`, or `yarn install`
- `docker compose up`, deployment commands, service restarts, or worker restarts
- `systemctl restart`, `kill`, or `pkill`
- `chmod -R`, `chown -R`
- database migrations, cleanup jobs, or data rewrite scripts

## Safe Default Commands

Read-only inspection is usually safe:

```bash
pwd
hostname
uname -a
git status --short
git --no-pager log --oneline -5
find . -maxdepth 2 -type f -print
sed -n '1,160p' README.md
python3 --version
.venv/bin/python --version
.venv/bin/ruff check tests/test_app.py
```

Do not point read commands at sensitive files.

## Development Process

- Start with `docs/documentation_index.md` to locate the relevant design, operation, and evaluation documents.
- Follow `docs/development_process.md` for the standard change lifecycle.
- Keep `docs/progress_log.md` updated for nontrivial work.
- Keep local isolation behavior aligned with `docs/local_isolation.md`.

## Verification And Commits

- Use `source scripts/env.sh` and project-local `.venv/bin/...` tools.
- Prefer focused tests for the changed behavior before broader suites.
- Update `docs/progress_log.md` for durable handoff when work is nontrivial.
- Stage only files that belong to the current task.
- Keep GitHub updated with small commits after successful verification.
