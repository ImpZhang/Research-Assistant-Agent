# TODO

This top-level TODO is the local development index for Research Assistant Agent. Development happens in this repository and is synchronized through GitHub.

Current product target: personal local deployment. A user should be able to clone the GitHub repository, create an untracked `.env`, provide their own model API keys, and run the agent locally without a central server, system access key, or multi-user SaaS layer.

## P0 - Local Development Safety

- Treat this local clone plus GitHub `main` as the current source of truth.
- Do not run remote SSH checks unless the operator explicitly asks for remote work.
- Check `git status --short`, branch, and recent commits before every edit round.
- Keep dependencies, caches, generated outputs, model files, logs, and data under this project root.
- Do not read or commit secrets, `.env` values, credentials, cookies, private keys, or production/private data.
- Run `bash scripts/check_secret_file_guard.sh` before changing ignore rules or adding config/auth-related files.
- Run `bash scripts/check_handoff_docs.sh` before changing AGENTS, README, TODO, handoff docs, or progress-log structure.
- Run `bash scripts/check_generated_file_guard.sh` before changing ignore rules or adding generated-artifact-producing tooling.

## P1 - Current Local Verification

- Run `bash scripts/check_context_search_evaluations.sh` before changing retrieval, external provider adapters, SOTA review/signoff, benchmark packets, or real-paper evaluation flow.
- Run `bash scripts/check_suite_contracts.sh` before changing default or long suite composition.
- Run `bash scripts/check_script_catalog.sh` before adding, renaming, or restructuring check scripts.
- Run `bash scripts/check_focused_test_coverage.sh` before adding or renaming pytest tests so every test remains assigned to a focused check script.
- Run `bash scripts/check_deployment_contracts.sh` before changing Dockerfile, docker-compose, deployment docs, migration/admin policy docs, or `.env.example` runtime placeholders.
- Run `bash scripts/check_pilot_readiness.sh` before changing pilot readiness, `/research/status` capabilities, setup wizard, onboarding tasks/progress, pilot reports, API-key guard, upload guardrail, or workbench first-run behavior.
- Run `bash scripts/check_research_workflow_primitives.sh` before changing local literature search, paper card extraction, structured extraction fallback, gap/idea generation, novelty screening, related-work matrices, or Markdown dossier exports.
- Run `bash scripts/check_research_planning_contracts.sh` before changing research profiles, advisor briefs, research plans, idea refinement, ranking, portfolios, agenda exports, or lineage/bundle planning metadata.
- Run `bash scripts/check_research_proposal_contracts.sh` before changing proposal drafts, proposal readiness reviews, proposal revisions, revision follow-up tasks, or proposal Markdown exports.
- `scripts/check_remote_safe_suite.sh` and `scripts/check_remote_long_suite.sh` are historical names; when used locally, treat them as local focused suites, not instructions to contact the remote server.

## P2 - Personal Local Agent Follow-Ups

