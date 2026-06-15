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

The current product behaves as a backend-first research workflow engine. It can produce a complete research handoff package from a smoke paper in both in-process and real HTTP service modes.

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

## What Works Well

- The full backend research workflow is coherent and traceable from paper ingestion to delivery bundle.
- Proposal, experiment, evidence-ledger, claim-validation, readiness, quality-gate, advisor, and bundle-release stages all produce structured artifacts.
- The system is not only a chatbot: it creates persistent research objects, task backlogs, graph links, Markdown exports, and delivery packages.
- The tool manifest and MCP bridge are broad enough for an external tool consumer to drive the workflow.
- Isolated test data now makes the long delivery-loop validation repeatable and fast.
- The real HTTP smoke confirms the app works through an actual temporary FastAPI server, not only through TestClient.

## Product Gaps

- The smoke paper is synthetic. A real paper or real project brief still needs qualitative evaluation.
- The generated readiness and quality scores show useful caution, but the actual scientific quality of gaps, ideas, novelty claims, and experiment plans still needs human review.
- Workbench availability is verified, but visual/interaction quality has not been systematically inspected in a browser session.
- Deployment posture is still pilot-oriented: backup, restore, migrations, monitoring, and production data boundaries remain hardening work.
- Multi-user/project scoping is designed but not production-enforced as a complete product boundary.
- External literature search is disabled for deterministic verification; live external search quality and failure modes still need a separate approved evaluation.

## Current Product Readiness Estimate

- Backend research workflow MVP: `75%` to `80%`.
- Demonstrable single-user pilot: `65%` to `70%`.
- Real user trial with guided operator support: `55%` to `60%`.
- Long-running production product: `45%` to `50%`.

## Recommended Next Steps

1. Run a browser-level Workbench inspection against a temporary isolated HTTP service and capture the main user path: upload, workflow launch, cockpit, advisor, bundle.
2. Add a small scripted product-quality evaluation using a real or representative paper fixture, with saved metrics for gap quality, idea quality, proposal completeness, and plan executability.
3. Decide whether the next demo target is API-first, Workbench-first, or MCP/tool-consumer-first.
4. Add a concise `docs/demo_runbook.md` that explains how to run the isolated product smoke and interpret the metrics.
5. Continue hardening docs and tests before touching production deployment, migrations, backups, or user-scoping enforcement.
