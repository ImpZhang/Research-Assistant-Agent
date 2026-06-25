# Research Assistant Agent

Research Assistant Agent is a backend-first research workflow system rebuilt from the lessons of SuperMew. It is not a plain RAG chatbot: the goal is to turn literature evidence into research gaps, testable ideas, novelty checks, related-work matrices, proposal drafts, reviewer critiques, experiment plans, graph context, and exportable proposal dossiers.

## Current Distribution Target

The current product target is a personal, local-deployable research agent. Each user clones `ImpZhang/Research-Assistant-Agent.git`, creates an untracked local `.env`, configures their own model provider API keys, and runs the backend, Workbench, optional MCP bridge, data, caches, models, benchmarks, logs, and outputs inside the local project root.

Multi-user accounts, tenant isolation, hosted SaaS operations, billing, SSO, and central admin workflows are intentionally out of scope for the current build. Historical `pilot`, `customer`, and `project scope` wording in API names and older docs should be read as single-operator local workflow and handoff terminology unless a future product decision changes the target.

See `docs/local_agent_distribution.md` and `docs/local_isolation.md` before changing packaging, setup, storage, or deployment behavior.

## Current Workflow

```text
paper upload
  -> evidence extraction
  -> structured paper card
  -> research gap mining
  -> structured idea generation
  -> novelty/collision screening
  -> reviewer simulation
  -> experiment planning
  -> benchmark run packet / experiment run tracking
  -> manual SOTA signoff record
  -> Markdown research dossier
  -> GraphRAG-lite context retrieval
```

The main product entrypoint is:

```http
POST /research/workflows/literature-to-ideas
```

It runs the full synchronous workflow and writes a job trace that can be fetched from:

```http
GET /research/jobs/{job_id}
GET /research/jobs/{job_id}/artifacts
GET /research/jobs
```

For long-running clients, use the async workflow entrypoint:

```http
POST /research/workflows/literature-to-ideas/async
```

It returns a `pending` job immediately and executes the workflow in the background.

## Implemented Capabilities

