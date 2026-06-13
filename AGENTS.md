# AGENTS.md

This repository is the source-of-truth project for Research Assistant Agent on the remote server.

## Source Of Truth

- Authoritative remote path: `/home/zhangwz/Research-Assistant-Agent`.
- GitHub repository: `ImpZhang/Research-Assistant-Agent.git`.
- Mac-side folders are handoff/context workspaces only unless the operator explicitly asks for a local experiment.
- Do not assume a Mac-side copy is complete, current, or runnable.

## Default Work Location

- Run inspection, tests, commits, and pushes from the remote repository first.
- Do not install dependencies or start services on the Mac workspace by default.
- Do not start or restart remote services unless the operator explicitly approves that action.
- Prefer small, reviewable changes with focused tests and progress-log updates.

## Before Modifying Remote Code

Always inspect the remote state first:

```bash
cd /home/zhangwz/Research-Assistant-Agent
git status --short
git branch --show-current
git --no-pager log --oneline -5
```

If unexpected tracked changes or new untracked files are present, stop and ask the operator before editing, staging, or committing. Two historical untracked root documents may exist:

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

## Verification And Commits

- Use `.venv/bin/...` tools already present on the remote host.
- Prefer focused tests for the changed behavior before broader suites.
- Update `docs/progress_log.md` for durable handoff when work is nontrivial.
- Stage only files that belong to the current task.
- Keep GitHub updated with small commits after successful verification.
