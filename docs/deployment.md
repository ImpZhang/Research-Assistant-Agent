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

## Pilot Notes

- Put a reverse proxy in front of `/workbench` for browser users.
- Keep `/health` and `/health/ready` available to the load balancer.
- Use `EXTERNAL_LITERATURE_SEARCH_ENABLED=false` unless outbound network and provider limits are intentionally configured.
- Back up the `/app/data` volume before upgrades.