- FastAPI API layer with OpenAPI docs.
- Local runtime-readiness checks with `/health/ready`, SQLite storage readiness, optional API-key auth readiness, Workbench asset readiness, model-provider configuration visibility, request-id response headers and header readiness, external-literature configuration checks, default-project scope contract, runtime readiness status capability, health build metadata, optional API-key protection for `/research/*`, Dockerfile, and docker-compose single-user deployment.
- SQLite/SQLAlchemy research database.
- Research profile for durable domains, goals, constraints, risk tolerance, target venues, and ranking weights.
- Upload and ingest size-limited `.txt`, `.md`, and `.pdf` papers with lightweight content sniffing before files are written.
- Section, chunk, and evidence extraction.
- Heuristic paper card extraction.
- OpenAI-compatible structured paper card extraction with safe heuristic fallback.
- Research gap mining from evidence records.
- OpenAI-compatible structured idea generation with deterministic fallback.
- Novelty/collision checks against existing evidence, gaps, ideas, and literature search results.
- Persisted related-work matrices that compare an idea with local evidence, gaps, nearby ideas, and literature search rows.
- Manual SOTA review packages that combine novelty screening, related-work rows, missing searches, review queries, and Markdown checklists before claiming novelty.
- SOTA external-search evidence packages that persist review queries, local/external provider statuses, result summaries, missing searches, and signoff readiness.
- Manual SOTA signoff records that capture reviewer decision, linked external-search evidence package, effective external-search completion, nearest work, evidence links, linked benchmark runs, final novelty claim, limitations, and remaining blockers.
- Persisted proposal drafts that bundle an idea, related-work positioning, experiment plan, risks, milestones, and evidence IDs.
- Proposal readiness reviews with advisor-style scores, concerns, required revisions, and missing evidence.
- Proposal revision artifacts that turn readiness-review actions into a revised proposal checkpoint.
- Research task backlog generation from proposal revisions, with task listing, status updates, and workbench task-board controls.
- Research task event logs for created/updated/progress/blocker notes and execution history.
- Experiment run tracking that links an experiment plan to task events, metrics, conclusions, artifacts, and Markdown run reports.
- Benchmark run packets that structure dataset, split, nearest baseline, primary metric, metric direction, command, dry-run flag, artifacts, and reproducibility notes as first-class experiment runs.
- Guarded local benchmark command runner that is disabled by default, executes command-argument lists without a shell when enabled, captures stdout/stderr/metrics under `outputs/benchmark-runs/`, and saves the result as an experiment run.
- Benchmark profile registry and a project-local geolocalization JSONL harness so Workbench/API clients can discover runnable benchmark profiles, see missing data/prediction paths, execute profile-backed commands, and parse country-accuracy/geodesic-distance metrics.
- Benchmark run comparison records that compute metric deltas between two experiment runs and persist the result as an auditable Markdown research brief.
- Benchmark evidence readiness gate and task generation that summarize completed runs, comparison briefs, missing evidence, warnings, and turn follow-up actions into task-board items before manual SOTA signoff.
- Experiment result analysis that turns run metrics into a decision, concerns, next actions, task events, and Markdown analysis reports.
- Follow-up task generation from experiment analysis next actions.
- Persisted task board snapshots for progress summaries, blocker tracking, and next-action exports.
- GraphRAG-lite links for proposal drafts, reviews, revisions, experiment runs, experiment analyses, decision memos, assumption audits, evidence ledgers, claim/evidence support edges, generated follow-up tasks, evidence-ledger follow-up tasks, decision follow-up tasks, project cockpit tasks, and task board snapshots.
- Idea lineage endpoint that hydrates matrices, proposal artifacts, experiment runs, experiment analyses, decision memos, assumption audits, evidence ledgers, tasks, task snapshots, and graph edge summaries.
- Idea activity timeline that turns proposal, experiment, decision, audit, evidence ledger, plan, and task events into a chronological handoff log.
- Traceable idea refinement from reviewer feedback, novelty risk, and experiment plans.
- Idea progress summaries that aggregate proposal, experiment, analysis, evidence-ledger follow-up, task, blocker, and recommended-next-step state.
- Idea research packets that bundle the latest artifacts, open tasks, graph edge summary, and Markdown context for a single idea.
- Idea readiness scoring that combines evidence, novelty, proposal review, experiment evidence, decision memo, assumptions, task health, and claim validation result impact.
- Idea quality gate that combines novelty, readiness, proposal review, experiment evidence, decision memo, task health, and claim validation result impact into a go/no-go decision.
- Task generation from idea quality-gate actions so go/no-go decisions become concrete de-risking work.
- Task generation from idea readiness blockers so readiness gaps become trackable follow-up work.
- Configurable novelty refresh for rerunning local and optional external literature collision checks on an idea.
- Task generation from novelty check recommended actions so collision-screening concerns become follow-up work.
- Project readiness overview for comparing recent ideas by readiness decision and blockers.
- Project quality gate overview for deciding which ideas to advance, de-risk, revise, park, or reject.
- Task generation from project quality-gate candidates for portfolio-level triage.
- Zip bundle export for a single idea's dossier, lineage, progress, packet, readiness, artifact Markdown, and JSON metadata.
- Idea decision memos that record pursue/revise/park/reject rationale, risks, evidence, next commitments, and graph links.
- Follow-up task generation from idea decision memo commitments.
- Idea assumption audits that expose falsifiable assumptions, validation signals, risk levels, and source artifacts.
- Idea evidence ledgers that map claims to supporting evidence, counterevidence, missing evidence, risks, coverage scores, Markdown exports, claim/evidence graph links, follow-up task generation, per-claim validation packets, project-level claim validation queues, queue-driven validation task generation, validation result reporting, and validation-result impact signals for readiness and quality gates.
- Project progress overview that aggregates all ideas, open tasks, blockers, recent analyses, and recommended actions.
- Project onboarding readiness checklist that turns profile, literature, workflow, task board, bundle, security, and MCP setup signals into a first-run pilot score, missing required checks, quick actions, and Markdown report.
- Project setup wizard that saves the first-run research profile, captures success criteria and the first milestone, then immediately returns refreshed onboarding readiness and a Markdown setup report.
- Task generation from project onboarding readiness gaps and optional pilot guardrails so first-run setup work enters the task board and GraphRAG-lite trace.
- Project onboarding progress tracking that reports setup-task completion, blockers, next action, current readiness, and Markdown status after onboarding tasks are generated.
- Customer-facing pilot status report that combines onboarding readiness/progress, cockpit phase, metrics, risks, next actions, quick actions, and Markdown for stakeholder updates.
- Persisted pilot report snapshots that save customer-facing status reports as `pilot_report` briefs with list, detail, and Markdown export endpoints.
- Pilot report snapshot comparison that shows status, metric, risk, next-action, and quick-action changes between two saved customer updates.
- Task generation from pilot report snapshot comparisons so new weekly risks and action changes become follow-up work.
- Task generation from pilot report snapshots so saved customer updates can drive follow-up work and GraphRAG-lite traceability.
- Project cockpit dashboard that compresses setup state, workflow stages, metrics, readiness, quality gates, opportunity radar, risks, highlights, quick actions, and Markdown export into one customer-facing entry point.
- Task generation from project cockpit primary action, next actions, risks, and highlights so the customer-facing entry point can drive the task board directly.
- Advisor chat endpoint that answers project-level questions from cockpit state, retrieved evidence, gaps, ideas, and GraphRAG-lite context, with Markdown output, citations, recommended actions, and tool suggestions.
- Task generation from advisor chat answers so recommendations, risks, and optional tool suggestions enter the task board and graph trace.
- Advisor action sessions that turn one advisor question into a grounded answer, follow-up tasks, a task-board snapshot, progress summary, and Markdown execution report.
- Project triage brief that combines progress, readiness, quality gates, and opportunity radar into one daily decision view.
- Task generation from project triage brief next actions and risks for daily execution.
- Persisted project triage snapshots that freeze daily decision state, source task ids, and Markdown exports for later review.
- Project triage snapshot comparison for tracking focus, risk, next-action, and metric changes across decision rounds.
- Task generation from triage snapshot comparison changes so newly added risks and actions enter the task board.
- Research opportunity radar that fuses portfolio ranking, readiness, blockers, and open tasks into a prioritized next-action view.
- Task generation from opportunity radar next actions so project-level prioritization enters the task board.
- Project handoff bundle export that packages triage brief, saved triage snapshots, latest triage comparison, pilot report snapshots, latest pilot report comparison, project overviews, readiness, quality gates, opportunity radar, claim validation queue, task board state, briefs, and research plans.
- Project bundle readiness checks that score whether the handoff package has enough snapshots, comparisons, claim validation, plans, quality gates, and opportunity context before customer/advisor delivery.
- Task generation from project bundle readiness gaps so missing handoff materials and final delivery checks become task-board work and GraphRAG-lite trace.
- Persisted project bundle readiness snapshots that save delivery preflight scores, missing checks, manifest summaries, and Markdown audits into the project bundle.
- Project bundle readiness snapshot comparison that tracks score, missing-check, action, quick-action, and manifest deltas across delivery rounds.
- Task generation from project bundle readiness snapshot comparisons so newly introduced handoff gaps and delivery actions become task-board work with graph traceability.
- Project bundle release notes that persist customer/advisor handoff metadata, recipient, readiness state, manifest signals, and Markdown delivery notes into the exported project bundle.
- Task generation from project bundle release notes so recipient confirmation, claim queue review, open task ownership, and release closeout enter the task board and graph trace.
- Project bundle release progress tracking that summarizes follow-up completion, blockers, next tasks, and latest release progress artifacts in the exported bundle.
- Project bundle release feedback records that capture customer/advisor acceptance status, signoff state, requested changes, blockers, accepted artifacts, follow-up tasks, and graph traceability.
- Project bundle release closeout reports that combine release progress, latest feedback, feedback-task progress, blockers, signoff state, and next actions into a delivery closeout decision.
- Task generation from project bundle release closeout reports so blockers, next actions, signoff gaps, and archive checks become traceable task-board work.
- Project bundle release acceptance packets that combine the release note, progress, feedback, closeout decision, closeout tasks, checklist, remaining actions, and Markdown signoff summary.
- Persisted project bundle release acceptance packet snapshots that freeze customer/advisor signoff state, acceptance status, remaining actions, and Markdown evidence into the exported project bundle.
- Project bundle release acceptance snapshot comparison that explains what changed between signoff attempts and can generate follow-up tasks for new remaining actions, checklist regressions, or status/signoff regressions.
- Project bundle release review sessions that turn the release, progress, feedback, closeout, acceptance packet, and acceptance snapshot comparison into a customer/advisor agenda, decisions, risks, follow-up actions, and review tasks.
- Persisted project bundle release review outcomes that record post-meeting decisions, participants, accepted artifacts, risks, follow-up actions, signoff state, task generation, graph traceability, and exported bundle artifacts.
- Project bundle release review outcome progress reports that summarize post-meeting follow-up completion, blockers, next tasks, and latest progress artifacts in the exported bundle.
- Persisted project bundle release review outcome signoff evidence records that capture approver decisions, notes, accepted artifacts, conditions, evidence links, graph traceability, and the current outcome progress snapshot in the exported bundle.
- Persisted advisor research briefs for group-meeting or supervisor-ready Markdown summaries, including profile, tasks, experiment decisions, plan progress, readiness signals, evidence ledger signals, claim validation queue/task/result signals, triage signals, and latest triage snapshot comparison.
- Persisted research execution plans that turn profile, ranked ideas, and open tasks into 7/14+ day action plans.
- Task generation from research execution plans so plan actions enter the task board, idea progress, lineage, research packets, and bundle exports.
- Research plan progress reports that summarize generated plan tasks, completion ratio, blockers, phases, and next plan actions.
- MCP/tool-ready manifest for stable research workflow APIs.
- MCP-ready HTTP tool bridge spec generated from the stable tool manifest.
- Lightweight stdio MCP-to-HTTP bridge script for exposing the stable HTTP tools to MCP clients without extra SDK dependencies.
- MCP bridge policy controls for read-only mode, allow/deny tool filters, API-key forwarding, project-scope header forwarding, request-id error correlation, and deployment health checks.
- Research idea portfolio ranking with profile-aware weighting, lineage deduplication, claim validation result adjustments, and weighted score breakdowns.
- Human feedback capture for idea shortlist/accept/revise/reject decisions and ranking adjustments.
- Markdown export for ranked idea portfolio reports.
- Persisted idea portfolio snapshots for saved shortlist/ranking review states.
- Portfolio snapshot comparison for tracking shortlist/ranking changes over time.
- 30/60/90-day execution agenda export for saved idea portfolios.
- Local literature search with optional OpenAlex, arXiv, and Semantic Scholar external-search adapters.
- Reviewer simulation for generated ideas.
- Experiment plan generation.
- Local hashed embedding index for evidence, gaps, and ideas, with optional external embedding provider vectors.
- Markdown export for paper cards and idea dossiers.
- Robust sparse-heading paper ingestion and gap-mining fallback for PDFs that expose Roman numeral headings, compact headings such as `RELATEDWORK`, or only a clean References heading.
- GraphRAG-lite node and edge persistence with same source/target/type edge reuse.
- Read-only GraphRAG-lite stats for node/edge type counts, orphan edge counts, and duplicate edge group counts.
- Query-time lexical/vector/rerank context retrieval over evidence, gaps, ideas, and optionally filtered graph neighborhoods, with stable ranking tie-breaks and score breakdowns.
- Synchronous workflow job trace with input, output, status, progress, and errors.
- Async literature-to-ideas workflow launch for frontend and MCP clients.
- Job artifact snapshots that hydrate workflow outputs into full papers, cards, gaps, ideas, checks, reviews, plans, and dossier Markdown.
- Job cancellation and retry controls for failed or interrupted workflow runs.
- Browser workbench for API-key-backed and project-scope-aware pilot access with scope-contract status, runtime readiness and request-id signals, first-run and delivery empty/API-key/network states, grouped idea/task/delivery/operations controls, pilot launch status, profile editing, upload, workflow launch, job tracking/cancel/retry, search, advisor chat/action sessions, cockpit, readiness, quality gates, decision, audit, bundle export, and dossier preview.
- Representative-paper human review protocol and persisted review records for Workbench-first pilot acceptance, with status capabilities `representative_paper_review_protocol` and `representative_paper_review_records`.
- End-to-end smoke test covering the current research workflow.
- Deterministic context-search evaluation fixtures for hit@k, MRR, graph edge hit/noise, score breakdown coverage/consistency, paper-filter leak checks, and empty-query guards.

