# Demo Runbook

This runbook explains how to evaluate the product as a research assistant workflow without touching the default remote development database.

## Safety Defaults

- Run from the remote source-of-truth project: `/home/zhangwz/Research-Assistant-Agent`.
- Check `git status --short` before editing or committing.
- Do not read or print `.env`, tokens, cookies, private keys, passwords, or credentials.
- The default product-effect smoke uses isolated data under `data/test-runs/` and disables external literature search.
- The smoke paper is synthetic; use it for workflow health, not scientific-quality claims.

## Isolated In-Process Product Smoke

Use this when you want a complete backend workflow evaluation without starting a service:

```bash
bash scripts/check_product_effect_smoke.sh
```

To run the same product smoke with a representative local paper fixture:

```bash
PRODUCT_EFFECT_SMOKE_PAPER_FILE=/path/to/paper.md bash scripts/check_product_effect_smoke.sh
```

Expected high-level indicators:

- `/health` returns `ok`.
- `/health/ready` returns `ready`.
- Workbench HTML is available.
- Tool manifest and MCP bridge expose the same tool count.
- The literature workflow creates gaps, ideas, novelty checks, reviews, and experiment plans.
- Proposal review reaches `ready_for_advisor_review` on the deterministic smoke paper.
- Experiment analysis returns `supports_hypothesis`.
- Project bundle readiness reaches `delivery_ready` after required artifacts are created.
- The final JSON includes graph node and edge counts.

## Temporary Real HTTP Smoke

Use this when you want to prove the same workflow works through a real FastAPI server. Bind only to localhost and use an isolated data directory.

```bash
RUN_ID=$(date +%s%N)
SMOKE_DATA_DIR="./data/test-runs/product-http-smoke-${RUN_ID}"
mkdir -p "${SMOKE_DATA_DIR}/papers" "${SMOKE_DATA_DIR}/research"
RESEARCH_DB_URL="sqlite:///${SMOKE_DATA_DIR}/research/research_assistant.db" \
PAPER_UPLOAD_DIR="${SMOKE_DATA_DIR}/papers" \
EXTERNAL_LITERATURE_SEARCH_ENABLED=false \
timeout 90 .venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 18081
```

In another shell while the server is running:

```bash
PRODUCT_EFFECT_SMOKE_BASE_URL=http://127.0.0.1:18081 bash scripts/check_product_effect_smoke.sh
```

Let `timeout` close the temporary server. Confirm no server remains:

```bash
pgrep -af 'uvicorn|smoke_api|pytest|check_remote' || true
```

## Interpreting The Current Baseline

The 2026-06-15 product-effect smoke baseline produced these representative metrics:

- Tool manifest: `119` tools.
- MCP bridge: `119` tools.
- Literature workflow: `3` gaps and `6` ideas.
- Proposal review: `ready_for_advisor_review`, score `0.92`.
- Readiness: score `0.6534`, decision `needs_targeted_work` before final delivery packaging.
- Quality gate: score `0.6574`, decision `de_risk_novelty`.
- Project bundle: `71` files, readiness `delivery_ready`, score `1.0`.
- Graph summary: `100` nodes and `100` edges in the smoke output.

## Demo Decision

Use this runbook to prove the backend workflow is demo-ready. Before a user-facing demo, still inspect the Workbench visually and run a real or representative paper through the workflow for qualitative review.
