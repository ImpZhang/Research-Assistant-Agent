# Product Effect Report

This report records the current product-level evaluation of Research Assistant Agent. It focuses on whether the system behaves like a research assistant workflow product, not only whether unit tests pass.

## Product Target

The intended product is a research assistant agent that turns literature and project context into an executable research workflow:

1. ingest a paper or research direction,
2. extract evidence and paper-card structure,
3. mine research gaps,
4. generate and rank research ideas,
5. screen novelty and related work,
6. draft and review proposals,
7. create experiment plans and task backlogs,
8. track evidence, assumptions, claim validation, and experiment outcomes,
9. summarize readiness, quality gates, cockpit state, advisor actions, and handoff bundles.

## Current Evaluation Summary

Status on 2026-06-15: backend workflow engine and verification harness are strong enough for MVP demonstration, while product polish still needs frontend, real-user workflow, deployment, and operator-hardening passes.

The current product behaves as a backend-first research workflow engine. It can produce a complete research handoff package from a smoke paper in both in-process and real HTTP service modes. The latest isolated smoke adds a product-effect scorecard: overall `0.9289`, band `demo_ready`, with strong foundation/research/delivery dimensions and a quality-signal dimension above the backend demo threshold.

## Verified Smoke Metrics

The smoke runs used isolated test data directories under `data/test-runs/` and disabled external literature search so no remote development database or external API state was required.

### In-Process Smoke

- Service health: `ok`.
- Service readiness: `ready`.
- Workbench available: `true`.
- Tool manifest count: `119`.
- MCP bridge tool count: `119`.
- Literature workflow output: `3` gaps, `6` ideas, `6` novelty checks, `6` reviews, `6` experiment plans.
- Proposal review: `ready_for_advisor_review`, score `0.92`.
- Experiment analysis: `supports_hypothesis`.
- Readiness score: `0.6534`, decision `needs_targeted_work`.
- Quality gate score: `0.6574`, decision `de_risk_novelty`.
- Advisor chat: intent `risk_review`, `10` recommended actions, `13` citations, `5` tool suggestions.
- Project bundle: `71` files, readiness level `delivery_ready`, score `1.0`, missing required count `0`.
- Research plan: `3` plan items, `9` generated tasks.
- Portfolio ranking: `5` ranked ideas, top score `3.585`.
- Graph context: `100` nodes, `100` edges in the final smoke summary.
- Product-effect scorecard: overall `0.9289`, band `demo_ready`, foundation `1.0`, research workflow `1.0`, quality signal `0.7157`, delivery loop `1.0`, failed checks `[]`.

### Real HTTP Smoke

The same smoke path was run against a temporary `uvicorn` service bound to `127.0.0.1:18081` with isolated SQLite and upload directories.

- Service health: `ok`.
- Service readiness: `ready`.
- Workbench available: `true`.
- Tool manifest count: `119`.
- MCP bridge tool count: `119`.
- Literature workflow output: `3` gaps, `6` ideas.
- Proposal review: `ready_for_advisor_review`, score `0.92`.
- Experiment analysis: `supports_hypothesis`.
- Readiness score: `0.6534`, decision `needs_targeted_work`.
- Quality gate score: `0.6574`, decision `de_risk_novelty`.
- Advisor chat: intent `risk_review`, `10` recommended actions, `13` citations.
- Project bundle: `71` files, readiness level `delivery_ready`, score `1.0`, missing required count `0`.
- Release closeout and acceptance status: `blocked`, as expected for a simulated handoff with requested changes and deferred signoff.
- Research plan items: `3`.
- Ranked ideas: `5`, top score `3.585`.
- Graph context: `100` nodes, `100` edges.


### Representative Markdown Smoke

The product-effect smoke was also run with a representative Markdown fixture through `PRODUCT_EFFECT_SMOKE_PAPER_FILE=/tmp/raa_gap_rich_paper.md`.

- Literature workflow output: `3` gaps, `6` ideas.
- Proposal review: `ready_for_advisor_review`, score `0.92`.
- Evidence ledger coverage: `0.49`.
- Project bundle: `71` files, readiness level `delivery_ready`, score `1.0`.
- Graph context: `100` nodes, `100` edges.
- Product-effect scorecard: overall `0.931`, band `demo_ready`, foundation `1.0`, research workflow `1.0`, quality signal `0.724`, delivery loop `1.0`, failed checks `[]`.

## What Works Well

- The full backend research workflow is coherent and traceable from paper ingestion to delivery bundle.
- Proposal, experiment, evidence-ledger, claim-validation, readiness, quality-gate, advisor, and bundle-release stages all produce structured artifacts.
- The system is not only a chatbot: it creates persistent research objects, task backlogs, graph links, Markdown exports, and delivery packages.
- The tool manifest and MCP bridge are broad enough for an external tool consumer to drive the workflow.
- Isolated test data now makes the long delivery-loop validation repeatable and fast.
- The real HTTP smoke confirms the app works through an actual temporary FastAPI server, not only through TestClient.

## Product Gaps

- The smoke paper is synthetic. A real paper or real project brief still needs qualitative evaluation.
- The generated readiness and quality scores show useful caution; the scorecard makes this visible through a quality-signal dimension of `0.7157`, driven by broader source-paper evidence context and mixed claim-validation outcomes.
- The actual scientific quality of gaps, ideas, novelty claims, and experiment plans still needs human review.
- Workbench availability is verified, and a static demo-path contract now protects the pilot flow from paper ingest through delivery closeout; true browser visual/interaction quality still needs a human/browser inspection pass.
- Deployment posture is still pilot-oriented: backup, restore, migrations, monitoring, and production data boundaries remain hardening work.
- Multi-user/project scoping is designed but not production-enforced as a complete product boundary.
- External literature search is disabled for deterministic verification; live external search quality and failure modes still need a separate approved evaluation.

## Current Product Readiness Estimate

- Backend research workflow MVP: `85%` to `90%`.
- Demonstrable single-user pilot: `75%` to `80%`.
- Real user trial with guided operator support: `60%` to `65%`.
- Long-running production product: `45%` to `50%`.

## Recommended Next Steps

1. Run a browser-level or human-observed Workbench inspection against a temporary isolated HTTP service and capture the main user path: upload, workflow launch, cockpit, advisor, bundle.
2. Keep the Workbench demo-path contract synchronized whenever sections or controls move, then improve the quality-signal dimension by strengthening evidence-ledger coverage and claim-validation scoring on representative papers.
3. Decide whether the next demo target is API-first, Workbench-first, or MCP/tool-consumer-first.
4. Continue hardening docs and tests before touching production deployment, migrations, backups, or user-scoping enforcement.