## Repository Layout

```text
backend/
  app.py
  research/
    adapters/      OpenAI-compatible JSON client
    config.py
    db.py
    models.py      SQLAlchemy domain models
    routes.py      FastAPI routes
    schemas.py     Pydantic API schemas
    services/      Research workflow services
docs/
scripts/
  check_backup_restore_contracts.sh
  check_context_search_evaluations.sh
  check_deployment_contracts.sh
  check_focused_test_coverage.sh
  check_generated_file_guard.sh
  check_graph_rag_lite.sh
  check_handoff_docs.sh
  check_local_agent_readiness.sh
  check_pilot_operational_preflight.sh
  check_pilot_readiness.sh
  check_product_effect_smoke.sh
  check_project_delivery_loop.sh
  check_remote_long_suite.sh
  check_remote_safe_suite.sh
  check_research_planning_contracts.sh
  check_script_catalog.sh
  check_secret_file_guard.sh
  check_suite_contracts.sh
  check_research_proposal_contracts.sh
  check_research_workflow_primitives.sh
  check_tool_bridge_contracts.sh
  check_workflow_job_controls.sh
  check_write_audit_guardrails.sh
  smoke_api.py
tests/
```

## Development Documents

Start future development from:

- `AGENTS.md` for repository operating rules.
- `docs/documentation_index.md` for the documentation map.
- `docs/development_process.md` for the standard change workflow and verification ladder.
- `docs/local_agent_distribution.md` for the personal local-agent distribution target.
- `docs/local_isolation.md` for Mac-local dependency, cache, data, model, output, and cleanup rules.
- `docs/model_provider_strategy.md` for chat, embedding, rerank, and provider configuration.

