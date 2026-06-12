# Research Assistant Agent Deployment

This project can run as a local FastAPI app or as a single-container service for an internal customer pilot.

## Runtime Contract

- Health: `GET /health`
- Readiness: `GET /health/ready`
- Protected API prefix: `/research`
- Default auth mode: disabled for local development, enabled in `docker-compose.yml`
- API key headers: `X-Research-Assistant-Key: <key>` or `Authorization: Bearer <key>`

## Environment

Copy `.env.example` to `.env` and set at least:

```bash
APP_ENV=production
API_KEY_AUTH_ENABLED=true
API_KEY=replace-with-a-long-random-secret
RESEARCH_DB_URL=sqlite:////app/data/research/research_assistant.db
PAPER_UPLOAD_DIR=/app/data/papers
PAPER_UPLOAD_ALLOWED_EXTENSIONS=.txt,.md,.pdf
PAPER_UPLOAD_MAX_BYTES=10485760
```

Paper uploads validate extension, size, and lightweight content signatures before writing files to `PAPER_UPLOAD_DIR`. Text and Markdown uploads must be UTF-8 text without null bytes; PDF uploads must start with a PDF header.

Optional write-operation audit trail:

```bash
WRITE_AUDIT_ENABLED=true
WRITE_AUDIT_DIR=/app/data/audit
WRITE_AUDIT_CLIENT_HEADER_NAME=X-Research-Assistant-Client
REQUEST_ID_HEADER_NAME=X-Request-ID

# Optional operator-only audit summary gate, disabled by default.
AUDIT_ADMIN_EXPORT_ENABLED=false
AUDIT_ADMIN_KEY=
AUDIT_ADMIN_KEY_HEADER_NAME=X-Research-Assistant-Admin-Key
```

`GET /health/ready` checks the audit directory when `WRITE_AUDIT_ENABLED=true`, so pilot deployments fail readiness if JSONL audit persistence cannot be prepared. Audit records are JSONL metadata only. They may include a short SHA-256 API-key fingerprint prefix for correlation, but must not contain raw request bodies, uploaded paper content, API keys, cookies, private keys, `.env` values, or provider credentials. Operator-only audit summary/export features must follow `docs/admin_authorization_policy.md`; audit retention and raw-export workflow are defined in `docs/write_audit_retention_policy.md`. The regular pilot API key is not admin authorization by itself. When `AUDIT_ADMIN_EXPORT_ENABLED=true`, the read-only summary endpoint is available at `GET /research/admin/write-audit/summary`, and bounded raw JSONL export is available at `GET /research/admin/write-audit/export`; both require the separate admin key header.

Model provider variables can stay empty for deterministic fallback behavior, or be filled with OpenAI-compatible endpoints:

```bash
MAIN_MODEL=
MAIN_BASE_URL=
MAIN_API_KEY=
EXTRACTION_MODEL=
EXTRACTION_BASE_URL=
EXTRACTION_API_KEY=
JUDGE_MODEL=
JUDGE_BASE_URL=
JUDGE_API_KEY=
```

## Pilot Deployment Checklist

Before starting or upgrading a customer-pilot service:

- [ ] Confirm the remote source-of-truth worktree is clean except for known handoff-only files: `git status --short`.
- [ ] Confirm the branch and commit intended for deployment: `git branch --show-current` and `git log --oneline -5`.
- [ ] Create or update `.env` from `.env.example` outside version control; never commit real API keys, cookies, private keys, or database credentials.
- [ ] Set `API_KEY_AUTH_ENABLED=true` and use a long random `API_KEY` for browser, MCP, and scripted access.
- [ ] Confirm `RESEARCH_DB_URL` and `PAPER_UPLOAD_DIR` point at persistent storage, not an ephemeral build directory.
- [ ] Back up `/app/data` or the equivalent data volume before rebuilds, migrations, or host moves.
- [ ] If SQLAlchemy models changed, review `docs/database_migration_strategy.md` and confirm no implicit startup migration is being relied on.
- [ ] Start or rebuild the service only during an approved deployment window.
- [ ] Verify `GET /health`, `GET /health/ready`, and authenticated `GET /research/status` before sharing `/workbench`; if write audit is enabled, confirm the readiness payload includes an enabled, writable `write_audit_dir` check.
- [ ] Open `/workbench`, save the API key in the top bar, refresh Pilot Launch, and confirm the first-run empty/error states are actionable.
- [ ] If MCP clients are used, run the bridge health check with the same API key and the intended read-only or allow/deny policy.
- [ ] If audit summary/export features are enabled in a future release, confirm the separate admin authorization gate described in `docs/admin_authorization_policy.md`.
- [ ] Record the deployed commit, verification commands, and rollback note in the project progress log or release notes.

