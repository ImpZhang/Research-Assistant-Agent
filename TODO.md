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

- Polish clone-to-run setup, local preflight, and `.env.example` so first-time users can configure model API keys without reading internal docs. Current baseline: `scripts/check_local_agent_readiness.sh` validates the local readiness contract without reading `.env`.
- Keep model-provider setup diagnosable through `scripts/check_model_provider_config.py` before running explicit real-provider smokes.
- Enable live external-search providers for local real-provider settings and require completed SOTA external-search evidence packages before final signoff.
- Add practical local benchmark recipes and prediction-generation pipelines on top of the guarded benchmark runner. Current baseline: `scripts/check_local_geoloc_benchmark_smoke.sh` verifies the local JSONL metric path with temporary fixtures, and `scripts/prepare_local_geoloc_benchmark.py` prepares ignored local files/profile manifests.
- Keep real multi-project/user isolation deferred; the current product is single-operator local deployment with a default project.
- Add Alembic-style migrations.
- Harden local queue/worker execution for long-running workflows and benchmark runs.
- Add local backup/export/import rehearsal and optional single-user Docker deployment checks.
- Keep backup planning grounded in `scripts/build_local_backup_manifest.py` before adding any data-copying or restore automation.
- Improve page/figure/table-aware PDF evidence extraction.

## P3 - Needs Explicit Operator Approval

- Dependency installation or synchronization.
- Docker compose startup or persistent service restarts.
- Database migrations or data cleanup.
- Production/private data inspection, exports, or backups.
- Any remote SSH/server work.