## Quick Start

This project is developed as a local clone. Keep dependencies, caches, data, model artifacts, generated outputs, and logs inside the project root.

```bash
cp .env.example .env
# edit .env locally; never commit real keys
./scripts/setup-local.sh
source scripts/env.sh
./scripts/run-local.sh
```

API docs:

```text
http://127.0.0.1:8000/docs
```

Research workbench:

```text
http://127.0.0.1:8000/workbench
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Model Configuration

The system works without model credentials by falling back to deterministic local services. To enable model-backed structured extraction and idea generation, set OpenAI-compatible environment variables:

```env
MAIN_MODEL=
MAIN_BASE_URL=
MAIN_API_KEY=

EXTRACTION_MODEL=
EXTRACTION_BASE_URL=
EXTRACTION_API_KEY=

JUDGE_MODEL=
JUDGE_BASE_URL=
JUDGE_API_KEY=

EMBEDDER=
EMBEDDER_BASE_URL=
EMBEDDER_API_KEY=
RETRIEVAL_EMBEDDING_PROVIDER=auto

RERANK_MODEL=
RERANK_BINDING_HOST=
RERANK_API_KEY=
RETRIEVAL_RERANK_PROVIDER=auto

EXTERNAL_LITERATURE_SEARCH_ENABLED=false
OPENALEX_BASE_URL=https://api.openalex.org
```

If `EXTRACTION_*` is empty, paper card extraction falls back to the heuristic extractor. If `MAIN_*` is empty, idea generation falls back to the deterministic idea generator. Retrieval can run without provider credentials through the local hash index; external embedding and rerank providers are used only when configured.

## Verification

Run unit tests:

```bash
uv run pytest -q
```

Run the focused-suite contract check so default and long remote suites keep the intended boundary:

```bash
bash scripts/check_suite_contracts.sh
```

Run the check-script catalog sync check so README and check script structure stay aligned:

```bash
bash scripts/check_script_catalog.sh
```

Run the secret-file guard to catch sensitive-looking tracked filenames and required ignore patterns:

```bash
bash scripts/check_secret_file_guard.sh
```

Run the handoff document consistency check so AGENTS, TODO, README, and the handoff queue keep the local-development operating rules aligned:

```bash
bash scripts/check_handoff_docs.sh
```

Run the generated-file guard to catch tracked caches, virtualenvs, dependency folders, and build/coverage outputs:

```bash
bash scripts/check_generated_file_guard.sh
```

Run the local-agent readiness check to verify the clone-to-run contract, project-local cache/data/output paths, ignored local artifacts, model placeholders, and setup/run scripts without reading `.env` values:

```bash
bash scripts/check_local_agent_readiness.sh
```

Run the local operational preflight to confirm docs, runtime artifacts, environment template keys, compose persistence, and safe-suite hooks before a packaged local deployment. Use `PILOT_PREFLIGHT_STRICT_GIT=true` before sharing a release to require a clean `main` checkout aligned with `origin/main`:

```bash
bash scripts/check_pilot_operational_preflight.sh
```

Run the focused-test coverage map check so new pytest tests stay assigned to a focused remote check:

```bash
bash scripts/check_focused_test_coverage.sh
```

Run focused deployment artifact and local runtime contract checks without starting a service:

```bash
bash scripts/check_deployment_contracts.sh
```

Run backup/restore contract checks to keep persistent data volume, cold-backup, restore, migration, and operator-approval guardrails aligned without touching Docker or live data:

```bash
bash scripts/check_backup_restore_contracts.sh
```

Run focused context-search evaluation checks on the local `.venv`:

```bash
bash scripts/check_context_search_evaluations.sh
```

Run an opt-in real-provider smoke and real-paper PDF evaluation from a configured local environment:

```bash
ALLOW_REAL_MODEL_PROVIDER_SMOKE=1 .venv/bin/python scripts/smoke_model_providers.py
ALLOW_REAL_PAPER_EVAL=1 .venv/bin/python scripts/evaluate_real_papers.py path/to/paper.pdf
```

Real-paper reports are written to `outputs/evaluations/`, can compare configured retrieval against a local hash/no-rerank baseline, and are available in the Workbench Real Eval panel.

Run focused GraphRAG-lite duplicate-edge and graph stats checks:

```bash
bash scripts/check_graph_rag_lite.sh
```

Run focused research workflow primitive checks for local literature search, paper cards, structured extraction fallback, gaps, ideas, novelty, related work, and Markdown dossier exports:

```bash
bash scripts/check_research_workflow_primitives.sh
```

Run focused research planning checks for profiles, advisor briefs, plans, idea refinement, ranking, portfolios, and agenda exports:

```bash
bash scripts/check_research_planning_contracts.sh
```

Run the long focused research proposal check for proposal drafts, readiness reviews, revisions, revision tasks, and Markdown exports before proposal changes:

```bash
bash scripts/check_research_proposal_contracts.sh
```

Run the long focused suite for checks that are intentionally kept out of the default local focused suite:

```bash
bash scripts/check_remote_long_suite.sh
```

Run focused local readiness, status capability, first-run onboarding, and report guardrail checks without starting a service:

```bash
bash scripts/check_pilot_readiness.sh
```

Run the isolated product-effect smoke to validate the complete research-assistant workflow without touching the default local database:

```bash
bash scripts/check_product_effect_smoke.sh
```

Use `PRODUCT_EFFECT_SMOKE_PAPER_FILE=/path/to/paper.md` with `check_product_effect_smoke.sh` to run the same product-effect smoke against a representative paper fixture. The JSON output includes `product_effect_score`, `product_effect_band`, and a dimension-level `product_effect_scorecard` for foundation, research workflow, quality signal, and delivery loop readiness. Use `docs/representative_paper_review.md` for the human review protocol and findings table before marking a representative-paper local review acceptable.

Run focused write-audit guardrail checks without reading local audit logs:

```bash
bash scripts/check_write_audit_guardrails.sh
```

Run focused workflow job, artifact, async, cancel, and retry checks:

```bash
bash scripts/check_workflow_job_controls.sh
```

Run focused tool manifest and MCP bridge contract checks:

```bash
bash scripts/check_tool_bridge_contracts.sh
```

Run the current focused suite without starting services. The script name is historical and does not imply SSH or remote-server work:

```bash
bash scripts/check_remote_safe_suite.sh
```

Run the full in-process API smoke workflow:

```bash
uv run python scripts/smoke_api.py
```

Run the same smoke workflow against a live server:

```bash
uv run python scripts/smoke_api.py --base-url http://127.0.0.1:8000
```

The smoke workflow uploads a paper, validates the research profile, tool manifest, MCP-ready bridge spec, and task execution controls, runs the project setup wizard, checks project onboarding readiness, creates onboarding tasks, tracks onboarding progress, builds and saves the pilot status report snapshot, compares pilot report snapshots, creates pilot report snapshot tasks, creates pilot report comparison tasks, runs the literature-to-ideas workflow, fetches the workflow job trace, builds a related-work matrix, proposal draft, readiness review, proposal revision, task backlog, experiment run, experiment analysis, analysis follow-up tasks, decision memo, decision follow-up tasks, assumption audit, evidence ledger, evidence-ledger follow-up tasks, claim validation packet, claim validation queue, claim queue follow-up tasks, claim validation result tracking/reporting/decision signals, idea progress summary, idea research packet, idea timeline, readiness score, quality gate, quality-gate follow-up tasks, readiness follow-up tasks, idea bundle export, project readiness overview, project quality gate overview, project onboarding readiness after workflow, project cockpit dashboard, project advisor chat, project advisor chat tasks, project advisor action session, project cockpit tasks, project triage brief, project triage tasks, persisted project triage snapshots, triage snapshot comparison, triage comparison tasks, project quality-gate tasks, project overview, project bundle readiness, project bundle readiness tasks, persisted project bundle readiness snapshots, bundle readiness snapshot comparison, bundle readiness comparison tasks, project bundle release notes, project bundle release tasks, project bundle release progress, project bundle release feedback, project bundle release feedback tasks, project bundle release closeout, project bundle release closeout tasks, project bundle release acceptance packets, persisted release acceptance snapshots, release acceptance snapshot comparison, release acceptance comparison tasks, release review sessions, release review session tasks, release review outcomes, release review outcome tasks, release review outcome progress, release review outcome signoff evidence, project bundle export with claim validation queue metadata and pilot/readiness/release/review-outcome/signoff metadata, advisor brief, research execution plan, plan tasks, plan progress, plan-aware advisor brief, plan-aware progress/packet/bundle checks, and task board snapshot, performs context search, and checks graph endpoints.
It also validates the job artifact snapshot endpoint used by the workbench and future MCP tools. The final summary reports a product-effect scorecard so a run can be judged by both completion and quality-risk signals.

## Useful Endpoints

```http
GET  /health
GET  /health/ready
POST /research/papers/upload
GET  /research/papers
GET  /research/papers/{paper_id}
GET  /research/papers/{paper_id}/evidence
POST /research/literature/search
POST /research/embeddings/rebuild
GET  /research/evaluations/real-paper/reports
GET  /research/evaluations/real-paper/reports/latest
GET  /research/evaluations/real-paper/reports/{report_id}
GET  /research/tools/manifest
GET  /research/tools/mcp-spec
GET  /research/profile
PUT  /research/profile
GET  /research/profile/export/markdown
GET  /research/progress/overview
GET  /research/onboarding/readiness
POST /research/onboarding/setup
POST /research/onboarding/tasks
GET  /research/onboarding/progress
GET  /research/pilot/report
POST /research/pilot/report/snapshots
GET  /research/pilot/report/snapshots
POST /research/pilot/report/snapshots/compare
POST /research/pilot/report/snapshots/compare/export/markdown
POST /research/pilot/report/snapshots/compare/tasks
GET  /research/pilot/report/snapshots/{snapshot_id}
GET  /research/pilot/report/snapshots/{snapshot_id}/export/markdown
POST /research/pilot/report/snapshots/{snapshot_id}/tasks
GET  /research/cockpit
GET  /research/cockpit/export/markdown
POST /research/cockpit/tasks
POST /research/advisor/chat
POST /research/advisor/chat/tasks
POST /research/advisor/action-session
GET  /research/triage/brief
GET  /research/triage/brief/export/markdown
POST /research/triage/brief/tasks
POST /research/triage/snapshots
GET  /research/triage/snapshots
POST /research/triage/snapshots/compare
POST /research/triage/snapshots/compare/export/markdown
POST /research/triage/snapshots/compare/tasks
GET  /research/triage/snapshots/{snapshot_id}
GET  /research/triage/snapshots/{snapshot_id}/export/markdown
GET  /research/opportunities/radar
POST /research/opportunities/radar/tasks
POST /research/export/project-bundle/releases
GET  /research/export/project-bundle/releases
GET  /research/export/project-bundle/releases/{release_id}
GET  /research/export/project-bundle/releases/{release_id}/export/markdown
POST /research/export/project-bundle/releases/{release_id}/tasks
GET  /research/export/project-bundle/releases/{release_id}/progress
POST /research/export/project-bundle/releases/{release_id}/feedback
GET  /research/export/project-bundle/releases/{release_id}/feedback
GET  /research/export/project-bundle/releases/{release_id}/feedback/{feedback_id}
GET  /research/export/project-bundle/releases/{release_id}/feedback/{feedback_id}/export/markdown
POST /research/export/project-bundle/releases/{release_id}/feedback/{feedback_id}/tasks
GET  /research/export/project-bundle/releases/{release_id}/closeout
POST /research/export/project-bundle/releases/{release_id}/closeout/tasks
GET  /research/export/project-bundle/releases/{release_id}/acceptance-packet
POST /research/export/project-bundle/releases/{release_id}/acceptance-packet/snapshots
GET  /research/export/project-bundle/releases/{release_id}/acceptance-packet/snapshots
GET  /research/export/project-bundle/releases/{release_id}/acceptance-packet/snapshots/{snapshot_id}
GET  /research/export/project-bundle/releases/{release_id}/acceptance-packet/snapshots/{snapshot_id}/export/markdown
POST /research/export/project-bundle/releases/{release_id}/acceptance-packet/snapshots/compare
POST /research/export/project-bundle/releases/{release_id}/acceptance-packet/snapshots/compare/export/markdown
POST /research/export/project-bundle/releases/{release_id}/acceptance-packet/snapshots/compare/tasks
GET  /research/export/project-bundle/releases/{release_id}/review-session
POST /research/export/project-bundle/releases/{release_id}/review-session/tasks
POST /research/export/project-bundle/releases/{release_id}/review-session/outcomes
GET  /research/export/project-bundle/releases/{release_id}/review-session/outcomes
GET  /research/export/project-bundle/releases/{release_id}/review-session/outcomes/{outcome_id}
GET  /research/export/project-bundle/releases/{release_id}/review-session/outcomes/{outcome_id}/export/markdown
POST /research/export/project-bundle/releases/{release_id}/review-session/outcomes/{outcome_id}/tasks
GET  /research/export/project-bundle/releases/{release_id}/review-session/outcomes/{outcome_id}/progress
GET  /research/export/project-bundle/readiness
POST /research/export/project-bundle/readiness/tasks
POST /research/export/project-bundle/readiness/snapshots
GET  /research/export/project-bundle/readiness/snapshots
GET  /research/export/project-bundle/readiness/snapshots/{snapshot_id}
GET  /research/export/project-bundle/readiness/snapshots/{snapshot_id}/export/markdown
POST /research/export/project-bundle/readiness/snapshots/compare
POST /research/export/project-bundle/readiness/snapshots/compare/export/markdown
POST /research/export/project-bundle/readiness/snapshots/compare/tasks
GET  /research/export/project-bundle
POST /research/briefs
GET  /research/briefs
GET  /research/briefs/{brief_id}
GET  /research/briefs/{brief_id}/export/markdown
POST /research/plans
GET  /research/plans
GET  /research/plans/{plan_id}
GET  /research/plans/{plan_id}/export/markdown
POST /research/plans/{plan_id}/tasks
GET  /research/plans/{plan_id}/progress