Commands that rebuild containers, restart services, change file ownership, or modify databases should be run only after explicit operator approval.

## Docker Compose

```bash
docker compose up --build
```

The compose file mounts a named volume at `/app/data`, so SQLite data, uploaded papers, and generated artifacts survive container restarts.

## Backup And Restore Notes

The production compose file declares a `research_assistant_data` volume mounted at `/app/data`. Docker Compose usually creates an engine volume named `<compose-project>_research_assistant_data`, so confirm the actual volume name before backing up or restoring.

Back up this data before rebuilds, host moves, database migrations, or destructive maintenance. A backup should include:

- `/app/data/research/research_assistant.db` and related SQLite sidecar files if present.
- `/app/data/papers` uploaded paper files.
- Generated bundle, brief, and workflow artifacts under `/app/data`.

Keep `.env`, API keys, cookies, private keys, and provider credentials in a separate secret manager or operator vault. Do not put them in git or public handoff bundles.

Cold backup is the preferred first-pilot path because SQLite and uploaded files can be copied consistently while the service is stopped. Example operator flow, only after explicit approval:

```bash
mkdir -p backups
docker compose stop research-assistant-agent
docker run --rm \
  -v research-assistant-agent_research_assistant_data:/data:ro \
  -v "$PWD/backups:/backup" \
  alpine sh -lc 'tar -C /data -czf /backup/research-assistant-data-YYYYMMDD-HHMMSS.tgz .'
docker compose start research-assistant-agent
```

If the Compose project name differs from the example, confirm the actual volume name first with `docker volume ls` and do not guess.

Restore should never write over a live service volume. Prefer restoring into a new empty target volume, then switching Compose to that volume only after operator review. Example operator flow, only after explicit approval:

```bash
docker compose stop research-assistant-agent
# Optional but recommended: back up the current volume before restore.
docker volume create research_assistant_data_restore
docker run --rm \
  -v research_assistant_data_restore:/data \
  -v "$PWD/backups:/backup:ro" \
  alpine sh -lc 'tar -C /data -xzf /backup/research-assistant-data-YYYYMMDD-HHMMSS.tgz'
# Review the restored volume, then update the compose volume mapping or perform an approved volume swap.
docker compose start research-assistant-agent
curl http://127.0.0.1:8000/health/ready
```

After restore or volume swap, verify `/health/ready`, authenticated `/research/status`, Workbench Pilot Launch, and a known project bundle or paper record before sharing the service again.

Check the service:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/health/ready
curl -H "X-Research-Assistant-Key: $API_KEY" http://127.0.0.1:8000/research/status
```

## MCP Bridge With API Key

When `API_KEY_AUTH_ENABLED=true`, forward the same key through the lightweight MCP bridge:

```bash
python scripts/mcp_http_bridge.py \
  --base-url http://127.0.0.1:8000 \
  --api-key "$API_KEY"
```

For a restricted client:

```bash
python scripts/mcp_http_bridge.py \
  --base-url http://127.0.0.1:8000 \
  --api-key "$API_KEY" \
  --read-only
```

The bridge also accepts `MCP_BRIDGE_API_KEY`, `RESEARCH_ASSISTANT_API_KEY`, or `API_KEY` from the environment.

## Workbench With API Key

The browser workbench is served at `/workbench`. When API protection is enabled, paste the same key into the top-bar API key field and choose `Save Key`. The key is stored in browser local storage and sent only to `/research/*` requests as `X-Research-Assistant-Key`.

Choose `Clear` to remove the key from the browser.

## Pilot Notes

- Put a reverse proxy in front of `/workbench` for browser users.
- Keep `/health` and `/health/ready` available to the load balancer.
- Use `EXTERNAL_LITERATURE_SEARCH_ENABLED=false` unless outbound network and provider limits are intentionally configured.
- Back up the `/app/data` volume before upgrades.