- Follow `docs/agent_engineering_strengthening_plan.md` for the next agent-engineering upgrades: trace tables, bounded Advisor tool calling, project-local skills, bad-case replay, and one isolated LangGraph workflow without replacing the stable service-layer workflow.
- Current trace baseline: `AgentRun`, `ToolCallRecord`, and `ReplayCase` persistence exists, and Advisor chat writes an `advisor_chat` run plus cockpit/context read tool-call records.
- Polish clone-to-run setup, local preflight, and `.env.example` so first-time users can configure model API keys without reading internal docs. Current baseline: `scripts/check_local_agent_readiness.sh` validates the local readiness contract without reading `.env`.
- Keep model-provider setup diagnosable through `scripts/check_model_provider_config.py` before running explicit real-provider smokes.
- Keep clone diagnostics consolidated through `scripts/check_local_doctor.sh` as setup, backup, SQLite-maintenance, and benchmark checks grow. Current baseline: `scripts/check_sqlite_maintenance.py` reports aggregate SQLite storage, table, vector-index, trace, sidecar, and quick-check status without reading secrets or private paper content.
- Current real-paper evaluation baseline: 12 geolocalization/place-recognition papers completed strictly with `multimodal-embedding-v1`, async workflow polling, retrieval comparison, and benchmark profile execution. Current query-evidence baseline: `scripts/build_geoloc_eval_dataset.py` and `scripts/check_geoloc_eval_dataset.py` generate and validate an ignored local 75-item query-evidence set plus 30 replay cases. Next evaluation credibility work is manual review and human-authored hard questions, not merely adding more PDFs.
- Enable live external-search providers for local real-provider settings and require completed SOTA external-search evidence packages before final signoff.
- Add practical local benchmark recipes and prediction-generation pipelines on top of the guarded benchmark runner. Current baseline: `scripts/check_local_geoloc_benchmark_smoke.sh` verifies the local JSONL metric path with temporary fixtures, `scripts/prepare_local_geoloc_benchmark.py` prepares ignored local files/profile manifests, and `scripts/run_geoloc_benchmark_pipeline.py` turns ground-truth/prediction JSONL artifacts into JSON/Markdown benchmark reports.
- Keep real multi-project/user isolation deferred; the current product is single-operator local deployment with a default project.
- Add live Alembic migration execution once dependency sync and operator migration commands are explicitly approved. Current baseline: `migrations/baseline_schema.json` and `scripts/check_migration_baseline.py` detect SQLAlchemy metadata drift without running live migrations.
- Harden local queue/worker execution for long-running workflows and benchmark runs. Current baseline: real-paper evaluation uses `async-poll` with visible job stages, poll history, artifact hydration, timeout recovery, and strict external-embedding fallback detection; the API also supports `WORKFLOW_BACKGROUND_TASKS_ENABLED=false` plus `scripts/run_workflow_worker.py` for an external local SQLite worker with lease/heartbeat metadata, stale-lease recovery, and bounded failed-job retry queueing. Remaining work is resumable workflow checkpoints.
- Keep optional single-user Docker deployment checks static unless the operator explicitly approves Docker startup. Current baseline: `scripts/check_single_user_docker_deployment.py` validates Dockerfile, compose, dockerignore, env-template, and deployment-doc contracts without starting Docker or reading `.env`.
- Keep backup planning grounded in `scripts/build_local_backup_manifest.py` before adding any real data-copying or restore automation. Current baseline: `scripts/rehearse_local_backup_restore.py` runs a synthetic-only archive/restore/manifest comparison and secret-exclusion rehearsal without copying live local data.
- Improve page/figure/table-aware PDF evidence extraction.

## P2 - Agent Interview Strengthening Follow-Ups

- Extend the bounded Advisor read-tool plan with replay workflow generation and richer live replay automation. Current baseline: opt-in model-ranked read-tool selection is candidate-validated with deterministic fallback, failed Advisor read tools are captured as failed `ToolCallRecord` rows plus `advisor_tool_failure` replay cases, replay invocations can opt into `agent_replay` trace recording, and context-search/citation/SOTA-readiness replay cases can opt into local live replay without external model calls.
- Add stricter tool schema validation/error branches for Advisor tool selection while preserving the existing response contract and deterministic fallback.
- Extend the project-local skill registry beyond the current `paper-ingestion`, `hybrid-context-search`, `literature-to-ideas`, `sota-review`, `benchmark-evaluation`, and `advisor-action-session` docs as new agent workflows are added.
- Extend the initial bad-case replay script with automatic wrong-citation/evidence-link replay-case creators and optional scheduled reports. Current baseline: context-search miss replay can execute local retrieval and validate required chunk/evidence/gap/idea ids plus minimum result counts; Advisor chat automatically captures evidence-seeking context misses; citation audit replay validates cited evidence existence, paper ownership, and required terms; SOTA-readiness replay audits signoff/manual-gate/external-search/benchmark blockers; SOTA signoff creation automatically captures confirmed-but-not-ready false positives; `--record-run` persists replay summary and live executor tool calls for audit; `/research/agent/metrics` aggregates replay case types, replay run statuses, live executor usage, and failed replay-run count.
- Extend the isolated LangGraph advisor/deep-review workflow with live replay hooks, optional human/write nodes, and richer verification after bounded tool selection matures; keep the current `WorkflowService` path intact.
- Strengthen local deployment polish around `.env.example`, backup/restore rehearsal, cleanup safety, first-run demo runbooks, and future approved SQLite maintenance actions. Current baseline: doctor diagnostics include the read-only SQLite maintenance report.

## P3 - Needs Explicit Operator Approval

- Dependency installation or synchronization.
- Docker compose startup or persistent service restarts.
- Database migrations or data cleanup.
- Production/private data inspection, exports, or backups.
- Any remote SSH/server work.
