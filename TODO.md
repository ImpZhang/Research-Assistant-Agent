# TODO

This top-level TODO is a stable index for the current remote-first handoff. The detailed historical queue lives in `codex_handoff/03_TODO.md`; the chronological work log lives in `docs/progress_log.md`.

## P0 - Remote-First Safety

- Treat `/home/zhangwz/Research-Assistant-Agent` on the remote server as source of truth.
- Check `git status --short`, branch, and recent commits before every edit round.
- Preserve the two historical untracked root documents unless the operator explicitly asks to handle them.
- Do not read or commit secrets, `.env` values, credentials, cookies, private keys, or production/private data.

## P1 - Pilot Readiness Without Service Changes

- Run `bash scripts/check_pilot_readiness.sh` before changing pilot readiness, API-key guard, upload guardrail, or workbench first-run behavior.
- Keep adding narrow, deterministic tests for user-facing research workflows.
- Keep README, `codex_handoff/03_TODO.md`, and `docs/progress_log.md` synchronized with completed slices.
- Prefer docs/tests/API guardrails that do not require dependency installs, migrations, service restarts, or deployment changes.

## P2 - Operator-Approved Hardening

- Backup/restore scripts only after deployment host and volume naming are confirmed.
- Write-audit rotation or cleanup only after backup and retention policy are confirmed.
- Database migration tooling only after dependency sync and migration approach are approved.
- User/project scoping only after migration tooling and auth identity are explicit.
- Queue/worker readiness only after deployment topology and backend choice are confirmed.

## P3 - Current GraphRAG And Context Search Direction

- Run `bash scripts/check_context_search_evaluations.sh` before changing context-search scoring or graph-expansion behavior.
- Continue deterministic context-search evaluation before changing scoring weights.
- Keep GraphRAG-lite and service-layer workflows as the default until scale, durability, or tool-sandbox triggers are explicit.
- Treat LangGraph as a future isolated workflow option, not the default runtime.
- Treat DeerFlow as a future external planner/tool consumer through the stable tool manifest and MCP bridge.

## P4 - Needs Explicit Operator Approval

- Remote smoke workflow against a running service.
- Dependency installation or synchronization.
- Docker compose startup or service restarts.
- Database migrations or data cleanup.
- Production data inspection, exports, or backups.