POST /research/papers/{paper_id}/card/extract-structured
GET  /research/papers/{paper_id}/card/export/markdown

POST /research/gaps/mine
POST /research/gaps/{gap_id}/ideas
POST /research/ideas/{idea_id}/novelty-check
POST /research/ideas/{idea_id}/novelty-refresh
POST /research/ideas/{idea_id}/novelty-checks/{check_id}/tasks
POST /research/ideas/{idea_id}/review
POST /research/ideas/{idea_id}/experiment-plan
GET  /research/ideas/{idea_id}/experiment-runs
POST /research/experiment-plans/{plan_id}/runs
GET  /research/experiment-plans/{plan_id}/runs
GET  /research/experiment-runs/{run_id}
PATCH /research/experiment-runs/{run_id}
GET  /research/experiment-runs/{run_id}/export/markdown
POST /research/experiment-runs/{run_id}/analysis
GET  /research/experiment-runs/{run_id}/analyses
GET  /research/ideas/{idea_id}/experiment-analyses
GET  /research/experiment-analyses/{analysis_id}
GET  /research/experiment-analyses/{analysis_id}/export/markdown
POST /research/experiment-analyses/{analysis_id}/tasks
POST /research/ideas/{idea_id}/refine
GET  /research/ideas/{idea_id}/progress
GET  /research/ideas/{idea_id}/research-packet
GET  /research/ideas/{idea_id}/timeline
GET  /research/ideas/{idea_id}/readiness
GET  /research/ideas/{idea_id}/quality-gate
POST /research/ideas/{idea_id}/quality-gate/tasks
POST /research/ideas/{idea_id}/readiness/tasks
GET  /research/ideas/{idea_id}/export/bundle
GET  /research/readiness/overview
GET  /research/quality/overview
POST /research/quality/overview/tasks
POST /research/ideas/{idea_id}/decision-memo
GET  /research/ideas/{idea_id}/decision-memos
GET  /research/ideas/{idea_id}/decision-memos/{memo_id}
GET  /research/ideas/{idea_id}/decision-memos/{memo_id}/export/markdown
POST /research/ideas/{idea_id}/decision-memos/{memo_id}/tasks
POST /research/ideas/{idea_id}/assumption-audit
GET  /research/ideas/{idea_id}/assumption-audits
GET  /research/ideas/{idea_id}/assumption-audits/{audit_id}
GET  /research/ideas/{idea_id}/assumption-audits/{audit_id}/export/markdown
POST /research/ideas/{idea_id}/evidence-ledger
GET  /research/ideas/{idea_id}/evidence-ledgers
GET  /research/ideas/{idea_id}/evidence-ledgers/{ledger_id}
GET  /research/ideas/{idea_id}/evidence-ledgers/{ledger_id}/export/markdown
POST /research/ideas/{idea_id}/evidence-ledgers/{ledger_id}/tasks
GET  /research/ideas/{idea_id}/evidence-ledgers/{ledger_id}/claims/{claim_id}/validation-packet
GET  /research/claims/validation-queue
POST /research/claims/validation-queue/tasks
POST /research/tasks/{task_id}/claim-validation-result
POST /research/ideas/{idea_id}/related-work-matrix
GET  /research/ideas/{idea_id}/related-work-matrices
GET  /research/ideas/{idea_id}/related-work-matrices/{matrix_id}
GET  /research/ideas/{idea_id}/related-work-matrices/{matrix_id}/export/markdown
POST /research/ideas/{idea_id}/sota-review-package
GET  /research/ideas/{idea_id}/sota-review-packages
GET  /research/ideas/{idea_id}/sota-review-packages/{brief_id}
GET  /research/ideas/{idea_id}/sota-review-packages/{brief_id}/export/markdown
POST /research/ideas/{idea_id}/proposal-draft
GET  /research/ideas/{idea_id}/proposal-drafts
GET  /research/ideas/{idea_id}/proposal-drafts/{draft_id}
GET  /research/ideas/{idea_id}/proposal-drafts/{draft_id}/export/markdown
POST /research/ideas/{idea_id}/proposal-drafts/{draft_id}/review
GET  /research/ideas/{idea_id}/proposal-drafts/{draft_id}/reviews
GET  /research/ideas/{idea_id}/proposal-drafts/{draft_id}/reviews/{review_id}
GET  /research/ideas/{idea_id}/proposal-drafts/{draft_id}/reviews/{review_id}/export/markdown
GET  /research/ideas/{idea_id}/lineage
POST /research/ideas/{idea_id}/proposal-drafts/{draft_id}/revise
GET  /research/ideas/{idea_id}/proposal-drafts/{draft_id}/revisions
GET  /research/ideas/{idea_id}/proposal-drafts/{draft_id}/revisions/{revision_id}
GET  /research/ideas/{idea_id}/proposal-drafts/{draft_id}/revisions/{revision_id}/export/markdown
POST /research/ideas/{idea_id}/proposal-drafts/{draft_id}/revisions/{revision_id}/tasks
GET  /research/tasks
GET  /research/tasks/{task_id}
PATCH /research/tasks/{task_id}
POST /research/tasks/{task_id}/events
GET  /research/tasks/{task_id}/events
POST /research/tasks/snapshots
GET  /research/tasks/snapshots
GET  /research/tasks/snapshots/{snapshot_id}
GET  /research/tasks/snapshots/{snapshot_id}/export/markdown
POST /research/ideas/rank
POST /research/ideas/rank/export/markdown
POST /research/ideas/portfolios
GET  /research/ideas/portfolios
POST /research/ideas/portfolios/compare
POST /research/ideas/portfolios/compare/export/markdown
GET  /research/ideas/portfolios/{portfolio_id}
GET  /research/ideas/portfolios/{portfolio_id}/export/markdown
GET  /research/ideas/portfolios/{portfolio_id}/agenda/markdown
POST /research/ideas/{idea_id}/feedback
GET  /research/ideas/{idea_id}/feedback
GET  /research/ideas/{idea_id}/export/markdown

