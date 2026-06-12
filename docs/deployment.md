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
```

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
- [ ] Start or rebuild the service only during an approved deployment window.
- [ ] Verify `GET /health`, `GET /health/ready`, and authenticated `GET /research/status` before sharing `/workbench`.
- [ ] Open `/workbench`, save the API key in the top bar, refresh Pilot Launch, and confirm the first-run empty/error states are actionable.
- [ ] If MCP clients are used, run the bridge health check with the same API key and the intended read-only or allow/deny policy.
- [ ] Record the deployed commit, verification commands, and rollback note in the project progress log or release notes.

Commands that rebuild containers, restart services, change file ownership, or modify databases should be run only after explicit operator approval.

## Docker Compose

```bash
docker compose up --build
```

The compose file mounts a named volume at `/app/data`, so SQLite data, uploaded papers, and generated artifacts survive container restarts.

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