POST /research/search/context
GET  /research/graph/stats
GET  /research/graph/nodes
GET  /research/graph/edges
POST /research/workflows/literature-to-ideas
POST /research/workflows/literature-to-ideas/async
GET  /research/jobs/{job_id}
POST /research/jobs/{job_id}/cancel
POST /research/jobs/{job_id}/retry
GET  /research/jobs/{job_id}/artifacts
GET  /workbench
```

## MCP Bridge

Run the backend first, then start the stdio bridge for MCP-capable clients:

```bash
uv run python scripts/mcp_http_bridge.py --base-url http://127.0.0.1:8000
```

The bridge loads `/research/tools/mcp-spec`, exposes `tools/list` and `tools/call`, and forwards tool calls to the FastAPI routes.
For safer client onboarding, narrow the exposed tools before connecting a client:

```bash
uv run python scripts/mcp_http_bridge.py --base-url http://127.0.0.1:8000 --read-only
uv run python scripts/mcp_http_bridge.py --base-url http://127.0.0.1:8000 --allow-tool get_project_progress --allow-tool get_idea_progress
uv run python scripts/mcp_http_bridge.py --base-url http://127.0.0.1:8000 --health-check
```

When `/research/*` API-key protection is enabled, forward the same key with `--api-key`, `MCP_BRIDGE_API_KEY`, `RESEARCH_ASSISTANT_API_KEY`, or `API_KEY`. Forward the non-secret project scope with `--project-id`, `MCP_BRIDGE_PROJECT_ID`, or `RESEARCH_ASSISTANT_PROJECT_ID`; the default header is `X-Research-Assistant-Project`.
The same policy can be configured with `MCP_BRIDGE_READ_ONLY`, `MCP_BRIDGE_ALLOW_TOOLS`, and `MCP_BRIDGE_DENY_TOOLS`.

## Local Deployment

For the normal local personal-agent path:

```bash
cp .env.example .env
# fill model provider keys in .env, then:
./scripts/setup-local.sh
source scripts/env.sh
./scripts/run-local.sh
```

For optional single-user Docker use, set a local `API_KEY` in `.env` and run Docker only after explicit operator approval:

```bash
docker compose up --build
```

See `docs/deployment.md` for the runtime contract, local deployment checklist, `/app/data` backup/restore operator notes, database/upload/audit ready checks, API key calls, Workbench key storage, MCP bridge auth forwarding, and backup notes. Write-operation audit logging has a configurable JSONL prototype plus default-off local-owner summary and bounded export endpoints described in `docs/write_operation_audit_design.md`. Admin-only audit access rules are documented in `docs/admin_authorization_policy.md`, and retention/export workflow is documented in `docs/write_audit_retention_policy.md`. Database migration policy is documented in `docs/database_migration_strategy.md` before migration tooling is introduced. Long-running workflow queue migration is documented in `docs/workflow_queue_design.md` before adding worker dependencies or deployment services.

## Near-Term Roadmap

- Polish the clone-to-run local setup path, local preflight, and `.env.example` guidance.
- Add real-provider smoke tests, batch embedding, page-image retrieval, and retrieval-mode evaluation fixtures.
- Add practical local benchmark recipes and prediction-generation pipelines for geolocalization evaluation.
- Add fully automated current-SOTA closure on top of manual SOTA review packages and external novelty search adapters.
- Add durable local worker queues, richer retry policies, and resumable workflow state for long runs.
- Expand the research Workbench into a full single-researcher review/edit loop.
- Harden optional local auth, backup/export, and richer binary artifact handling around the lightweight MCP bridge.

## Handoff And Operations

- `AGENTS.md` records local-development agent rules, safety boundaries, and verification expectations.
- `TODO.md` summarizes the active local-development priority queue.
- `codex_handoff/03_TODO.md` keeps the detailed historical handoff queue.
- `docs/progress_log.md` keeps the chronological implementation and verification log.

## Design Documents

- `docs/research_assistant_requirements.md`
- `docs/research_assistant_technical_design.md`
- `docs/local_agent_distribution.md`
- `docs/admin_authorization_policy.md`
- `docs/database_migration_strategy.md`
- `docs/write_operation_audit_design.md`
- `docs/write_audit_retention_policy.md`
- `docs/user_project_scoping_design.md`
- `docs/workflow_queue_design.md`
- `docs/graphrag_langgraph_deerflow_evaluation.md`
- `docs/context_search_evaluation_plan.md`
- `docs/representative_paper_review.md`
