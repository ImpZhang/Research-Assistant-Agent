# Progress Log

This log records local-first maintenance and implementation progress for Research Assistant Agent. It intentionally excludes passwords, API keys, real `.env` values, cookies, private keys, and other secret material.

## 2026-06-29 - Realistic Gold Evidence Evaluation

Implementation completed:

- Added `configs/geoloc_realistic_gold.v1.jsonl` as a reviewer-style gold-label spec with blind natural queries, primary/supporting gold targets, required evidence terms, target-paper leakage checks, and label rationales.
- Added `scripts/build_geoloc_realistic_eval.py` to resolve the committed gold-label spec against the local 12-paper SQLite corpus and write ignored local `realistic_gold_questions.jsonl`, `realistic_replay_cases.jsonl`, `realistic_gold_manifest.json`, and `realistic_gold_review.md`.
- Added `scripts/check_geoloc_realistic_eval.py` to run realistic corpus-level retrieval without per-query paper filters, calculate primary hit@1/3/5/8, any/all-gold hit@8, primary MRR, partial/miss counts, replay pass rate, and export primary-miss replay cases.
- Added regression coverage in `tests/test_geoloc_eval_dataset_tools.py` proving realistic gold labels resolve to evidence, preserve label rationales, and run no-per-query-filter retrieval checks.
- Wired the new scripts into `scripts/check_context_search_evaluations.sh`.
- Updated README, TODO, documentation index, and geoloc evaluation docs to distinguish regression-style hard questions from realistic no-filter metrics.

Local realistic evaluation generated:

- Questions: `20`.
- Gold labels: `38` total, `20` primary and `18` supporting.
- Corpus scope: `12` papers.
- Per-query paper filter: `false`.
- Primary hit@1: `0.2`.
- Primary hit@3: `0.5`.
- Primary hit@5: `0.5`.
- Primary hit@8: `0.65`.
- Any-gold hit@8: `0.65`.
- All-gold hit@8: `0.4`.
- Primary MRR: `0.3571`.
- Replay pass rate: `0.65`.
- Primary misses: `7`.
- Partial gold hits: `5`.
- Failure replay cases: `7`.
- Second-pass metrics matched the first pass.

Verification completed:

- `.venv/bin/pytest -q tests/test_geoloc_eval_dataset_tools.py::test_geoloc_realistic_gold_builder_and_checker` passed.
- `.venv/bin/python scripts/build_geoloc_realistic_eval.py --dataset-dir data/evaluation/geoloc_12paper --gold-spec configs/geoloc_realistic_gold.v1.jsonl --dataset-id geoloc_12paper_realistic_gold_v1 --min-questions 20 --json` passed.
- `.venv/bin/python scripts/check_geoloc_realistic_eval.py --dataset-dir data/evaluation/geoloc_12paper --min-questions 20 --min-paper-coverage 12 --min-primary-hit-at-8 0.5 --min-mrr-primary 0.2 --min-replay-pass-rate 0.5 --write-json data/evaluation/geoloc_12paper/realistic_quality_report.json --write-markdown data/evaluation/geoloc_12paper/realistic_quality_report.md --write-failure-replay data/evaluation/geoloc_12paper/realistic_failure_replay_cases.jsonl --json` passed.
- Re-ran build/check to `realistic_quality_report_second_pass.json` and compared key metrics against the first report; all matched.
- `.venv/bin/ruff check scripts/build_geoloc_realistic_eval.py scripts/check_geoloc_realistic_eval.py tests/test_geoloc_eval_dataset_tools.py` passed.
- `.venv/bin/ruff format --check` equivalent for the new/changed realistic eval scripts and tests passed.
- `bash scripts/check_handoff_docs.sh`, `bash scripts/check_focused_test_coverage.sh`, `bash scripts/check_script_catalog.sh`, `bash scripts/check_secret_file_guard.sh`, `bash scripts/check_generated_file_guard.sh`, and `git diff --check` passed.
- `bash scripts/check_context_search_evaluations.sh` passed: `51 passed`.
- `bash scripts/check_local_safe_suite.sh` passed; the local operational preflight warning about git status was expected because this implementation round had uncommitted changes.

## 2026-06-29 - Human Hard Questions And PDF Ingestion P3 Hardening

Implementation completed:

- Added `configs/geoloc_hard_questions.v1.jsonl` with 20 researcher-style hard questions for idea search, novelty boundaries, baselines, retrieval design, failure modes, reasoning signals, and benchmark gaps.
- Added `scripts/build_geoloc_hard_questions.py` to map committed hard-question seeds to local SQLite evidence ids and generate ignored local hard replay cases.
- Added `scripts/check_geoloc_hard_questions.py` to validate hard-question count, paper coverage, intent coverage, evidence existence, strict retrieval hit@8, and replay pass rate.
- Added regression coverage in `tests/test_geoloc_eval_dataset_tools.py` for hard-question build/check behavior with a temporary SQLite fixture.
- Hardened upload ingestion title guessing to skip publisher/header/front-matter noise and fall back to safer filename-derived titles.
- Expanded section-heading detection for common PDF variants such as `Methods`, `Experimental Setup`, `Results and Discussion`, `Conclusion and Future Work`, and trailing punctuation.
- Added chunk-level evidence top-up for long sparse full-text sections so PDFs with weak heading extraction produce enough retrievable evidence for downstream gap/idea work.
- Added upload regression tests for noisy title guessing, compound heading variants, and sparse full-text evidence top-up.

Local hard-question dataset generated:

- Hard questions: `20`.
- Hard replay cases: `20`.
- Papers covered: `12`.
- Intents covered: `19`.
- Retrieval any-hit@8: `1.0`.
- Retrieval all-gold-hit@8: `1.0`.
- Replay pass rate: `1.0`.
- Errors: `0`; warnings: `0`.

Verification completed:

- `.venv/bin/ruff format backend/research/services/document_ingestion.py scripts/build_geoloc_hard_questions.py scripts/check_geoloc_hard_questions.py tests/test_app.py tests/test_geoloc_eval_dataset_tools.py` passed.
- `.venv/bin/ruff check backend/research/services/document_ingestion.py scripts/build_geoloc_hard_questions.py scripts/check_geoloc_hard_questions.py tests/test_app.py tests/test_geoloc_eval_dataset_tools.py` passed.
- `.venv/bin/pytest -q tests/test_geoloc_eval_dataset_tools.py tests/test_app.py::test_upload_skips_noisy_front_matter_when_guessing_title tests/test_app.py::test_upload_detects_compound_heading_variants tests/test_app.py::test_upload_long_sparse_text_adds_chunk_topup_evidence tests/test_app.py::test_upload_preserves_preamble_when_only_reference_heading_matches tests/test_app.py::test_upload_detects_roman_heading_sections_and_claim_gap_topup tests/test_app.py::test_upload_filters_metadata_checklist_and_leading_chart_noise` passed: `8 passed`.
- `.venv/bin/python scripts/build_geoloc_hard_questions.py --dataset-dir data/evaluation/geoloc_12paper --questions configs/geoloc_hard_questions.v1.jsonl --dataset-id geoloc_12paper_hard_questions_v1 --min-hard-questions 20 --json` passed.
- `.venv/bin/python scripts/check_geoloc_hard_questions.py --dataset-dir data/evaluation/geoloc_12paper --min-hard-questions 20 --min-paper-coverage 12 --min-intent-coverage 12 --run-retrieval --min-any-hit-at-8 1.0 --min-all-hit-at-8 1.0 --min-replay-pass-rate 1.0 --write-json data/evaluation/geoloc_12paper/hard_question_quality_report.json --write-markdown data/evaluation/geoloc_12paper/hard_question_quality_report.md --json` passed.
- `bash scripts/check_script_catalog.sh`, `bash scripts/check_handoff_docs.sh`, `bash scripts/check_secret_file_guard.sh`, `bash scripts/check_generated_file_guard.sh`, `bash scripts/check_focused_test_coverage.sh`, and `git diff --check` passed.
- `bash scripts/check_research_workflow_primitives.sh` passed: `57 passed`.
- `bash scripts/check_context_search_evaluations.sh` passed: `50 passed`.
- `bash scripts/check_local_safe_suite.sh` passed; the local operational preflight warning about git status was expected because this implementation round had uncommitted changes.

## 2026-06-29 - Query-Evidence Dataset And Replay Quality Gates

Implementation completed:

- Added `scripts/build_geoloc_eval_dataset.py` to build ignored local `data/evaluation/geoloc_12paper/` artifacts from the 12-paper real evaluation report and local SQLite evidence rows.
- Added `scripts/check_geoloc_eval_dataset.py` to validate dataset shape, evidence ids, paper ownership, query/evidence overlap, secret-like content, retrieval hit rates, and replay pass rates.
- Added regression coverage in `tests/test_geoloc_eval_dataset_tools.py` with a temporary SQLite fixture, generated query-evidence rows, replay cases, retrieval validation, JSON report, and Markdown report.
- Wired the new scripts and tests into `scripts/check_context_search_evaluations.sh`.
- Added `docs/geoloc_eval_dataset_quality.md` as the durable quality policy and command reference.

Local dataset generated:

- Dataset directory: `data/evaluation/geoloc_12paper/` (ignored by Git).
- Query-evidence pairs: `75`.
- Replay cases: `30`.
- Papers covered: `12`.
- Replay types: `22` context-search cases and `8` citation-audit cases.

Quality verification completed:

- `.venv/bin/python scripts/check_geoloc_eval_dataset.py --dataset-dir data/evaluation/geoloc_12paper --run-retrieval ...` passed.
- Re-ran the same checker with a second quality-report output; it passed with identical retrieval and replay metrics.
- Retrieval hit@1: `0.9867`; hit@3: `1.0`; hit@8: `1.0`.
- Replay pass rate: `1.0`.
- Errors: `0`; warnings: `0`.
- `bash scripts/check_context_search_evaluations.sh` passed: `49 passed`.
- `bash scripts/check_focused_test_coverage.sh`, `bash scripts/check_script_catalog.sh`, `bash scripts/check_handoff_docs.sh`, `bash scripts/check_secret_file_guard.sh`, and `bash scripts/check_generated_file_guard.sh` passed.

## 2026-06-29 - Twelve-Paper Evaluation Set Expansion

Strict real evaluation completed:

- Expanded the strict geolocalization/place-recognition evaluation set from `4` to `12` papers by adding Img2Loc, PIGEON, Street-Level Geolocalization with MLLM+RAG, Vision-Language Reasoning for Geolocalization, GEOMR, HADGEO, CAMP, and NetVLAD.
- Report: `outputs/evaluations/real_paper_eval_20260628_160429.json`.
- Completed papers: `12 / 12`; failed papers: `0`.
- Workflow recovered count: `0`.
- Provider fallback warnings: `0`.
- Embedding models: `["multimodal-embedding-v1"]`; embedding dimension: `1024`; indexed objects: `99`.
- Context-search evidence coverage: `12 / 12` papers.
- Retrieval comparison: `36` queries with `27` top-evidence overlaps.
- Benchmark runs/completed: `12 / 12`.
- Proposal review decision was `ready_for_advisor_review` for all 12 papers.

Evaluation implications:

- The project now has a stronger real-paper workflow stability story than the previous 3-4 paper smoke.
- The 12-paper run still does not prove scientific SOTA, broad generalization, or citation correctness by itself.
- The next evaluation layer should be 50-80 labeled query-evidence pairs and 20-30 bad-case replay cases covering context misses, citation mismatch, title/section extraction noise, weak evidence, benchmark artifact gaps, and worker/retry edge cases.

## 2026-06-28 - GeoRanker Restored To Strict Evaluation Set

Implementation completed:

- Raised the default local paper upload limit from 10 MiB to 20 MiB in `backend/research/config.py`, `.env.example`, and `docs/deployment.md` so larger representative PDFs such as GeoRanker can be evaluated without disabling upload protection.
- Kept upload guardrail behavior intact: oversized files are still rejected when `PAPER_UPLOAD_MAX_BYTES` is set lower, and invalid/non-positive values still fall back safely.
- Re-ran the strict real-paper evaluation with GeoRanker, G3, GeoToken, and Recognition through Reasoning.

Strict real evaluation completed:

- Report: `outputs/evaluations/real_paper_eval_20260628_155144.json`.
- Completed papers: `4 / 4`; failed papers: `0`.
- Workflow recovered count: `0`.
- Provider fallback warnings: `0`.
- Embedding models: `["multimodal-embedding-v1"]`; embedding dimension: `1024`; indexed objects: `38`.
- Context-search evidence coverage: `4 / 4` papers.
- Retrieval comparison: `12` queries with `8` top-evidence overlaps.
- Benchmark runs/completed: `4 / 4`.
- Proposal review decision was `ready_for_advisor_review` for all four papers.

Verification completed:

- `.venv/bin/ruff check backend/research/config.py tests/test_app.py` passed.
- `.venv/bin/python -m pytest tests/test_app.py::test_upload_rejects_file_larger_than_limit tests/test_app.py::test_upload_invalid_max_bytes_falls_back_to_default_limit tests/test_app.py::test_upload_non_positive_max_bytes_falls_back_to_default_limit` passed: `3 passed`.

## 2026-06-28 - Strict Three-Paper Evaluation And Local Hardening

Implementation completed:

- Added `scripts/run_geoloc_benchmark_pipeline.py` to convert project-local geolocalization ground-truth and prediction JSONL artifacts into JSON/Markdown benchmark pipeline reports.
- Refactored `scripts/benchmark_geoloc_predictions.py` so the metric computation is reusable by the pipeline script.
- Hardened `WorkflowWorkerService` with stale-lease recovery, bounded failed-job retry queueing, and a targeted `run_job(job_id)` path for deterministic local worker diagnostics.
- Extended `scripts/run_workflow_worker.py` with `--job-id`, `--stale-lease-seconds`, `--max-auto-retries`, and `--retry-backoff-seconds`.
- Added `migrations/baseline_schema.json`, `migrations/README.md`, and `scripts/check_migration_baseline.py` as an Alembic-style metadata baseline and drift check without adding Alembic, running migrations, or touching live data.
- Updated README, TODO, deployment, documentation index, workflow queue design, and database migration strategy to reflect the current benchmark, worker, and migration-baseline capabilities.

Strict real evaluation completed:

- Ran G3, GeoToken, and Recognition through Reasoning PDFs with `multimodal-embedding-v1`, `--require-external-embeddings`, async workflow polling, retrieval comparison, and `--benchmark-profile-id json-metrics-smoke`.
- Report: `outputs/evaluations/real_paper_eval_20260628_131612.json`.
- Completed papers: `3 / 3`; failed papers: `0`.
- Workflow recovered count: `0`.
- Provider fallback warnings: `0`.
- Embedding models: `["multimodal-embedding-v1"]`; embedding dimension: `1024`; indexed objects: `30`.
- Context-search evidence coverage: `3 / 3` papers.
- Retrieval comparison: `9` queries with `7` top-evidence overlaps.
- Benchmark runs/completed: `3 / 3`.
- Proposal review decision was `ready_for_advisor_review` for all three papers.

Verification completed:

- `bash scripts/check_workflow_job_controls.sh` passed: `11 passed`.
- `bash scripts/check_deployment_contracts.sh` passed: `17 passed`.
- `.venv/bin/python -m pytest tests/test_sota_signoff_and_benchmark.py::test_geoloc_prediction_benchmark_harness_outputs_metrics tests/test_sota_signoff_and_benchmark.py::test_geoloc_benchmark_pipeline_writes_json_and_markdown_reports tests/test_sota_signoff_and_benchmark.py::test_geoloc_benchmark_pipeline_reports_missing_inputs` passed: `3 passed`.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `bash scripts/check_script_catalog.sh` passed.
- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_local_safe_suite.sh` passed, including deployment contracts `17 passed`, workflow job controls `11 passed`, local geolocalization benchmark smoke, and context-search/evaluation checks `48 passed`.

## 2026-06-28 - Embedding Model Switch

Implementation completed:

- Switched the current embedding model template and deployment docs from `qwen3-vl-embedding` to `multimodal-embedding-v1`.
- Updated the retrieval provider adapter so DashScope multimodal fallback covers `multimodal-embedding-*` model names as well as the earlier VL embedding name.
- Updated provider configuration, retrieval adapter, and real-evaluation report tests to use `multimodal-embedding-v1` as the current embedding model.
- Updated the local ignored `.env` `EMBEDDER` value without printing or committing secret file contents.

Verification completed:

- `.venv/bin/ruff check backend/research/adapters/retrieval_provider_adapter.py tests/test_model_provider_config.py tests/test_retrieval_provider_adapter.py tests/test_evaluation_reports.py` passed.
- `.venv/bin/ruff format --check backend/research/adapters/retrieval_provider_adapter.py tests/test_model_provider_config.py tests/test_retrieval_provider_adapter.py tests/test_evaluation_reports.py` passed.
- `.venv/bin/python -m pytest tests/test_model_provider_config.py tests/test_retrieval_provider_adapter.py tests/test_evaluation_reports.py` passed: `17 passed`.
- Application config loaded the local `.env` and reported `settings.embedder=multimodal-embedding-v1` without printing provider keys.
- `env ALLOW_REAL_MODEL_PROVIDER_SMOKE=1 .venv/bin/python scripts/smoke_model_providers.py` passed for main, extraction, judge, embedding, and rerank; `multimodal-embedding-v1` returned 1024-dimensional vectors.
- Strict real-paper evaluation passed on GeoToken with `--require-external-embeddings`, async workflow polling, and `--benchmark-profile-id json-metrics-smoke`.
- Strict report: `outputs/evaluations/real_paper_eval_20260628_095514.json`.
- Strict report summary: `completed_paper_count=1`, `provider_fallback_warning_count=0`, `embedding_models=["multimodal-embedding-v1"]`, `benchmark_run_count=1`, and `benchmark_completed_count=1`.

## 2026-06-28 - Async-Poll Real Evaluation Workflow

Implementation completed:

- Added explicit workflow job stage reporting through `JobRead.stage` and `JobRead.stage_message`.
- Updated `WorkflowService` to persist stage/progress updates for queued, starting, card extraction, gap mining, idea generation, quality artifact creation, Markdown rendering, completion, and timeout states.
- Added `WORKFLOW_BACKGROUND_TASKS_ENABLED`; when set to `false`, async workflow routes only enqueue jobs so a separate local worker can consume them.
- Added `WorkflowWorkerService` and `scripts/run_workflow_worker.py` as a project-local SQLite worker path that claims pending workflow jobs, records lease/heartbeat metadata in `Job.output_json`, runs the workflow, and preserves existing polling/artifact endpoints.
- Changed `scripts/evaluate_real_papers.py` default workflow execution mode to `async-poll`.
- Implemented a local short-lived worker process for real-paper evaluation jobs so the evaluator can queue a workflow job, poll `GET /research/jobs/{job_id}`, hydrate artifacts, and avoid relying on `TestClient` synchronous background-task behavior.
- Preserved `--workflow-mode sync-endpoint` as a legacy diagnostic option.
- Added optional benchmark-profile execution to the real-paper evaluator with `--benchmark-profile-id` and `--require-benchmark-profile`, so deep quality reports can use guarded local benchmark runs instead of only synthetic planning dry runs.
- Added workflow poll history, execution mode, stage, recovery count, and provider-fallback warning counts to JSON and Markdown real-paper evaluation reports.
- Added `--require-external-embeddings` so strict real-provider evaluations fail when embedding rebuild falls back to local hash embeddings.
- Added tests for job stage serialization, local worker execution, normal async artifact summaries, recovered artifact summaries, provider-fallback warnings, benchmark-backed report rendering, and report rendering.

Real verification completed:

- Ran one real GeoToken PDF through the new `async-poll` evaluator path with `--skip-deep-quality-loop` and `--skip-retrieval-mode-comparison`.
- Verified visible stage polling: `queued`, `extracting_card`, `generating_ideas`, and `completed`.
- Latest smoke report: `outputs/evaluations/real_paper_eval_20260628_044953.json`.
- The smoke completed `1 / 1` paper with no workflow recovery.
- Ran one real GeoToken PDF through the benchmark-backed deep quality path with `--benchmark-profile-id json-metrics-smoke`.
- Benchmark-backed smoke report: `outputs/evaluations/real_paper_eval_20260628_050448.json`.
- The benchmark-backed smoke completed `1 / 1` paper, recorded `workflow_execution_mode=async_job_polling`, `workflow_stage=completed`, `benchmark_run_count=1`, `benchmark_completed_count=1`, and `experiment_run_source=benchmark_profile`.
- External embedding provider smoke currently fails for embedding with `HTTP 403 AllocationQuota.FreeTierOnly`; main, extraction, judge, and rerank still pass. The evaluator now records local-hash fallback warnings and can fail strictly via `--require-external-embeddings`.

Verification completed:

- `.venv/bin/ruff check backend/research/schemas.py backend/research/routes.py backend/research/services/workflow_service.py scripts/evaluate_real_papers.py tests/test_app.py tests/test_evaluation_reports.py` passed.
- `.venv/bin/ruff format --check backend/research/schemas.py backend/research/routes.py backend/research/services/workflow_service.py scripts/evaluate_real_papers.py tests/test_app.py tests/test_evaluation_reports.py` passed.
- `.venv/bin/python -m pytest tests/test_evaluation_reports.py tests/test_app.py::test_literature_to_ideas_workflow_runs_full_pipeline tests/test_app.py::test_async_literature_to_ideas_workflow_completes_job_trace tests/test_app.py::test_job_cancel_and_retry_controls` passed: `10 passed`.
- `.venv/bin/python -m pytest tests/test_evaluation_reports.py tests/test_sota_signoff_and_benchmark.py tests/test_app.py::test_literature_to_ideas_workflow_runs_full_pipeline tests/test_app.py::test_async_literature_to_ideas_workflow_completes_job_trace tests/test_app.py::test_async_literature_to_ideas_workflow_can_run_from_local_worker tests/test_app.py::test_job_cancel_and_retry_controls` passed: `23 passed`.
- `bash scripts/check_workflow_job_controls.sh` passed: `9 passed`.
- `bash scripts/check_local_safe_suite.sh` passed, including focused coverage, local readiness, project skills, operational preflight, backup/restore contracts, workflow primitives, workflow job controls, local geolocalization benchmark smoke, and context-search/evaluation checks.
- `.venv/bin/python scripts/run_workflow_worker.py --once` passed with an idle empty-queue result.
- `env ALLOW_REAL_MODEL_PROVIDER_SMOKE=1 .venv/bin/python scripts/smoke_model_providers.py` confirmed embedding quota exhaustion and successful main/extraction/judge/rerank checks.

## 2026-06-27 - Real Paper Evaluation Runner Hardening

Implementation completed:

- Hardened `scripts/evaluate_real_papers.py` for real-PDF, real-provider evaluation by adding workflow timeout configuration, job-artifact recovery, step-level deep-quality progress logging, and deep-quality warning metrics.
- Disabled workflow-internal novelty checks by default for the real evaluator so uncontrolled external literature calls do not block the core literature-to-ideas run; the operator can still opt in with `--run-workflow-novelty-check`.
- Switched the real evaluator's related-work matrix step to a local service path with local hash embedding and disabled rerank, preserving persisted matrix artifacts while avoiding long model-provider calls in the deep quality loop.
- Added dependency injection to `RelatedWorkService` so production routes retain default retrieval behavior while scripts/tests can pass bounded retrieval services.
- Added structured idea title post-processing for model-generated ideas: generic or duplicate titles are rewritten from gap evidence, and geolocalization ideas now prefer distinct mechanisms across a workflow batch.
- Added regression coverage for recovered workflow-artifact summaries and duplicate/generic geolocalization title rewriting.

Real evaluation completed:

- Ran a full three-paper geolocalization evaluation on the local machine using the configured real provider stack.
- Final report: `outputs/evaluations/real_paper_eval_20260627_150056.json`.
- Final Markdown report: `outputs/evaluations/real_paper_eval_20260627_150056.md`.
- Completed papers: `3 / 3`.
- Generated gaps/ideas: `9 / 9`.
- Embedding model: `qwen3-vl-embedding`.
- Indexed evaluation objects: `42`.
- Context searches with evidence: `3 / 3` papers.
- Retrieval comparison coverage: `6 / 9` top-evidence overlap against the local hash/no-rerank baseline.
- Deep quality warnings: `0` across all three papers.
- Idea title diversity improved to `3 / 3` unique titles and `3 / 3` unique mechanisms for each evaluated paper.
- Two papers hit the 120-second workflow boundary and recovered from completed job artifacts, validating the recovery path without losing downstream quality-loop artifacts.

Verification completed:

- `.venv/bin/ruff check backend/research/services/structured_idea_service.py tests/test_structured_idea_service.py` passed.
- `.venv/bin/ruff check backend/research/services/structured_idea_service.py tests/test_structured_idea_service.py backend/research/services/related_work_service.py scripts/evaluate_real_papers.py tests/test_evaluation_reports.py` passed.
- `.venv/bin/ruff format --check backend/research/services/related_work_service.py backend/research/services/structured_idea_service.py scripts/evaluate_real_papers.py tests/test_evaluation_reports.py tests/test_structured_idea_service.py` passed.
- `.venv/bin/python -m pytest tests/test_structured_idea_service.py` passed: `2 passed`.
- `.venv/bin/python -m pytest tests/test_structured_idea_service.py tests/test_evaluation_reports.py` passed: `7 passed`.
- `.venv/bin/python -m pytest tests/test_evaluation_reports.py tests/test_app.py::test_literature_to_ideas_workflow_runs_full_pipeline tests/test_app.py::test_async_literature_to_ideas_workflow_completes_job_trace tests/test_app.py::test_job_cancel_and_retry_controls` passed: `8 passed`.
- `.venv/bin/python -m pytest tests/test_structured_idea_service.py tests/test_evaluation_reports.py tests/test_app.py::test_literature_to_ideas_workflow_runs_full_pipeline tests/test_app.py::test_async_literature_to_ideas_workflow_completes_job_trace tests/test_app.py::test_job_cancel_and_retry_controls` passed: `10 passed`.

## 2026-06-27 - Automatic Advisor Context-Miss Replay Capture

Implementation completed:

- Added automatic `context_search_miss` replay-case capture for Advisor chat when an evidence-seeking question executes `search_research_context` but returns no evidence.
- Stored the Advisor source run, retrieval query, paper filter, expected minimum evidence count, observed zero-evidence result, tool plan, and run metadata for replay.
- Added regression coverage with an intentionally unmatched paper filter to prove Advisor creates the replay case without failing the chat response.
- Wired the new test into `scripts/check_workflow_job_controls.sh`.
- Updated replay documentation, the agent strengthening plan, and TODO to describe the new automatic capture boundary.

Verification completed:

- `.venv/bin/ruff check backend/research/routes.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/research/routes.py tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_advisor_chat_captures_context_search_miss_replay_case` passed: `1 passed`.
- `bash scripts/check_workflow_job_controls.sh` passed: `8 passed`.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `bash scripts/check_script_catalog.sh` passed.
- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_local_safe_suite.sh` passed, including agent replay `4 passed`, project skill registry validation, local readiness, deployment/local doctor contracts `15 passed`, backup/restore manifest/rehearsal tests `6 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `8 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `42 passed`.

## 2026-06-27 - Automatic SOTA False-Positive Replay Capture

Implementation completed:

- Updated SOTA signoff creation to automatically persist a `sota_readiness_false_positive` replay case when a signoff is `sota_confirmed` but the manual gate is not ready for a SOTA claim.
- Stored expected replay gates for signoff status, ready-for-SOTA-claim, external-search completion, benchmark evidence readiness, nearest-work count, benchmark-run count, and blocker count.
- Stored observed manual-gate state so the case is immediately useful for local replay and audit.
- Added regression coverage to the benchmark/signoff flow proving the replay case is created for a confirmed-but-not-ready SOTA signoff.
- Updated replay documentation, the agent strengthening plan, and TODO to describe the automatic capture boundary.

Verification completed:

- `.venv/bin/ruff check backend/research/services/sota_review_service.py tests/test_sota_signoff_and_benchmark.py` passed.
- `.venv/bin/ruff format --check backend/research/services/sota_review_service.py tests/test_sota_signoff_and_benchmark.py` passed.
- `.venv/bin/pytest -q tests/test_sota_signoff_and_benchmark.py::test_benchmark_run_packet_can_anchor_sota_signoff` passed: `1 passed`.
- `bash scripts/check_context_search_evaluations.sh` passed: `42 passed`.
- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `bash scripts/check_local_safe_suite.sh` passed, including agent replay `4 passed`, project skill registry validation, local readiness, deployment/local doctor contracts `15 passed`, backup/restore manifest/rehearsal tests `6 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `7 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `42 passed`.

## 2026-06-27 - Replay Observability Metrics

Implementation completed:

- Extended `GET /research/agent/metrics` with replay-specific observability fields: case-type counts, `agent_replay` run status counts, live executor usage counts, and failed replay-run count.
- Updated the Markdown export to include replay case type counts, replay run status counts, and live executor counts.
- Added regression coverage that creates an `agent_replay` failed run plus `replay.sota_readiness_audit` tool call and verifies both JSON metrics and Markdown output.
- Updated replay documentation, TODO, and the technical design to describe the aggregate replay analytics boundary.

Verification completed:

- `.venv/bin/ruff check backend/research/schemas.py backend/research/routes.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/research/schemas.py backend/research/routes.py tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_agent_trace_records_run_tool_call_and_replay_case` passed: `1 passed`.
- `bash scripts/check_workflow_job_controls.sh` passed: `7 passed`.
- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `bash scripts/check_local_safe_suite.sh` passed, including agent replay `4 passed`, project skill registry validation, local readiness, deployment/local doctor contracts `15 passed`, backup/restore manifest/rehearsal tests `6 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `7 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `42 passed`.

## 2026-06-27 - SOTA Readiness Live Replay Executor

Implementation completed:

- Added a local `sota_readiness_audit` live replay executor for `sota_readiness`, `sota_readiness_false_positive`, and `sota_signoff_audit` replay cases.
- Audited local `sota_signoff_record` briefs for signoff status, manual gate readiness, external-search completion, nearest-work count, benchmark-run count, benchmark evidence readiness, and blockers.
- Added expectations for signoff status, ready-for-SOTA-claim, effective external-search completion, benchmark evidence readiness, nearest-work count, benchmark-run count, blocker count, and required/forbidden blockers.
- Updated `--record-run` tool summaries so `replay.sota_readiness_audit` records signoff status, readiness, blocker count, nearest-work count, and benchmark-run count.
- Added a regression test that creates a deliberate SOTA false positive where `signoff_status=sota_confirmed` but manual gate readiness is false; replay now fails it and records the failed replay run.
- Updated replay documentation, the agent strengthening plan, TODO, and README to describe SOTA-readiness live replay.

Verification completed:

- `.venv/bin/ruff check scripts/replay_agent_case.py tests/test_agent_replay_script.py` passed.
- `.venv/bin/pytest -q tests/test_agent_replay_script.py` passed: `4 passed`.
- `bash scripts/check_agent_replay.sh` passed: `4 passed`.
- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `bash scripts/check_context_search_evaluations.sh` passed: `42 passed`.
- `bash scripts/check_local_safe_suite.sh` passed, including agent replay `4 passed`, project skill registry validation, local readiness, deployment/local doctor contracts `15 passed`, backup/restore manifest/rehearsal tests `6 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `7 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `42 passed`.

## 2026-06-27 - Citation Audit Live Replay Executor

Implementation completed:

- Added a local `citation_audit` live replay executor for `citation_audit`, `citation_mismatch`, and `missing_citation` replay cases.
- Audited observed `cited_evidence_ids` against local `Evidence` rows, optional expected `paper_ids`, and optional `required_citation_terms`.
- Added expectations for required/forbidden cited evidence ids, minimum citation count, maximum missing citation count, maximum wrong-paper citation count, and maximum citation term misses.
- Updated `--record-run` tool summaries so `replay.citation_audit` records cited/found/missing/wrong-paper/term-miss counts.
- Added a fixture-backed regression test that persists paper/evidence/replay rows, runs citation audit with trace recording, and verifies replay pass plus `replay.citation_audit` trace output.
- Updated replay documentation, the agent strengthening plan, TODO, and README to describe citation live replay.

Verification completed:

- `.venv/bin/ruff check scripts/replay_agent_case.py tests/test_agent_replay_script.py` passed.
- `.venv/bin/ruff format --check scripts/replay_agent_case.py tests/test_agent_replay_script.py` passed.
- `.venv/bin/pytest -q tests/test_agent_replay_script.py` passed: `3 passed`.
- `bash scripts/check_agent_replay.sh` passed: `3 passed`.
- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `bash scripts/check_context_search_evaluations.sh` passed: `42 passed`.
- `bash scripts/check_local_safe_suite.sh` passed, including agent replay `3 passed`, project skill registry validation, local readiness, deployment/local doctor contracts `15 passed`, backup/restore manifest/rehearsal tests `6 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `7 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `42 passed`.

## 2026-06-27 - Replay Run Trace Recording

Implementation completed:

- Added opt-in `--record-run` support to `scripts/replay_agent_case.py`.
- Persisted replay invocations as `agent_replay` `AgentRun` rows with filter inputs, aggregate summary, per-case verdict rollups, latency, and local script metadata.
- Recorded live replay executors as `ToolCallRecord` rows, currently `replay.context_search`, including redacted arguments, result-count summaries, status, and replay verdict metadata.
- Kept trace recording disabled by default so ad hoc deterministic replay remains report-only.
- Extended the replay regression test to assert `agent_replay` and `replay.context_search` trace rows are created when `--record-run` is enabled.
- Updated replay documentation, the agent strengthening plan, TODO, and README to describe the new audit path.

Verification completed:

- `.venv/bin/ruff check scripts/replay_agent_case.py tests/test_agent_replay_script.py` passed.
- `.venv/bin/ruff format --check scripts/replay_agent_case.py tests/test_agent_replay_script.py` passed.
- `.venv/bin/pytest -q tests/test_agent_replay_script.py` passed: `2 passed`.
- `bash scripts/check_agent_replay.sh` passed: `2 passed`.
- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `bash scripts/check_local_safe_suite.sh` passed, including agent replay `2 passed`, project skill registry validation, local readiness, deployment/local doctor contracts `15 passed`, backup/restore manifest/rehearsal tests `6 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `7 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `42 passed`.

## 2026-06-27 - Context Search Live Replay Executor

Implementation completed:

- Added an opt-in `--live-executors` mode to `scripts/replay_agent_case.py`.
- Implemented a bounded local executor for `context_search` and `context_search_miss` replay cases that calls `RetrievalService.search_context` with forced local hash embedding and disabled external rerank.
- Added live replay expectations for required chunk/evidence/gap/idea ids, minimum result counts, and `live_status`.
- Preserved deterministic log-only replay as the default path and kept JSON/Markdown report generation intact.
- Added a fixture-backed regression test that creates temporary paper/chunk/evidence rows, replays a context-search miss, and verifies the expected local retrieval results without model-provider calls.
- Updated replay documentation, the agent strengthening plan, TODO, and README to describe the new boundary.

Verification completed:

- `.venv/bin/ruff check scripts/replay_agent_case.py tests/test_agent_replay_script.py` passed.
- `.venv/bin/pytest -q tests/test_agent_replay_script.py` passed: `2 passed`.
- `bash scripts/check_agent_replay.sh` passed: `2 passed`.
- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `bash scripts/check_context_search_evaluations.sh` passed: `42 passed`.
- `bash scripts/check_local_safe_suite.sh` passed, including agent replay `2 passed`, project skill registry validation, local readiness, deployment/local doctor contracts `15 passed`, backup/restore manifest/rehearsal tests `6 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `7 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `42 passed`.

## 2026-06-27 - Advisor Model Ranked Tool Selection

Implementation completed:

- Added `tool_selection_mode` to Advisor requests with safe default `deterministic` and opt-in `model_ranked`.
- Added candidate-validated main-model ranking for Advisor read tools, including model rationales, selected/skipped tool-plan output, invalid-tool filtering, max-tool-call enforcement, and deterministic fallback when the model client is unavailable or returns invalid output.
- Kept Advisor tool execution read-only and bounded; successful and failed tool calls continue to write trace records and failed read tools still create replay cases.
- Added a no-network test using a fake model-ranked selector and wired it into the workflow/job focused check.
- Updated the agent strengthening plan, TODO, and model-provider strategy to describe the new boundary.

Verification completed:

- `.venv/bin/pytest -q tests/test_app.py::test_advisor_chat_records_agent_trace_tool_calls tests/test_app.py::test_advisor_chat_records_failed_tool_call_and_replay_case tests/test_app.py::test_advisor_chat_uses_model_ranked_read_tool_selection` passed: `3 passed`.
- `bash scripts/check_workflow_job_controls.sh` passed: `7 passed`.
- `bash scripts/check_agent_replay.sh` passed: `1 passed`.
- `bash scripts/check_tool_bridge_contracts.sh` passed: `12 passed`.
- `bash scripts/check_local_safe_suite.sh` passed, including agent replay `1 passed`, project skill registry validation, local readiness, deployment/local doctor contracts `15 passed`, backup/restore manifest/rehearsal tests `6 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `7 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `42 passed`.

## 2026-06-27 - Advisor Failed Tool Replay Capture

Implementation completed:

- Wrapped Advisor read-tool execution so failed tools are recorded as failed `ToolCallRecord` rows with arguments, error, latency, selected/skipped tool-plan context, and no side effects.
- Added automatic `advisor_tool_failure` replay-case creation with expected/observed tool state whenever an Advisor read tool fails.
- Preserved existing Advisor response behavior for successful calls and kept failed requests marked as failed `AgentRun` rows with actual recorded tool-call count.
- Updated the agent strengthening plan and TODO to reflect that failed-tool capture is now implemented; model-ranked tool selection and richer replay executors remain future work.

Verification completed:

- `.venv/bin/pytest -q tests/test_app.py::test_advisor_chat_records_agent_trace_tool_calls tests/test_app.py::test_advisor_chat_records_failed_tool_call_and_replay_case` passed: `2 passed`.
- `bash scripts/check_workflow_job_controls.sh` passed: `6 passed`.
- `bash scripts/check_agent_replay.sh` passed: `1 passed`.
- `bash scripts/check_tool_bridge_contracts.sh` passed: `12 passed`.
- `bash scripts/check_local_safe_suite.sh` passed, including agent replay `1 passed`, project skill registry validation, local readiness, deployment/local doctor contracts `15 passed`, backup/restore manifest/rehearsal tests `6 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `6 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `42 passed`.

## 2026-06-27 - Single User Docker Static Check

Implementation completed:

- Added `scripts/check_single_user_docker_deployment.py` as a no-Docker-start static contract check for Dockerfile, docker-compose, dockerignore, `.env.example`, and deployment documentation.
- Added regression tests for the passing repository contract, missing-token failure reporting, and project-local JSON/Markdown report output.
- Wired the check into deployment focused contracts and documented it in README, local isolation, deployment notes, documentation index, and TODO.

Verification completed:

- `.venv/bin/pytest -q tests/test_single_user_docker_deployment.py` passed: `3 passed`.
- `python3 scripts/check_single_user_docker_deployment.py --json` passed on the local checkout with all 5 static contract checks passing.
- `bash scripts/check_deployment_contracts.sh` passed: `15 passed`.
- `bash scripts/check_local_safe_suite.sh` passed, including agent replay `1 passed`, project skill registry validation, local readiness, deployment/local doctor contracts `15 passed`, backup/restore manifest/rehearsal tests `6 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `5 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `42 passed`.

## 2026-06-27 - Synthetic Backup Restore Rehearsal

Implementation completed:

- Added `scripts/rehearse_local_backup_restore.py` to run a synthetic-only local backup/restore rehearsal with archive creation, temporary restore, aggregate manifest comparison, and secret-exclusion checks.
- Added regression tests covering successful synthetic rehearsal, project-local JSON/Markdown reports, and rejection of report paths outside the project root.
- Wired the rehearsal into backup/restore focused contracts and documented it in README, local isolation, deployment notes, documentation index, and TODO.

Verification completed:

- `.venv/bin/pytest -q tests/test_local_backup_restore_rehearsal.py` passed: `3 passed`.
- `python3 scripts/rehearse_local_backup_restore.py --json` passed on the local checkout with synthetic-only mode, matching source/restored manifests, `.env` excluded, and no secret-copy violations.
- `bash scripts/check_backup_restore_contracts.sh` passed: manifest/rehearsal tests `6 passed` plus backup/restore contract validation.
- `bash scripts/check_local_safe_suite.sh` passed, including agent replay `1 passed`, project skill registry validation, local readiness, deployment/local doctor contracts `12 passed`, backup/restore manifest/rehearsal tests `6 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `5 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `42 passed`.

## 2026-06-27 - SQLite Maintenance Report

Implementation completed:

- Added `scripts/check_sqlite_maintenance.py` as a read-only aggregate SQLite maintenance report for database size, WAL/SHM sidecars, table counts, `research_embeddings` owner/model counts, agent trace counts, and `PRAGMA quick_check`.
- Guarded the script so databases outside the project root are not inspected unless the operator explicitly passes `--allow-outside-project`.
- Wired the report into `scripts/check_local_doctor.sh`, deployment-focused tests, README, local isolation, deployment notes, vector-store strategy, documentation index, and TODO.

Verification completed:

- `.venv/bin/pytest -q tests/test_sqlite_maintenance.py tests/test_local_doctor.py` passed: `6 passed`.
- `python3 scripts/check_sqlite_maintenance.py --json` passed on the local checkout with quick-check `ok`, project-local SQLite storage, and aggregate-only output.
- `bash scripts/check_local_doctor.sh` passed with the new SQLite maintenance section and without printing `.env` values.
- `bash scripts/check_local_safe_suite.sh` passed, including agent replay `1 passed`, project skill registry validation, local readiness, deployment/local doctor contracts `12 passed`, backup/restore manifest tests `3 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `5 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `42 passed`.

## 2026-06-27 - Agent Observability Markdown Export

Implementation completed:

- Added `GET /research/agent/metrics/export/markdown` to export the existing agent observability metrics as a local Markdown report.
- Exposed `export_agent_observability_metrics_markdown` in the tool manifest and covered it in the manifest/trace regression tests.
- Updated README, replay evaluation docs, and technical design to document the report boundary.

Verification completed:

- `.venv/bin/pytest -q tests/test_app.py::test_agent_trace_records_run_tool_call_and_replay_case tests/test_app.py::test_tool_manifest_lists_mcp_ready_research_tools` passed: `2 passed`.
- `bash scripts/check_tool_bridge_contracts.sh` passed: `12 passed`.
- `bash scripts/check_workflow_job_controls.sh` passed: `5 passed`.
- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `git diff --check` passed.
- `bash scripts/check_local_safe_suite.sh` passed, including agent replay `1 passed`, project skill registry validation, local readiness, deployment/local doctor contracts `8 passed`, backup/restore manifest tests `3 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `5 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `42 passed`.

## 2026-06-27 - Agent Observability Metrics

Implementation completed:

- Added `GET /research/agent/metrics` to summarize local `AgentRun`, `ToolCallRecord`, and `ReplayCase` observability state.
- Metrics include run counts by status/type, average run latency, tool-call counts by status/name, tool success rate, replay verdict distribution, replay pass rate, and recent failed run/tool summaries.
- Exposed `get_agent_observability_metrics` in the tool manifest and `agent_observability_metrics` in runtime status capabilities.
- Added regression coverage to the agent trace test and updated README, replay docs, technical design, and the agent-engineering strengthening plan.

Verification completed:

- `.venv/bin/pytest -q tests/test_app.py::test_agent_trace_records_run_tool_call_and_replay_case tests/test_app.py::test_tool_manifest_lists_mcp_ready_research_tools tests/test_app.py::test_research_status` passed: `3 passed`.
- `bash scripts/check_workflow_job_controls.sh` passed: `5 passed`.
- `bash scripts/check_tool_bridge_contracts.sh` passed: `12 passed`.
- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `git diff --check` passed.
- `bash scripts/check_local_safe_suite.sh` passed, including agent replay `1 passed`, project skill registry validation, local readiness, deployment/local doctor contracts `8 passed`, backup/restore manifest tests `3 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `5 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `42 passed`.

## 2026-06-27 - Bounded Advisor Read Tool Plan

Implementation completed:

- Added `max_tool_calls` to Advisor chat requests and implemented a bounded deterministic read-tool planner.
- The Advisor now selects from approved read tools: `get_project_cockpit`, `search_research_context`, `get_idea_progress`, `get_idea_lineage`, and `list_research_tasks`.
- Added selected/skipped tool plan metadata and compact observations to `source_summaries.tool_plan`.
- Preserved the existing Advisor response contract while expanding traceable tool calls beyond cockpit/context reads.
- Updated README, TODO, technical design, project skill docs, and the agent-engineering strengthening plan to mark bounded read-first tool calling as the current baseline.

Verification completed:

- `.venv/bin/pytest -q tests/test_app.py::test_advisor_chat_records_agent_trace_tool_calls tests/test_app.py::test_tool_manifest_lists_mcp_ready_research_tools tests/test_app.py::test_research_status` passed: `3 passed`.
- `bash scripts/check_workflow_job_controls.sh` passed: `5 passed`.
- `bash scripts/check_project_skills.sh` passed.
- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `git diff --check` passed.
- `bash scripts/check_local_safe_suite.sh` passed, including agent replay `1 passed`, project skill registry validation, local readiness, deployment/local doctor contracts `8 passed`, backup/restore manifest tests `3 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `5 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `42 passed`.

## 2026-06-27 - LangGraph Advisor Deep Review

Implementation completed:

- Added `POST /research/agent/advisor-deep-review` as an opt-in LangGraph workflow with `load_state`, `retrieve_context`, `verify_evidence`, and `compose_answer` nodes.
- The workflow creates an `advisor_deep_review` `AgentRun`, records cockpit/context read calls as `ToolCallRecord` rows, and returns an Advisor-compatible answer plus verification flags.
- Added `AdvisorDeepReviewRequest` and `AdvisorDeepReviewResponse` schemas without changing the existing Advisor chat or literature-to-ideas response contracts.
- Exposed `run_advisor_deep_review` in the tool manifest and `langgraph_advisor_deep_review` in runtime status capabilities.
- Extended focused Advisor trace coverage to verify LangGraph nodes, trace output, tool-call records, and source-run status.
- Updated README, TODO, the technical design, and the agent-engineering strengthening plan to make the LangGraph workflow boundary explicit.

Verification completed:

- `.venv/bin/pytest -q tests/test_app.py::test_research_status tests/test_app.py::test_tool_manifest_lists_mcp_ready_research_tools tests/test_app.py::test_advisor_chat_records_agent_trace_tool_calls` passed: `3 passed`.
- `bash scripts/check_workflow_job_controls.sh` passed: `5 passed`.
- `bash scripts/check_tool_bridge_contracts.sh` passed: `12 passed`.
- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `git diff --check` passed.
- `bash scripts/check_local_safe_suite.sh` passed, including agent replay `1 passed`, project skill registry validation, local readiness, deployment/local doctor contracts `8 passed`, backup/restore manifest tests `3 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `5 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `42 passed`.

## 2026-06-27 - Agent Replay Evaluation

Implementation completed:

- Added `scripts/replay_agent_case.py` as the first deterministic local bad-case replay evaluator over saved `ReplayCase`, `AgentRun`, and `ToolCallRecord` rows.
- Added JSON and Markdown report output with pass/fail/needs-review counts, pass rate, reasons, source run ids, and observed tool names.
- Added secret-shaped value redaction to replay output and kept the first replay path read-only: no model calls, no tool execution, and no live workflow mutation.
- Added `tests/test_agent_replay_script.py` with a temporary SQLite fixture that creates an agent run, tool call, replay case, and Markdown report.
- Added `scripts/check_agent_replay.sh` and wired it into the default safe suite contract.
- Added `docs/agent_replay_eval.md` and updated README, TODO, documentation index, and the agent-engineering strengthening plan.

Verification completed:

- `bash scripts/check_agent_replay.sh` passed.
- `bash scripts/check_suite_contracts.sh` passed.
- `bash scripts/check_script_catalog.sh` passed.
- `bash scripts/check_handoff_docs.sh` passed.
- `git diff --check` passed.
- `bash scripts/check_local_safe_suite.sh` passed, including agent replay `1 passed`, project skill registry validation, local readiness, deployment/local doctor contracts `8 passed`, backup/restore manifest tests `3 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `5 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `42 passed`.

## 2026-06-27 - Project Skill Registry

Implementation completed:

- Added six project-local skills under `skills/*/SKILL.md`: `paper-ingestion`, `hybrid-context-search`, `literature-to-ideas`, `sota-review`, `benchmark-evaluation`, and `advisor-action-session`.
- Added `docs/project_skill_registry.md` as the registry map for local operators and future agents.
- Added `scripts/check_project_skills.sh` to validate required skill files, frontmatter names/descriptions, required instruction sections, registry links, and placeholder-free content.
- Wired the project skill check into the default safe suite contract and README script catalog.
- Updated TODO and the agent-engineering strengthening plan to mark the first skill registry slice as complete.

Verification completed:

- `bash scripts/check_project_skills.sh` passed.
- `python3 /Users/zwz/.codex/skills/.system/skill-creator/scripts/quick_validate.py <skill-dir>` passed for all six skill directories.
- `bash scripts/check_suite_contracts.sh` passed.
- `bash scripts/check_script_catalog.sh` passed.
- `bash scripts/check_handoff_docs.sh` passed.
- `git diff --check` passed.
- `bash scripts/check_local_safe_suite.sh` passed, including project skill registry validation, local readiness, deployment/local doctor contracts `8 passed`, backup/restore manifest tests `3 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `5 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `42 passed`.

## 2026-06-27 - Advisor Chat Trace Wiring

Implementation completed:

- Wired `/research/advisor/chat` into `AgentTraceService` so each successful Advisor chat creates an `advisor_chat` `AgentRun`.
- Recorded the deterministic cockpit read and context-search read as `ToolCallRecord` rows, including bounded argument summaries, result summaries, status, side-effect policy, and trace metadata.
- Added `agent_run_id` to `AdvisorChatResponse` so Workbench, API clients, replay tooling, and MCP bridge consumers can inspect the exact trace behind an answer.
- Added `AgentTraceService.finish_run` so agent runs can transition from `running` to `completed` or `failed` with redacted output/error metadata.
- Added focused regression coverage for Advisor trace creation without coupling the new trace behavior to the long delivery-loop test.
- Updated README, TODO, and the agent-engineering strengthening plan to mark Advisor trace wiring as implemented while keeping bounded LLM tool selection as the next step.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/schemas.py backend/research/services/agent_trace_service.py backend/research/routes.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/schemas.py backend/research/services/agent_trace_service.py backend/research/routes.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_agent_trace_records_run_tool_call_and_replay_case tests/test_app.py::test_advisor_chat_records_agent_trace_tool_calls` passed: `2 passed`.
- `bash scripts/check_workflow_job_controls.sh` passed: `5 passed`.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_tool_bridge_contracts.sh` passed: `12 passed`.
- `bash scripts/check_research_planning_contracts.sh` passed: `3 passed`.
- `git diff --check` passed.
- `bash scripts/check_local_safe_suite.sh` passed, including local readiness, deployment/local doctor contracts `8 passed`, backup/restore manifest tests `3 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `5 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `42 passed`.

## 2026-06-27 - Agent Trace Foundation

Implementation completed:

- Added `AgentRun`, `ToolCallRecord`, and `ReplayCase` persistence models as the trace foundation for future Advisor tool calling, replay, and LangGraph workflows.
- Added `AgentTraceService` with bounded listing, run/tool/replay creation, and secret redaction for sensitive keys and provider-token-shaped values.
- Added create/read APIs under `/research/agent/runs`, `/research/agent/runs/{run_id}/tool-calls`, and `/research/agent/replay-cases`.
- Exposed read-only trace inspection tools through the tool manifest and MCP bridge spec while keeping trace creation out of the MCP tool manifest for now.
- Updated README, TODO, and the agent engineering strengthening plan to mark trace persistence as the first completed roadmap slice.

Verification completed:

- `.venv/bin/pytest -q tests/test_app.py::test_agent_trace_records_run_tool_call_and_replay_case tests/test_app.py::test_tool_manifest_lists_mcp_ready_research_tools tests/test_app.py::test_tool_bridge_spec_maps_manifest_to_http_tool_schemas tests/test_app.py::test_job_cancel_and_retry_controls` passed: `4 passed`.
- `bash scripts/check_workflow_job_controls.sh` passed: `4 passed`.
- `bash scripts/check_tool_bridge_contracts.sh` passed: `12 passed`.
- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `bash scripts/check_deployment_contracts.sh` passed: `8 passed`.
- `git diff --check` passed.
- `bash scripts/check_local_safe_suite.sh` passed, including local readiness, deployment/local doctor contracts `8 passed`, backup/restore manifest tests `3 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `4 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `42 passed`.

## 2026-06-27 - Agent Engineering Strengthening Plan

Documentation completed:

- Added `docs/agent_engineering_strengthening_plan.md` as the roadmap for trace tables, Advisor tool calling, project-local skills, bad-case replay, one isolated LangGraph workflow, guardrails, case memory, observability, and personal local deployment polish.
- Documented that the stable FastAPI/service-layer workflow should remain intact while LangGraph is introduced only for an opt-in workflow that benefits from explicit DAG state.
- Updated README, documentation index, and TODO so future work can start from the agent-engineering strengthening plan instead of chat history.

Verification completed:

- `bash scripts/check_handoff_docs.sh` passed.
- `git diff --check` passed.

## 2026-06-26 - Hybrid Chunk And Artifact Retrieval

Implementation completed:

- Combining traditional chunk-level RAG with the existing artifact-level research retrieval contract.
- Extending the local SQLite `ResearchEmbedding.vector_json` baseline so source chunks, evidence, gaps, and ideas share the same clone-to-run embedding path.
- Adding context-search API results for source chunks while keeping evidence, gap, idea, and GraphRAG-lite response fields backward compatible.
- Adding deterministic chunk vector-rescue and paper-filter checks to the focused context-search evaluation suite.

Verification completed:

- `.venv/bin/pytest -q tests/test_app.py::test_context_search_chunk_vector_hit_rescues_lexical_miss tests/test_app.py::test_context_search_paper_filter_evaluation_fixture tests/test_app.py::test_context_search_graph_context_respects_paper_filter tests/test_app.py::test_context_search_returns_evidence_and_graph_context` passed: `4 passed`.
- `bash scripts/check_context_search_evaluations.sh` passed: `42 passed`.
- `git diff --check` passed.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_local_safe_suite.sh` passed, including local readiness, deployment/local doctor contracts `8 passed`, backup/restore manifest tests `3 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `3 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `42 passed`.

## 2026-06-26 - Vector Store Strategy

Documentation completed:

- Added `docs/vector_store_strategy.md` to clarify that the current personal local-agent target does not require Milvus, Qdrant, pgvector, or another external vector database.
- Documented the current SQLite `ResearchEmbedding.vector_json` baseline, deterministic local hash embeddings, optional external embedding provider, optional rerank provider, and migration triggers for a dedicated vector store.
- Updated README, documentation index, model-provider strategy, and local distribution docs so future work does not accidentally treat Milvus as a required clone-to-run dependency.

Verification completed:

- `bash scripts/check_handoff_docs.sh` passed.
- `git diff --check` passed.
- `bash scripts/check_local_agent_readiness.sh` passed.

## 2026-06-26 - Benchmark Readiness Blocks SOTA Claim Readiness

Implementation completed:

- Tightened SOTA signoff manual gates so `confirmed_novel` records with incomplete benchmark evidence add `benchmark_evidence_not_ready`.
- `ready_for_sota_claim` now requires both `signoff_status == "sota_confirmed"` and no manual-gate blockers, so a human signoff can be saved while publication-grade claim readiness remains blocked until benchmark readiness has a completed run and comparison brief.
- Added regression coverage for both sides: complete benchmark comparison evidence keeps ready-for-claim true, while missing comparison evidence blocks ready-for-claim.
- Updated README and the technical design note for the stricter SOTA claim boundary.

Verification completed:

- `.venv/bin/pytest -q tests/test_sota_signoff_and_benchmark.py::test_benchmark_run_comparison_persists_brief tests/test_sota_signoff_and_benchmark.py::test_benchmark_run_packet_can_anchor_sota_signoff tests/test_sota_signoff_and_benchmark.py::test_sota_external_search_evidence_records_provider_completion` passed: `3 passed`.
- `bash scripts/check_context_search_evaluations.sh` passed: `41 passed in 9.97s`.
- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `git diff --check` passed.
- `bash scripts/check_local_safe_suite.sh` passed, including local readiness, deployment/local doctor contracts `8 passed`, backup/restore manifest tests `3 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `3 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `41 passed`.

## 2026-06-26 - Local Doctor Entrypoint

Implementation completed:

- Added `scripts/check_local_doctor.sh` as a combined local diagnostics entrypoint.
- The doctor runs local readiness, model-provider config, aggregate backup manifest, and geolocalization benchmark readiness checks without starting a service or printing secrets.
- Added `--inspect-only` to `scripts/prepare_local_geoloc_benchmark.py` so read-only diagnostics can inspect missing benchmark files without creating directories.
- Wired the doctor into README, documentation index, development process, local distribution flow, local readiness contracts, and focused deployment checks.

Verification completed:

- `bash -n scripts/check_local_doctor.sh scripts/check_deployment_contracts.sh` passed.
- `bash scripts/check_script_catalog.sh` passed.
- `bash scripts/check_deployment_contracts.sh` passed: `8 passed in 0.88s`.
- `.venv/bin/pytest -q tests/test_sota_signoff_and_benchmark.py::test_prepare_local_geoloc_benchmark_inspect_only_does_not_create_dirs` passed.
- `bash scripts/check_context_search_evaluations.sh` passed: `41 passed in 9.96s`.
- `bash scripts/check_local_agent_readiness.sh` passed.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_generated_file_guard.sh` passed.
- `bash scripts/check_local_safe_suite.sh` passed, including local readiness, deployment/local doctor contracts `8 passed`, backup/restore manifest tests `3 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `3 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `41 passed`.

## 2026-06-26 - Local Backup Manifest

Implementation completed:

- Added `scripts/build_local_backup_manifest.py` as a read-only aggregate manifest builder for local backup planning.
- The manifest covers `data/research`, `data/papers`, `data/audit`, `data/benchmarks`, `outputs`, and `configs/benchmark_profiles.json`; it reports file counts and byte totals without listing private paper filenames or reading file contents.
- The manifest detects secret-like files such as `.env` and reports that they are excluded, without reading or printing secret values.
- Wired the helper into backup/restore contracts, local readiness documentation, deployment notes, local isolation, and the local distribution flow.

Verification completed:

- `.venv/bin/pytest -q tests/test_local_backup_manifest.py` passed: `3 passed`.
- `python3 scripts/build_local_backup_manifest.py --json` passed on the local checkout and reported aggregate counts only.
- `bash scripts/check_backup_restore_contracts.sh` passed: manifest tests `3 passed` plus backup/restore contract validation.
- `bash scripts/check_local_agent_readiness.sh` passed.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_generated_file_guard.sh` passed.
- `bash scripts/check_local_safe_suite.sh` passed, including local readiness, deployment contracts `6 passed`, backup/restore manifest tests `3 passed`, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `3 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `40 passed`.

## 2026-06-26 - Model Provider Config Doctor

Implementation completed:

- Added `scripts/check_model_provider_config.py` as a no-network model-provider readiness doctor for the current shell environment.
- The doctor checks main, extraction, judge, embedding, and rerank roles by variable presence only, reports variable names and missing groups, supports `--require-real`, and does not print API key values.
- Wired the doctor into deployment contract checks and local readiness documentation.

Verification completed:

- `.venv/bin/pytest -q tests/test_model_provider_config.py` passed: `3 passed`.
- `python3 scripts/check_model_provider_config.py --json` passed and reported fallback-ready status without printing key values.
- `bash scripts/check_deployment_contracts.sh` passed: `6 passed in 0.80s`.
- `bash scripts/check_local_agent_readiness.sh` passed.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_secret_file_guard.sh` passed.
- `bash scripts/check_local_safe_suite.sh` passed, including local readiness, deployment contracts `6 passed`, backup/restore contracts, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `3 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `40 passed`.

## 2026-06-26 - Local Geolocalization Benchmark Smoke

Implementation completed:

- Added `scripts/check_local_geoloc_benchmark_smoke.sh` as a standalone local benchmark smoke for the geolocalization JSONL scoring harness.
- Added `scripts/prepare_local_geoloc_benchmark.py` to prepare project-local benchmark directories, optionally write ignored example JSONL files and `configs/benchmark_profiles.json`, validate record schema, and report runnable state without reading `.env`.
- The smoke writes temporary ground-truth and prediction JSONL fixtures under project-local `outputs/`, runs `scripts/benchmark_geoloc_predictions.py`, verifies country accuracy, baseline improvement, missing-prediction accounting, and mean/median geodesic-distance metrics, then removes its temporary fixture directory.
- Wired the smoke into `scripts/check_context_search_evaluations.sh` so benchmark scoring regressions are covered by the focused evaluation suite.
- Documented the smoke and preparation helper in README, TODO, development process, documentation index, and local personal-agent distribution flow.

Verification completed:

- `bash -n scripts/check_local_geoloc_benchmark_smoke.sh scripts/check_context_search_evaluations.sh` passed.
- `bash scripts/check_local_geoloc_benchmark_smoke.sh` passed.
- `bash scripts/check_script_catalog.sh` passed.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `.venv/bin/pytest -q tests/test_sota_signoff_and_benchmark.py::test_prepare_local_geoloc_benchmark_writes_example_profile tests/test_sota_signoff_and_benchmark.py::test_prepare_local_geoloc_benchmark_reports_missing_files` passed: `2 passed`.
- `bash scripts/check_context_search_evaluations.sh` passed: `40 passed in 9.07s`.
- `bash scripts/check_local_safe_suite.sh` passed, including local readiness, deployment contracts `3 passed`, backup/restore contracts, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `3 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `40 passed`.

## 2026-06-26 - Local Agent Readiness Preflight

Implementation completed:

- Added `scripts/check_local_agent_readiness.sh` as a read-only clone-to-run readiness check for the personal local-agent target.
- The check verifies required local deployment files, ignored local artifacts, `.env.example` placeholder coverage, project-local cache/data/model/output/log paths, setup/run scripts, local Python version when `.venv` exists, and benchmark profile override handling.
- The check reports whether `.env` exists but does not read `.env` values.
- Wired the check into README, TODO, documentation index, local distribution flow, suite contracts, and the default local safe suite.
- Added `test_local_agent_readiness_contract` to keep README, env template, local isolation exports, setup/run scripts, and safe-suite wiring aligned.
- Added the benchmark profile readiness route test to `scripts/check_context_search_evaluations.sh` so focused coverage no longer misses it.
- Updated backup/restore and database migration contract wording from historical customer-pilot language to local deployment language.
- Isolated benchmark-runner and structured-extraction fallback tests from local `.env` and shell model-provider settings so the suite remains stable when the personal checkout has real provider keys configured.

Verification completed:

- `bash scripts/check_local_agent_readiness.sh` passed.
- `bash scripts/check_script_catalog.sh` passed.
- `bash scripts/check_suite_contracts.sh` passed.
- `bash scripts/check_deployment_contracts.sh` passed: `2 passed in 1.52s`.
- `bash scripts/check_generated_file_guard.sh` passed.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `bash scripts/check_context_search_evaluations.sh` passed: `37 passed in 6.63s`.
- `bash scripts/check_backup_restore_contracts.sh` passed.
- `bash scripts/check_research_workflow_primitives.sh` passed: `54 passed in 5.58s`.
- `bash scripts/check_remote_safe_suite.sh` passed, including local readiness, deployment contracts `2 passed`, backup/restore contracts, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `3 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `37 passed`.
- `git diff --check` passed.

## 2026-06-26 - Workbench Local Operator Copy

Implementation completed:

- Updated visible Workbench first-run navigation and setup copy from historical customer-pilot wording to local personal-agent wording.
- Changed visible labels to `Local Path`, `Local Launch`, `Status Report`, and `Save Status Report` while preserving DOM ids, CSS classes, and `/research/pilot/*` API compatibility.
- Updated Workbench default setup name and constraints to local deployment wording.
- Updated Workbench-generated release recipient defaults from `advisor_or_customer` to `advisor_or_reviewer`.

Verification completed:

- `bash scripts/check_pilot_readiness.sh` passed: `36 passed in 6.97s`.
- `bash scripts/check_deployment_contracts.sh` passed: `2 passed in 1.59s`.
- `git diff --check` passed.

## 2026-06-26 - Local Check Entrypoints

Implementation completed:

- Added `scripts/check_local_operational_preflight.sh` as the preferred local wrapper around the historical operational preflight.
- Added `LOCAL_PREFLIGHT_STRICT_GIT` as a local-name alias for strict git checks while preserving `PILOT_PREFLIGHT_STRICT_GIT` compatibility.
- Added `scripts/check_local_safe_suite.sh` as the preferred local wrapper around the historical safe focused suite.
- Updated the historical operational preflight completion hint so it points new users to `LOCAL_PREFLIGHT_STRICT_GIT` first while preserving the old variable.
- Updated README, development process, documentation index, local distribution flow, suite contracts, and deployment contract tests to prefer the `check_local_*` entrypoints while keeping old script names available for compatibility.

Verification completed:

- `bash -n scripts/check_local_operational_preflight.sh scripts/check_local_safe_suite.sh scripts/check_suite_contracts.sh` passed.
- `bash scripts/check_script_catalog.sh` passed.
- `bash scripts/check_suite_contracts.sh` passed.
- `bash scripts/check_local_operational_preflight.sh` passed with expected dirty-worktree warnings for this in-progress change; it did not read `.env` values.
- `bash scripts/check_deployment_contracts.sh` passed: `2 passed in 1.55s`.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `bash scripts/check_local_safe_suite.sh` passed, including local readiness, deployment contracts `2 passed`, backup/restore contracts, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `3 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `37 passed`.

## 2026-06-26 - Local Runtime Smoke

Implementation completed:

- Added `scripts/check_local_runtime_smoke.sh` as an opt-in transient runtime smoke for personal local deployments.
- The smoke starts `./scripts/run-local.sh` on a configurable localhost port, waits for `/health`, verifies `/health/ready`, confirms Workbench HTML contains local operator copy, writes server logs under `logs/local-runtime-smoke.log`, and stops the server automatically.
- Documented the runtime smoke in README, development process, documentation index, and local distribution flow.
- Added deployment contract coverage for the runtime smoke script without adding it to the default safe suite, so routine checks do not start services.

Verification completed:

- `bash -n scripts/check_local_runtime_smoke.sh` passed.
- `bash scripts/check_script_catalog.sh` passed.
- `bash scripts/check_deployment_contracts.sh` passed: `3 passed in 1.54s`.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `PORT=8011 bash scripts/check_local_runtime_smoke.sh` passed with `Base URL: http://127.0.0.1:8011`.
- `bash scripts/check_local_safe_suite.sh` passed, including local readiness, deployment contracts `3 passed`, backup/restore contracts, workflow primitives `54 passed`, research planning `3 passed`, write audit `7 passed`, workflow job controls `3 passed`, tool bridge `12 passed`, GraphRAG-lite `4 passed`, and context search/evaluation `37 passed`.

## 2026-06-25 - Personal Local Agent Product Scope

Decision recorded:

- Locked the current product target to a personal, local-deployable research agent distributed by GitHub clone.
- Clarified that each operator owns their local `.env`, model provider keys, SQLite data, uploaded papers, benchmark files, generated outputs, logs, and caches.
- Marked multi-user accounts, tenant isolation, hosted SaaS operations, billing, SSO, central admin workflows, and remote-server workflow as out of scope for the current build.
- Added `docs/local_agent_distribution.md` as the clone-to-run and local distribution source of truth.
- Updated README, TODO, deployment, admin authorization, documentation index, development process, and user/project scoping docs to align with the local personal-agent target.
- Updated deployment contract tests and the local operational preflight script so their required tokens match the local deployment target.

Verification completed:

- `git diff --check` passed.
- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_secret_file_guard.sh` passed.
- `bash scripts/check_generated_file_guard.sh` passed.
- `bash scripts/check_deployment_contracts.sh` passed: `1 passed in 1.42s`.
- `bash scripts/check_pilot_operational_preflight.sh` passed with expected dirty-worktree warnings for this in-progress change; it did not read `.env` values.

## 2026-06-25 - Benchmark Evidence Task Generation

Implementation completed:

- Added benchmark evidence readiness follow-up task generation.
- Added `POST /research/ideas/{idea_id}/benchmark-evidence/readiness/tasks`.
- Added Workbench `Benchmark Tasks` to create task-board items from missing benchmark runs, missing comparison briefs, artifact gaps, regression warnings, or signoff handoff actions.
- Added duplicate protection so repeated clicks do not create duplicate open tasks for the same readiness action.

Production boundary:

- Task generation does not run benchmarks automatically; it turns benchmark readiness gaps into explicit execution work.

## 2026-06-25 - Benchmark Readiness In SOTA Signoff

Implementation completed:

- Added compact benchmark evidence readiness summaries to SOTA review packages.
- Added benchmark evidence readiness status, missing items, and warnings to SOTA signoff manual-gate summaries.
- Updated SOTA signoff Markdown so reviewers can see benchmark evidence readiness beside external-search and nearest-work gates.

Production boundary:

- Superseded on 2026-06-26: benchmark readiness now blocks `ready_for_sota_claim` through the manual gate when evidence is incomplete, while still saving the human signoff record.
- Publication-grade claims should still link completed benchmark runs, comparison briefs, external SOTA evidence, and reviewer notes explicitly.

## 2026-06-25 - Benchmark Evidence Readiness Gate

Implementation completed:

- Added `BenchmarkEvidenceService` to summarize an idea's completed benchmark runs and benchmark comparison briefs.
- Added `GET /research/ideas/{idea_id}/benchmark-evidence/readiness` with missing items, warnings, recommended actions, readiness status, and Markdown export.
- Added Workbench `Benchmark Gate` so a researcher can inspect whether benchmark evidence is ready before manual SOTA signoff.
- Added readiness coverage to benchmark comparison tests, status capability checks, tool manifest checks, and Workbench static checks.

Production boundary:

- Readiness is an evidence-completeness gate, not an automatic scientific approval.
- Human signoff and external SOTA evidence remain required before publication-grade claims.

## 2026-06-25 - Benchmark Run Comparison Briefs

Implementation completed:

- Added `BenchmarkRunComparisonService` to compare two `ExperimentRun` benchmark records for the same idea.
- Added `POST /research/experiment-runs/compare`, which computes per-metric baseline/candidate values, deltas, improvement flags, and a comparison status.
- Persisted comparison outputs as `ResearchBrief(scope="benchmark_run_comparison")` with Markdown export.
- Added Workbench `Compare Runs` to compare the latest two benchmark runs for the active experiment plan.
- Added tests for persisted comparison briefs and Workbench/tool-manifest discovery.

Production boundary:

- Comparisons are only as reliable as the underlying benchmark runs and artifacts.
- Publication-grade claims still need repeated runs, controlled seeds/splits, external SOTA evidence, and human signoff.

## 2026-06-25 - Benchmark Profiles And Geolocalization Harness

Implementation completed:

- Added `BENCHMARK_PROFILE_MANIFEST_PATH` with ignored local profile overrides at `configs/benchmark_profiles.json` and a committed example at `configs/benchmark_profiles.example.json`.
- Added built-in benchmark profiles for JSON metric smoke execution and geolocalization country-accuracy JSONL evaluation.
- Added `GET /research/benchmark-profiles` so Workbench, MCP-style clients, and operators can see runnable profiles, missing project-local data paths, and command templates before execution.
- Added `profile_id` support to benchmark command execution so profile defaults fill benchmark name, dataset, split, metric, command args, working directory, timeout, and config metadata.
- Added `scripts/benchmark_geoloc_predictions.py` to evaluate project-local ground truth/prediction JSON or JSONL files, emitting country accuracy plus optional mean/median geodesic-distance metrics.
- Updated Workbench `Benchmark Exec` to select a runnable profile instead of sending a hard-coded command.

Production boundary:

- Real benchmark data remains untracked under `data/benchmarks/`; predictions remain untracked under `outputs/predictions/`.
- The built-in geolocalization profile becomes runnable only after the expected ground-truth and prediction files exist.
- Scientific claims still require repeated measured runs, external SOTA evidence, and signoff review.

## 2026-06-25 - Local-Only Development Policy

Policy update completed:

- Updated `AGENTS.md` so the local clone plus GitHub `main` is the current development source of truth.
- Removed default remote SSH status checks from the local project operating rules.
- Replaced the top-level TODO with local development, local verification, and local product follow-up priorities.
- Updated README and development-process wording so historical `check_remote_*` script names are treated as local focused suites rather than instructions to contact a remote server.
- Updated `scripts/check_handoff_docs.sh` to enforce the new local-only handoff wording.

Verification completed:

- `bash scripts/check_secret_file_guard.sh` passed.
- `bash scripts/check_generated_file_guard.sh` passed.
- `git diff --check` passed before the handoff script update.

## 2026-06-25 - Guarded Benchmark Command Runner

Implementation completed:

- Added `BENCHMARK_RUNNER_*` local configuration with the runner disabled by default.
- Added `BenchmarkExecutionCreate` and `POST /research/experiment-plans/{plan_id}/benchmark-run/execute`.
- Added `BenchmarkCommandRunnerService`, which validates allowed commands, keeps working/output paths inside the project root, executes command-argument lists without a shell, captures stdout/stderr/command metadata/metrics, and saves artifacts under `outputs/benchmark-runs/`.
- Saved executed benchmark results as `ExperimentRun` records with `execution_kind=benchmark_command`, parsed metric results, artifact links, and Markdown export.
- Added Workbench `Benchmark Exec` control and readiness reporting under `/health/ready`.
- Added tests for disabled-by-default behavior and successful local command execution.

Production boundary:

- The runner is a controlled local execution hook, not a scheduler or sandbox.
- Real scientific claims still require a real dataset harness, captured artifacts, repeated runs, and SOTA signoff evidence.

## 2026-06-25 - SOTA Signoff And Benchmark Run Packets

Implementation completed:

- Added structured benchmark run packets at `POST /research/experiment-plans/{plan_id}/benchmark-run`, backed by `ExperimentRun` so dataset, split, baseline, primary metric, command, artifacts, dry-run mode, and reproducibility notes can be analyzed and exported through existing experiment workflows.
- Added SOTA external-search evidence packages at `POST /research/ideas/{idea_id}/sota-external-search-evidence`, backed by `ResearchBrief(scope="sota_external_search_evidence")`, so local/external provider statuses, result summaries, missing searches, and signoff readiness are persisted before final novelty review.
- Added manual SOTA signoff records at `POST /research/ideas/{idea_id}/sota-signoffs`, stored as `ResearchBrief(scope="sota_signoff_record")` with reviewer decision, external-search completion, nearest work, evidence links, linked benchmark runs, final novelty claim, limitations, and signoff blockers.
- Connected signoff records to `external_search_evidence_id`, so a completed saved search evidence package can satisfy effective external-search completion without relying only on a hand-entered boolean.
- Added list/detail/Markdown export endpoints for SOTA signoff records.
- Added list/detail/Markdown export endpoints for SOTA external-search evidence packages.
- Updated the tool manifest, status capabilities, Workbench buttons, README, documentation index, and focused evaluation script.
- Added an end-to-end regression test proving a real-mode benchmark packet can anchor a `sota_confirmed` signoff when external search and nearest-work evidence are recorded.
- Added a regression test proving completed external-search provider results make a SOTA evidence package ready for signoff.

Production boundary:

- The evidence and signoff APIs record human/current-literature review state; they do not automatically prove SOTA.
- Benchmark packets can represent dry-run or real-mode runs; publication-grade claims still require linked artifacts, current literature review, and repeatable metric execution.

## 2026-06-25 - Local Documentation And Development Process Index

Documentation maintenance completed:

- Added `docs/documentation_index.md` as the canonical map for product, architecture, operations, evaluation, benchmark, and handoff documents.
- Added `docs/development_process.md` to define the standard local development lifecycle, verification ladder, runtime checks, cleanup, and handoff expectations.
- Updated `AGENTS.md` so this local GitHub clone is treated as a runnable local deployment when the operator requests local work, while preserving remote/GitHub source-of-truth awareness.
- Linked the new documentation entry points from `README.md`.

Verification completed:

- `bash -n scripts/env.sh scripts/setup-local.sh scripts/run-local.sh scripts/clean.sh scripts/deep-clean.sh scripts/docker-clean.sh` passed.
- Documentation-only workflow; no service restart, dependency install, or data migration was required.

## 2026-06-25 - Local Qwen Provider Configuration

Local configuration completed:

- Wrote the real provider key only to the ignored local `.env` file with user-only file permissions.
- Configured the local `.env` for `qwen3-32b`, `qwen3-vl-embedding`, and `qwen3-rerank` through a DashScope-style OpenAI-compatible base URL.
- Updated `.env.example` with model names and base URLs but no secret values.
- Added embedder and rerank settings to application config and `/health/ready` model-provider readiness reporting without exposing key values.
- Added OpenAI-compatible embedding/rerank provider adapters, provider modes, local-test safety gates, external embedding index storage, batch embedding, unchanged-text hash skips, learned rerank integration after lexical/vector recall, and an explicit opt-in real-provider smoke script.
- Fixed DashScope Qwen3 non-streaming chat calls by adding `enable_thinking=false`, added automatic native DashScope fallback for `qwen3-vl-embedding` and `qwen3-rerank`, and verified all five provider roles with the explicit real-provider smoke script.
- Added `scripts/evaluate_real_papers.py` for opt-in end-to-end PDF/text/Markdown paper evaluation with local JSON/Markdown reports under `outputs/evaluations/`.
- Ran real-provider deep evaluation on G3, GeoToken, and Recognition through Reasoning PDFs. All 3 completed, external `qwen3-vl-embedding` indexed 30 objects, context search returned evidence/graph context for all queries, and proposal reviews reached `ready_for_advisor_review`; remaining blockers are novelty collision risk, missing related-work searches, and one high-risk assumption per idea.
- Added `docs/real_paper_evaluation_report.md` as the durable summary of real-PDF metrics and remaining production blockers.
- Added `docs/model_provider_strategy.md` to record model roles, current wiring status, text-vs-vision embedding guidance, and test-safety rules.
- Added local real-paper evaluation report APIs and a Workbench Real Eval panel for loading the latest report into the dossier preview.
- Added evaluator-side retrieval-mode comparison against a local hash/no-rerank baseline for the same context queries.
- Added manual SOTA review package generation for ideas, including novelty screening, related-work matrix creation, missing-search tracking, review queries, Markdown checklist export, list/detail/export APIs, and a Workbench action.
- Linked the provider strategy from the documentation index, README, and deployment docs.

Verification completed:

- Confirmed `.env` is ignored by git and has user-only permissions.
- Verified provider model names and key presence through a redacted local check.

Remaining implementation gap:

- `qwen3-32b` is wired through the existing OpenAI-compatible JSON client.
- Remaining production hardening: add live external-search SOTA signoff, optional image/page embedding, and measured benchmark execution hooks.

## 2026-06-12 Remote Handoff Baseline

Remote source of truth:

- Path: `/home/zhangwz/Research-Assistant-Agent`
- Branch: `main`
- GitHub: `ImpZhang/Research-Assistant-Agent.git`
- Current pushed baseline after formatting: `9178e46 Format research service modules`

Remote worktree notes:

- Two historical root-level docs remain untracked and intentionally untouched:
  - `research_assistant_requirements.md`
  - `research_assistant_technical_design.md`
- `uv.lock` was restored after `uv run` changed registry URLs during verification.
- Future verification should prefer `.venv/bin/ruff` and `.venv/bin/pytest` when dependency sync is not intended.

Verification summary:

- `.venv/bin/ruff check .`: passed
- `.venv/bin/ruff format --check .`: passed after formatting six service modules
- `uv run pytest -q`: passed before formatting, `43 passed in 727.94s`
- `uv run python scripts/smoke_api.py`: passed before formatting, manifest count `114`, project bundle file count `158`

Completed maintenance:

- Formatted six research service modules.
- Committed and pushed `9178e46 Format research service modules`.

Next planned work:

1. Implement durable project bundle release review outcome signoff evidence records.
2. Add schema, routes, graph links, tool manifest entries, project bundle metadata/artifacts, Workbench controls, tests, smoke coverage, README, and docs.
3. Verify with ruff, pytest, and smoke.
4. Commit and push the completed feature.

## 2026-06-12 - Release Review Outcome Signoff Evidence

Implemented in progress:

- Added release review outcome signoff schema, API routes, tool manifest entries, graph linkage, project bundle metadata/Markdown artifacts, Workbench controls, pytest coverage, smoke coverage, README, and requirements/design documentation.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff check backend/research/routes.py backend/research/schemas.py backend/research/services/artifact_graph_service.py tests/test_app.py scripts/smoke_api.py` passed.
- `.venv/bin/ruff format --check backend/research/routes.py backend/research/schemas.py backend/research/services/artifact_graph_service.py tests/test_app.py scripts/smoke_api.py` passed after formatting touched Python files.
- Focused pytest passed: `5 passed in 474.12s`.
- Full pytest passed: `43 passed in 752.08s`.
- Smoke API passed with `tool_manifest_count=118`, `tool_bridge_count=118`, `project_bundle_file_count=166`, and deferred release review outcome signoff evidence in the project bundle summary.

Committed and pushed:

- `d2e0741 Add release review outcome signoff evidence`.

## 2026-06-12 - Workbench Pilot Launch Status

Implemented in progress:

- Added a read-only Workbench Pilot Launch panel that aggregates onboarding readiness, onboarding progress, and project cockpit state.
- Added static tests and documentation for the customer-pilot first screen.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `git --no-pager diff --check` passed.
- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_workbench_static_assets_are_served` passed: `1 passed in 3.55s`.

## 2026-06-12 - Handoff TODO Refresh

Documentation maintenance completed:

- Marked release review outcome signoff evidence as completed in `codex_handoff/03_TODO.md`.
- Recorded the first completed P3 slice and split remaining customer-pilot hardening into narrower follow-up tasks.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

## 2026-06-12 - Workbench First-Run State Helpers

Implemented in progress:

- Added Workbench helpers for API-key, network, and generic API errors.
- Routed repeated Workbench error rendering through the helper so first-run failures show actionable retry guidance.
- Added empty-state rendering for missing paper uploads and missing pilot report snapshots.
- Added static tests and documentation for the customer-pilot first-run state behavior.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `git --no-pager diff --check` passed.
- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_workbench_static_assets_are_served` passed: `1 passed in 3.56s`.

## 2026-06-12 - Pilot Deployment Checklist

Documentation maintenance completed:

- Added a customer-pilot deployment checklist covering remote git state, `.env` handling, API-key protection, persistent storage, backups, health checks, Workbench verification, MCP bridge checks, and operator approval for state-changing commands.
- Linked the checklist from README deployment notes.
- Updated handoff TODO so the next P3 slices focus on write-operation audit design and later Workbench delivery empty states.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `git --no-pager diff --check` passed.
- Documentation-only change; no service start, dependency install, or business-code test was required.


## 2026-06-12 - Write Operation Audit Design

Documentation maintenance completed:

- Added `docs/write_operation_audit_design.md` to define purpose, non-goals, event shape, capture points, JSONL-first storage, redaction rules, acceptance criteria, and open questions.
- Linked the audit design from README, requirements, technical design, and handoff TODO.
- Kept this as design-only work; no middleware, persistence, route, deployment, or service behavior changed.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `git --no-pager diff --check` passed.
- Reviewed `docs/write_operation_audit_design.md` for secret-safe redaction guidance and design-only scope.
- Documentation-only change; no service start, dependency install, or business-code test was required.

## 2026-06-12 - Workbench Delivery Empty States

Implemented in progress:

- Reused `renderWorkbenchEmpty` for workflow preconditions that require an upstream idea, proposal, task board, experiment run, evidence ledger, release note, feedback record, acceptance snapshot, review outcome, signoff evidence, bundle readiness snapshot, triage snapshot, or research plan.
- Preserved loading/creating/recording progress states on `renderResult(..., "warn")` so empty states remain distinct from in-flight work.
- Added static Workbench assertions for delivery empty-state copy.
- Updated README, requirements, technical design, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- Confirmed no old-style precondition `renderResult(..., "warn")` calls remain for `first`/`before`/`at least` workflow empty states.
- `git --no-pager diff --check` passed.
- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_workbench_static_assets_are_served` passed: `1 passed in 3.38s`.

## 2026-06-12 - Data Backup And Restore Notes

Documentation maintenance completed:

- Added `/app/data` backup/restore operator notes to `docs/deployment.md` for the compose service and Docker volume.
- Documented what the backup must include, what secrets must stay outside git/public bundles, and why cold backup is the preferred first-pilot path.
- Added restore guardrails: do not restore over a live service volume, back up current data first, and verify health/readiness/Workbench after restore.
- Linked the backup/restore notes from README and updated handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `git --no-pager diff --check` passed.
- Reviewed backup/restore examples to avoid destructive restore-over-live-volume guidance.
- Documentation-only change; no service start, Docker command, dependency install, or business-code test was required.


## 2026-06-12 - JSONL Write Operation Audit Prototype

Implemented in progress:

- Added a disabled-by-default write-operation audit middleware for non-GET `/research/*` requests.
- Added `backend/research/services/write_audit_service.py` for JSONL append, operation/entity categorization, and metadata sanitization.
- Added non-secret config placeholders in `.env.example` and deployment docs.
- Added tests proving JSONL records are written when enabled, default-disabled behavior is preserved, and API keys/request bodies are not serialized.
- Updated README, technical design, audit design, status capability, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `git --no-pager diff --check` passed.
- `.venv/bin/ruff check backend/app.py backend/research/config.py backend/research/routes.py backend/research/services/write_audit_service.py tests/test_app.py` passed.
- `.venv/bin/ruff format backend/app.py backend/research/config.py backend/research/routes.py backend/research/services/write_audit_service.py tests/test_app.py` reformatted two files.
- `.venv/bin/ruff format --check backend/app.py backend/research/config.py backend/research/routes.py backend/research/services/write_audit_service.py tests/test_app.py` passed.
- Focused pytest passed: `5 passed in 4.68s`.
- Full `tests/test_app.py` passed: `37 passed in 749.43s (0:12:29)`.


## 2026-06-12 - Workbench Delivery Control Grouping

Implemented in progress:

- Grouped the Workbench dossier controls into idea loop, task board, project delivery, and project operations action groups.
- Preserved existing element ids and JavaScript bindings while making the long delivery workflow easier to scan.
- Added responsive CSS so action groups collapse cleanly on narrow screens.
- Added static Workbench assertions for the new grouping labels.
- Updated README, technical design, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `git --no-pager diff --check` passed.
- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_workbench_static_assets_are_served` passed: `1 passed in 3.50s`.


## 2026-06-12 - Database Migration Strategy

Documentation maintenance completed:

- Added `docs/database_migration_strategy.md` to document the current SQLAlchemy `create_all` state, first-pilot schema-change policy, future Alembic direction, pre-migration checklist, SQLite constraints, acceptance criteria, and open questions.
- Linked the strategy from README, deployment checklist, technical design, and handoff TODO.
- Kept this as documentation-only work; no dependencies, migration directories, database commands, or service behavior changed.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `git --no-pager diff --check` passed.
- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format tests/test_app.py` reformatted the touched test file.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_deployment_artifacts_document_customer_runtime` passed: `1 passed in 3.12s`.

## 2026-06-12 - Upload Size And Extension Guardrails

Implemented in progress:

- Added upload extension validation before writing paper files to disk, defaulting to `.txt`, `.md`, and `.pdf`.
- Added `PAPER_UPLOAD_MAX_BYTES` with a 10 MiB default and rejection before writing oversized uploads to disk.
- Added runtime env support for `PAPER_UPLOAD_DIR`, `PAPER_UPLOAD_ALLOWED_EXTENSIONS`, and `PAPER_UPLOAD_MAX_BYTES` so pilot deployments can tune upload policy without code changes.
- Added tests for unsupported extension rejection and oversized upload rejection.
- Updated `.env.example`, deployment docs, technical design, status capability, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `git --no-pager diff --check` passed.
- `.venv/bin/ruff format backend/research/config.py backend/research/routes.py backend/research/services/document_ingestion.py tests/test_app.py` reformatted one file.
- `.venv/bin/ruff check backend/research/config.py backend/research/routes.py backend/research/services/document_ingestion.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/research/config.py backend/research/routes.py backend/research/services/document_ingestion.py tests/test_app.py` passed.
- Focused pytest passed: `5 passed in 4.85s`.
- Full `tests/test_app.py` passed: `39 passed in 737.83s (0:12:17)`.


## 2026-06-12 - API Key Fingerprints In Write Audit

Implemented in progress:

- Added short SHA-256 API-key fingerprint prefixes to write-operation audit metadata when an API key is supplied.
- Preserved secret safety by never serializing API key values, request bodies, or payload text into audit JSONL records.
- Added tests for successful authenticated writes and failed 401 writes to prove fingerprints are recorded without key disclosure.
- Updated deployment docs, audit design, technical design, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format backend/app.py tests/test_app.py` left files unchanged.
- `.venv/bin/ruff check backend/app.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/app.py tests/test_app.py` passed.
- Focused pytest passed: `4 passed in 4.27s`.
- Full `tests/test_app.py` passed: `40 passed in 750.26s (0:12:30)`.


## 2026-06-12 - Admin Authorization Policy

Implemented in progress:

- Added `docs/admin_authorization_policy.md` to define the operator-only boundary for future audit summary/export features.
- Clarified that the regular pilot API key is not admin authorization by itself because Workbench, scripts, and MCP clients may share it.
- Updated deployment, audit design, README, and handoff TODO references without adding endpoints or changing runtime behavior.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- Reviewed `docs/admin_authorization_policy.md` for secret-safe placeholder-only guidance.
- `git --no-pager diff --check` passed.
- No runtime code, dependencies, services, databases, or secret files were touched.


## 2026-06-12 - Admin-Gated Write Audit Summary

Implemented in progress:

- Added default-off `AUDIT_ADMIN_EXPORT_ENABLED` settings and `AUDIT_ADMIN_KEY_HEADER_NAME` placeholder documentation without adding real secrets.
- Added `GET /research/admin/write-audit/summary`, registered only when the admin export flag is enabled.
- Added sanitized JSONL aggregate summary logic that reports counts, status classes, routes, and recent request ids without actor labels, key fingerprints, request bodies, or raw events.
- Added tests for default-disabled behavior, normal API-key-only denial, wrong admin key denial, and successful sanitized summary output.
- Updated README, deployment notes, audit design, technical design, admin authorization policy, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format backend/app.py backend/research/config.py backend/research/routes.py backend/research/schemas.py backend/research/services/write_audit_service.py tests/test_app.py` reformatted one file, then left files unchanged on rerun.
- `.venv/bin/ruff check backend/app.py backend/research/config.py backend/research/routes.py backend/research/schemas.py backend/research/services/write_audit_service.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/app.py backend/research/config.py backend/research/routes.py backend/research/schemas.py backend/research/services/write_audit_service.py tests/test_app.py` passed.
- Focused pytest passed: `7 passed in 3.60s`.
- Full `tests/test_app.py` passed with verbose durations: `43 passed in 762.87s (0:12:42)`.


## 2026-06-12 - Upload Content Sniffing Guardrails

Implemented in progress:

- Added lightweight content sniffing before uploaded papers are written to disk.
- Rejected `.txt` and `.md` uploads that contain null bytes or are not UTF-8 text.
- Rejected `.pdf` uploads that do not start with a PDF header before invoking PDF parsing or writing the file.
- Added tests proving binary text and fake PDF uploads fail before files are persisted.
- Updated README, deployment notes, technical design, status capability, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format backend/research/services/document_ingestion.py backend/research/routes.py tests/test_app.py` reformatted one file.
- `.venv/bin/ruff check backend/research/services/document_ingestion.py backend/research/routes.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/research/services/document_ingestion.py backend/research/routes.py tests/test_app.py` passed.
- Focused pytest passed: `7 passed in 5.85s`.
- Full `tests/test_app.py` passed with verbose durations: `45 passed in 759.05s (0:12:39)`.


## 2026-06-12 - Write Audit Retention Policy

Implemented in progress:

- Added `docs/write_audit_retention_policy.md` to define first-pilot JSONL retention targets and operator raw-export workflow.
- Clarified that raw audit export remains unimplemented until the documented retention workflow is implemented in code.
- Updated README, deployment notes, audit design, admin authorization policy, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- Reviewed `docs/write_audit_retention_policy.md` for secret-safe placeholder-only guidance.
- `grep -R "write_audit_retention_policy" -n README.md docs codex_handoff/03_TODO.md` confirmed cross-document references.
- `git --no-pager diff --check` passed.
- No runtime code, dependencies, services, databases, raw audit exports, or secret files were touched.


## 2026-06-12 - Admin-Gated Write Audit Raw Export

Implemented in progress:

- Added `GET /research/admin/write-audit/export`, registered only when `AUDIT_ADMIN_EXPORT_ENABLED=true`.
- Reused the separate audit admin key gate and kept normal pilot API-key-only callers unauthorized.
- Added bounded export filters with `max_records`, `start_created_at`, and `end_created_at` query parameters.
- Re-sanitized exported events with the existing field allowlist plus metadata sensitive-key filtering before rendering JSONL.
- Added tests for default-disabled behavior, admin authorization, bounded export, time-window filtering, and secret/body/prompt exclusion.
- Updated README, deployment notes, audit design, retention policy, admin authorization policy, status capability, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format backend/app.py backend/research/routes.py backend/research/services/write_audit_service.py tests/test_app.py` reformatted one file after the export route and service changes.
- `.venv/bin/ruff check backend/app.py backend/research/routes.py backend/research/services/write_audit_service.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/app.py backend/research/routes.py backend/research/services/write_audit_service.py tests/test_app.py` passed.
- Focused pytest passed: `6 passed in 3.16s`.
- Full `tests/test_app.py` passed with verbose durations: `46 passed in 796.39s (0:13:16)`.


## 2026-06-12 - User Project Scoping Design

Implemented in progress:

- Added `docs/user_project_scoping_design.md` to define the target user, project, and membership model before migrations.
- Clarified that current `created_by`, `owner_type`, and artifact `scope` values are not authorization boundaries.
- Defined default-project compatibility, request scope resolution, API behavior, Workbench/MCP forwarding, migration sequencing, and future acceptance criteria.
- Updated README, technical design, database migration strategy, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- Reviewed `docs/user_project_scoping_design.md` for migration-safe, secret-free scoping guidance.
- `grep -R "user_project_scoping_design" -n README.md docs codex_handoff/03_TODO.md` confirmed cross-document references.
- `git --no-pager diff --check` passed.
- No runtime code, dependencies, services, databases, schema migrations, or secret files were touched.


## 2026-06-12 - Write Audit Readiness Check

Implemented in progress:

- Added `write_audit_dir` to `/health/ready` so deployments report audit persistence readiness.
- Kept audit readiness non-blocking when `WRITE_AUDIT_ENABLED=false` and checked directory creation/writability when enabled.
- Added tests for disabled and enabled audit readiness states plus the status capability flag.
- Updated README, deployment notes, technical design, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format backend/app.py backend/research/routes.py tests/test_app.py` left files unchanged.
- `.venv/bin/ruff check backend/app.py backend/research/routes.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/app.py backend/research/routes.py tests/test_app.py` passed.
- Focused pytest passed: `4 passed in 4.48s`.
- Full `tests/test_app.py` passed with verbose durations: `47 passed in 771.24s (0:12:51)`.

## 2026-06-12 - Durable Workflow Queue Design

Documentation maintenance completed:

- Added `docs/workflow_queue_design.md` to document the current FastAPI `BackgroundTasks` + `jobs` table contract and the future durable queue migration path.
- Compared DB-backed worker leasing, RQ/Redis, Celery/Dramatiq, and Temporal without adding dependencies or changing runtime behavior.
- Documented API compatibility requirements for async workflow queueing, job polling, artifact hydration, cancel, and retry.
- Recorded future job leasing, heartbeat, retry, and idempotency fields as migration-gated work.
- Updated README, technical design, and handoff TODO references.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `grep -R "workflow_queue_design" -n README.md docs/research_assistant_technical_design.md codex_handoff/03_TODO.md` confirmed cross-document references.
- Reviewed `docs/workflow_queue_design.md` for design-only scope and secret-safe operator guidance.
- `git --no-pager diff --check` passed.
- Documentation-only change; no dependency install, service start, worker start, migration, or business-code test was required.

## 2026-06-12 - Handoff TODO Consistency Refresh

Documentation maintenance completed:

- Updated Priority 3 handoff TODO to reflect that admin-gated write-audit summary and bounded raw JSONL export endpoints are already complete.
- Replaced the stale audit summary/export next slice with audit rotation/cleanup guidance gated on backup and retention decisions.
- Clarified that a checked `/data` backup script still waits for operator confirmation of deployment host and volume naming.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- Reviewed `codex_handoff/03_TODO.md` Priority 3 and Priority 4 sections for stale completed work.
- `git --no-pager diff --check` passed.
- Documentation-only change; no dependency install, service start, migration, backup command, or business-code test was required.

## 2026-06-12 - GraphRAG LangGraph DeerFlow Revisit

Documentation maintenance completed:

- Added `docs/graphrag_langgraph_deerflow_evaluation.md` to record the P6 evaluation of heavier graph retrieval and orchestration options.
- Documented current implementation boundaries: relational GraphRAG-lite nodes/edges, lexical/vector/context search, graph neighbor expansion, service-layer workflows, and placeholder LangGraph modules.
- Recommended keeping GraphRAG-lite and service-layer workflows for now, while treating full GraphRAG, deeper LangGraph runtime use, and DeerFlow as trigger-gated future options.
- Updated README, technical design, and handoff TODO references.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- Reviewed `graph_service.py`, `retrieval_service.py`, `models.py`, graph/search routes, tests, smoke coverage, and technical design references.
- `grep -R "graphrag_langgraph_deerflow_evaluation" -n README.md docs codex_handoff/03_TODO.md` confirmed cross-document references.
- `git --no-pager diff --check` passed.
- Documentation-only change; no dependency install, service start, migration, queue worker, or business-code test was required.

## 2026-06-12 - GraphRAG-Lite Stats Endpoint

Implemented in progress:

- Added `GET /research/graph/stats` for read-only GraphRAG-lite observability.
- Reported total node/edge counts, node type counts, edge type counts, orphan edge count, and duplicate edge group count.
- Added the endpoint to the stable tool manifest as `get_graph_stats` without side effects.
- Added focused test coverage and smoke API coverage for the stats endpoint.
- Updated README, technical design, P6 evaluation notes, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format backend/research/services/graph_service.py backend/research/schemas.py backend/research/routes.py tests/test_app.py scripts/smoke_api.py` left files unchanged.
- `.venv/bin/ruff check backend/research/services/graph_service.py backend/research/schemas.py backend/research/routes.py tests/test_app.py scripts/smoke_api.py` passed.
- `.venv/bin/ruff format --check backend/research/services/graph_service.py backend/research/schemas.py backend/research/routes.py tests/test_app.py scripts/smoke_api.py` passed.
- Focused pytest passed: `2 passed in 2.91s`.

## 2026-06-12 - Context Search Graph Edge Filters

Implemented in progress:

- Added optional `graph_edge_types` to `ContextSearchRequest` and `RetrievalService.search_context`.
- Kept default context search behavior unchanged when no edge type filter is supplied.
- Filtered only GraphRAG-lite neighbor expansion edges, leaving evidence, gap, idea, and vector retrieval behavior unchanged.
- Added focused test coverage for filtering context search graph edges to `paper_has_evidence`.
- Updated README, technical design, P6 evaluation notes, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format backend/research/services/retrieval_service.py backend/research/schemas.py backend/research/routes.py tests/test_app.py` reformatted two files.
- `.venv/bin/ruff check backend/research/services/retrieval_service.py backend/research/schemas.py backend/research/routes.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/research/services/retrieval_service.py backend/research/schemas.py backend/research/routes.py tests/test_app.py` passed.
- Focused pytest passed: `2 passed in 45.65s`.

## 2026-06-13 - GraphRAG-Lite Duplicate Edge Reuse

Implemented in progress:

- Updated `GraphService.create_edge` to reuse an existing edge with the same source node, target node, and edge type.
- Merged evidence ids without duplicates, merged payload metadata, and retained the higher edge weight when a duplicate write is requested.
- Added service-level test coverage proving duplicate edge writes return the same edge and do not increase row count for that source/target/type.
- Updated README, technical design, P6 evaluation notes, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format backend/research/services/graph_service.py tests/test_app.py` left files unchanged.
- `.venv/bin/ruff check backend/research/services/graph_service.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/research/services/graph_service.py tests/test_app.py` passed.
- Service-level focused pytest passed: `1 passed in 3.41s`.
- Existing GraphRAG-lite workflow link pytest passed: `1 passed in 2.58s`.

## 2026-06-13 - Context Search Ranking Tie-Breaks

Implemented in progress:

- Added stable tie-break ranking for context search results after lexical and vector scoring.
- Reused the same ranking helper for lexical-only hits and vector-merged hits.
- Same-score results now prefer more matched terms, then newer artifacts, then stable ids.
- Added focused unit coverage for the tie-break order and reran the context search graph/filter regression test.
- Updated README, technical design, P6 evaluation notes, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format backend/research/services/retrieval_service.py tests/test_app.py` left files unchanged.
- `.venv/bin/ruff check backend/research/services/retrieval_service.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/research/services/retrieval_service.py tests/test_app.py` passed.
- Focused pytest passed: `2 passed in 47.13s`.

## 2026-06-13 - Context Search Score Breakdowns

Implemented in progress:

- Added `score_breakdown` to scored evidence, gap, and idea context-search results.
- Split scores into lexical, bonus, phrase, and vector contributions.
- Reused score breakdowns for lexical-only hits and vector-merged hits.
- Added focused test coverage proving vector-backed evidence includes a positive vector contribution.
- Updated README, technical design, P6 evaluation notes, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format backend/research/services/retrieval_service.py backend/research/schemas.py backend/research/routes.py tests/test_app.py` left files unchanged.
- `.venv/bin/ruff check backend/research/services/retrieval_service.py backend/research/schemas.py backend/research/routes.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/research/services/retrieval_service.py backend/research/schemas.py backend/research/routes.py tests/test_app.py` passed.
- Focused pytest passed: `2 passed in 43.69s`.

## 2026-06-13 - Context Search Evaluation Plan

Documentation maintenance completed:

- Added `docs/context_search_evaluation_plan.md` to define retrieval calibration questions, fixture shape, metrics, scoring-change rules, and guardrails.
- Documented hit@k, MRR, graph edge hit rate, graph noise rate, score breakdown coverage, and empty-query guard checks as initial metrics.
- Clarified that future scoring changes should be evidence-led and should not use private customer data or secrets in committed fixtures.
- Updated README, technical design, and handoff TODO references.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- Reviewed `docs/context_search_evaluation_plan.md` for design-only scope and secret-safe evaluation guidance.
- `grep -R "context_search_evaluation_plan" -n README.md docs codex_handoff/03_TODO.md` confirmed cross-document references.
- `git --no-pager diff --check` passed.
- Documentation-only change; no dependency install, service start, migration, evaluation job, or business-code test was required.

## 2026-06-13 - Context Search Evaluation Fixture

Implemented in progress:

- Extended the deterministic context-search pytest fixture with retrieval evaluation metrics.
- Added helper checks for evidence hit@k, mean reciprocal rank, score breakdown coverage, graph edge hit rate, and graph noise rate.
- Verified the synthetic context-search fixture keeps expected evidence at hit@1/hit@3/hit@5 with MRR 1.0.
- Verified `paper_has_evidence` graph edge hits and zero graph noise under an edge-type filter.
- Updated README, context-search evaluation plan, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` reformatted one file.
- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- Focused pytest passed: `1 passed in 56.37s`.

## 2026-06-13 - Context Search Empty Query Guard Fixture

Implemented in progress:

- Added an `empty_query_guard_rate` helper for deterministic context-search evaluation.
- Added a fast fixture covering empty, too-short, and punctuation-only queries.
- Verified each invalid query returns HTTP 400 with the stable searchable-term error message.
- Updated README, context-search evaluation plan, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` reformatted one file.
- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- Focused pytest passed: `1 passed in 1.93s`.

## 2026-06-13 - Context Search Score Breakdown Consistency Fixture

Implemented in progress:

- Added a `score_breakdown_total_match_rate` helper for deterministic context-search evaluation.
- Extended the context-search graph fixture so every evidence/gap/idea result must have score breakdown totals matching the visible score within rounding tolerance.
- Updated README, context-search evaluation plan, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` left the file unchanged.
- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- Focused pytest passed: `1 passed in 46.22s`.

## 2026-06-13 - Context Search Graph Noise Assertion

Implemented in progress:

- Reused the existing `graph_noise_rate` helper in the filtered graph context-search fixture.
- Required filtered graph edges to report zero unrelated edge types when `graph_edge_types` is restricted to `paper_has_evidence`.
- Updated handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` left the file unchanged.
- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- Focused pytest passed: `1 passed in 47.86s`.

## 2026-06-13 - Context Search Paper Filter Fixture

Implemented in progress:

- Added an API-level `paper_filter_leak_rate` evaluation helper for context-search evidence.
- Added a deterministic two-paper fixture that proves unfiltered search can find paper A while a `paper_ids=[paper B]` search does not leak paper A evidence.
- Verified `include_graph=false` returns no graph nodes or edges in the scoped fixture.
- Updated README, context-search evaluation plan, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` left the file unchanged.
- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- Focused pytest passed: `1 passed in 25.41s`.

## 2026-06-13 - Remote Agent Handoff Index

Implemented in progress:

- Added root `AGENTS.md` with remote source-of-truth rules, safety constraints, secret handling, prohibited commands, and verification guidance.
- Added root `TODO.md` as a stable index over the detailed handoff queue and current approval-gated work.
- Linked AGENTS, TODO, `codex_handoff/03_TODO.md`, and `docs/progress_log.md` from README.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- Confirmed the known password literal is absent from `AGENTS.md`, `TODO.md`, `README.md`, and `docs/progress_log.md`.
- `git --no-pager diff --cached --check` passed with no whitespace errors.

## 2026-06-13 - Context Search Evaluation Check Script

Implemented in progress:

- Added `scripts/check_context_search_evaluations.sh` as a focused remote check for context-search evaluation fixtures.
- The script runs `.venv/bin/ruff check`, `.venv/bin/ruff format --check`, and the empty-query, paper-filter, and graph-context pytest fixtures.
- Linked the script from README repository layout and verification instructions.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- First script attempt was interrupted by an SSH connection timeout; reconnect confirmed no lingering `pytest`, `ruff`, or script process.
- Rerun `bash scripts/check_context_search_evaluations.sh` passed: `3 passed in 66.85s`.

## 2026-06-13 - Context Search Evaluation Script Coverage

Implemented in progress:

- Added the fast context-search ranking tie-break unit test to `scripts/check_context_search_evaluations.sh`.
- Kept the script scoped to existing `.venv` tools and focused pytest targets; it still does not install dependencies or start services.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_context_search_evaluations.sh` passed with the expanded target list: `4 passed in 66.02s`.

## 2026-06-13 - Context Search Evaluation Handoff Sync

Implemented in progress:

- Updated handoff TODO to make `scripts/check_context_search_evaluations.sh` the default focused check before scoring or graph-expansion changes.
- Updated the top-level TODO and context-search evaluation plan with the same script guidance.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- Reviewed the documentation diff for `TODO.md`, `codex_handoff/03_TODO.md`, and `docs/context_search_evaluation_plan.md`.
- `git --no-pager diff --check` passed with no whitespace errors.

## 2026-06-13 - Context Search Unknown Edge Filter Fixture

Implemented in progress:

- Extended the context-search graph fixture with an unknown `graph_edge_types` allowlist value.
- Verified scoped retrieval still returns evidence but graph edges stay empty instead of falling back to unrelated edge types.
- Updated the context-search evaluation plan and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_context_search_evaluations.sh` passed: `4 passed in 69.73s`.

## 2026-06-13 - Context Search Paper Filter Artifact Coverage

Implemented in progress:

- Extended the paper-filter evaluation fixture so scoped searches check gaps and ideas in addition to evidence.
- Added gap and idea paper-filter leak-rate helpers based on `source_paper_ids` and `related_paper_ids`.
- Updated the context-search evaluation plan and handoff TODO to describe artifact-level paper-filter coverage.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- First script run exposed an under-specified fixture: paper B lacked limitation/future-work evidence for gap mining.
- Added explicit `Limitations` and `Future Work` sections to the fixture paper.
- Rerun `bash scripts/check_context_search_evaluations.sh` passed: `4 passed in 68.22s`.

## 2026-06-13 - GraphRAG-Lite Check Script

Implemented in progress:

- Added `scripts/check_graph_rag_lite.sh` as a focused remote check for GraphRAG-lite duplicate-edge reuse and graph link/stat fixtures.
- Linked the script from README verification instructions and handoff TODO.
- Kept the script scoped to existing `.venv` tools and focused pytest targets; it does not install dependencies or start services.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_graph_rag_lite.sh` passed: `2 passed in 2.87s`.

## 2026-06-13 - Pilot Readiness Check Script

Implemented in progress:

- Added `scripts/check_pilot_readiness.sh` as a focused remote check for health/readiness, optional API-key guard behavior, upload guardrails, Workbench static assets, onboarding readiness, and pilot status report behavior.
- Linked the script from README verification instructions, top-level TODO, and handoff TODO.
- Kept the script scoped to existing `.venv` tools and in-process pytest targets; it does not install dependencies or start services.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_pilot_readiness.sh` passed: `13 passed in 21.89s`.

## 2026-06-13 - Remote Safe Suite Check Script

Implemented in progress:

- Added `scripts/check_remote_safe_suite.sh` as an aggregate no-service verification entrypoint.
- The suite runs pilot-readiness, GraphRAG-lite, and context-search focused checks in sequence.
- Linked the aggregate script from README verification instructions and top-level TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_remote_safe_suite.sh` passed all three focused suites: pilot readiness `13 passed in 22.48s`, GraphRAG-lite `2 passed in 2.39s`, and context search `4 passed in 67.51s`.

## 2026-06-13 - Write Audit Guardrail Check Script

Implemented in progress:

- Added `scripts/check_write_audit_guardrails.sh` as a focused remote check for JSONL write-audit sanitization, failed-key fingerprinting, default-off behavior, admin gating, sanitized summary, and bounded raw export behavior.
- Added the write-audit guardrail script to `scripts/check_remote_safe_suite.sh`.
- Linked the script from README verification instructions, top-level TODO, and handoff TODO.
- Kept the script scoped to existing `.venv` tools and in-process pytest targets; it does not read production audit logs, install dependencies, or start services.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_write_audit_guardrails.sh` passed: `7 passed in 3.81s`.
- `bash scripts/check_remote_safe_suite.sh` passed all four focused suites: pilot readiness `13 passed in 23.30s`, write audit `7 passed in 3.88s`, GraphRAG-lite `2 passed in 2.84s`, and context search `4 passed in 68.06s`.

## 2026-06-13 - Workflow Job Controls Check Script

Implemented in progress:

- Added `scripts/check_workflow_job_controls.sh` as a focused remote check for synchronous literature-to-ideas workflow artifacts, async job traces, and cancel/retry controls.
- Added the workflow job controls script to `scripts/check_remote_safe_suite.sh`.
- Linked the script from README verification instructions, top-level TODO, and handoff TODO.
- Kept the script scoped to existing `.venv` tools and in-process pytest targets; it does not install dependencies or start services.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_workflow_job_controls.sh` passed: `3 passed in 85.05s`.
- `bash scripts/check_remote_safe_suite.sh` passed all five focused suites: pilot readiness `13 passed in 22.05s`, write audit `7 passed in 3.68s`, workflow job controls `3 passed in 86.43s`, GraphRAG-lite `2 passed in 2.86s`, and context search `4 passed in 66.83s`.

## 2026-06-13 - Pilot Upload Happy-Path Check

Implemented in progress:

- Added `test_upload_text_paper` to `scripts/check_pilot_readiness.sh` so pilot-readiness checks cover both upload rejection guardrails and the valid text-upload happy path.
- Updated handoff TODO to describe the expanded upload coverage.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_pilot_readiness.sh` passed: `14 passed in 22.13s`.
- `bash scripts/check_remote_safe_suite.sh` passed all five focused suites: pilot readiness `14 passed in 21.76s`, write audit `7 passed in 3.81s`, workflow job controls `3 passed in 87.02s`, GraphRAG-lite `2 passed in 2.87s`, and context search `4 passed in 68.41s`.

## 2026-06-13 - Tool Bridge Contract Check Script

Implemented in progress:

- Added `scripts/check_tool_bridge_contracts.sh` as a focused remote check for `/research/tools/manifest`, `/research/tools/mcp-spec`, and the dependency-light MCP HTTP bridge helpers.
- Added the tool bridge contract script to `scripts/check_remote_safe_suite.sh`.
- Linked the script from README verification instructions, top-level TODO, and handoff TODO.
- Kept the script scoped to existing `.venv` tools and in-process/unit pytest targets; it does not install dependencies or start services.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_tool_bridge_contracts.sh` passed: `10 passed in 2.21s`.
- `bash scripts/check_remote_safe_suite.sh` passed all six focused suites: pilot readiness `14 passed in 24.31s`, write audit `7 passed in 3.91s`, workflow job controls `3 passed in 85.40s`, tool bridge contracts `10 passed in 2.04s`, GraphRAG-lite `2 passed in 2.85s`, and context search `4 passed in 67.07s`.

## 2026-06-13 - Deployment Contract Check Script

Implemented in progress:

- Added `scripts/check_deployment_contracts.sh` as a focused remote check for Dockerfile, docker-compose, deployment docs, migration/admin policy docs, and `.env.example` customer-runtime placeholders.
- Added the deployment contract script to `scripts/check_remote_safe_suite.sh`.
- Linked the script from README verification instructions, top-level TODO, and handoff TODO.
- Kept the script scoped to existing `.venv` tools and in-process pytest targets; it does not install dependencies, read real `.env` values, or start services.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_deployment_contracts.sh` passed: `1 passed in 1.64s`.
- `bash scripts/check_remote_safe_suite.sh` passed all seven focused suites: pilot readiness `14 passed in 25.04s`, deployment contracts `1 passed in 1.69s`, write audit `7 passed in 3.87s`, workflow job controls `3 passed in 86.54s`, tool bridge contracts `10 passed in 2.31s`, GraphRAG-lite `2 passed in 2.83s`, and context search `4 passed in 67.54s`.

## 2026-06-13 - Pilot First-Run Readiness Coverage

Implemented in progress:

- Expanded `scripts/check_pilot_readiness.sh` from 14 to 18 pytest targets.
- Added existing first-run setup wizard, onboarding task creation, onboarding progress, and pilot report snapshot/export/comparison coverage to the focused pilot-readiness check.
- Updated README, top-level TODO, and handoff TODO so the script is the default check before changing setup wizard, onboarding, pilot report, upload, API-key, or Workbench first-run behavior.
- Kept the work scoped to existing `.venv` tools and in-process pytest targets; it does not install dependencies or start services.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_pilot_readiness.sh` passed: `18 passed in 56.48s`.
- `bash scripts/check_remote_safe_suite.sh` passed all seven focused suites: pilot readiness `18 passed in 55.80s`, deployment contracts `1 passed in 1.65s`, write audit `7 passed in 3.97s`, workflow job controls `3 passed in 85.72s`, tool bridge contracts `10 passed in 2.17s`, GraphRAG-lite `2 passed in 2.93s`, and context search `4 passed in 68.14s`.

## 2026-06-13 - Research Workflow Primitive Check Script

Implemented in progress:

- Added `scripts/check_research_workflow_primitives.sh` as a focused remote check for deterministic local literature search, provider parsers, paper-card extraction, gap mining, idea generation, review/experiment planning, novelty screening, related-work matrices, and Markdown dossier exports.
- Added the research workflow primitive script to `scripts/check_remote_safe_suite.sh`.
- Linked the script from README verification instructions, top-level TODO, and handoff TODO.
- Kept the script scoped to existing `.venv` tools and in-process pytest targets; it does not install dependencies, start services, or require external API access.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_research_workflow_primitives.sh` passed: `10 passed in 65.83s`.
- `bash scripts/check_remote_safe_suite.sh` passed all eight focused suites: pilot readiness `18 passed in 57.19s`, deployment contracts `1 passed in 1.71s`, research workflow primitives `10 passed in 67.80s`, write audit `7 passed in 4.18s`, workflow job controls `3 passed in 86.09s`, tool bridge contracts `10 passed in 2.19s`, GraphRAG-lite `2 passed in 2.91s`, and context search `4 passed in 63.99s`.

## 2026-06-13 - Research Planning Contract Check Script

Implemented in progress:

- Added `scripts/check_research_planning_contracts.sh` as a focused remote check for research profiles, profile-aware advisor briefs, research plans, plan tasks/progress, idea refinement, ranking, portfolios, agenda exports, and lineage/bundle planning metadata.
- Added the research planning contract script to `scripts/check_remote_safe_suite.sh`.
- Linked the script from README verification instructions, top-level TODO, and handoff TODO.
- Kept the script scoped to existing `.venv` tools and in-process pytest targets; it does not install dependencies, start services, or require external API access.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_research_planning_contracts.sh` passed: `3 passed in 68.06s`.
- `bash scripts/check_remote_safe_suite.sh` passed all nine focused suites: pilot readiness `18 passed in 57.17s`, deployment contracts `1 passed in 1.39s`, research workflow primitives `10 passed in 67.82s`, research planning contracts `3 passed in 68.48s`, write audit `7 passed in 3.96s`, workflow job controls `3 passed in 85.59s`, tool bridge contracts `10 passed in 2.20s`, GraphRAG-lite `2 passed in 2.93s`, and context search `4 passed in 68.69s`.

## 2026-06-13 - Proposal Contract Check And Scoped Vector Search

Implemented in progress:

- Added `scripts/check_research_proposal_contracts.sh` as a focused remote check for proposal drafts, readiness reviews, proposal revisions, revision follow-up tasks, and proposal Markdown exports.
- Kept the proposal check separate from `scripts/check_remote_safe_suite.sh` because the current deep proposal chain is long-running.
- Fixed scoped context search so vector hits are filtered by `paper_ids` before scoring instead of taking a small global vector top-k and filtering afterward.
- Expanded `scripts/check_context_search_evaluations.sh` ruff coverage to include `backend/research/services/retrieval_service.py` and `backend/research/services/embedding_service.py`.
- Updated README, top-level TODO, and handoff TODO with the proposal check entry.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_research_proposal_contracts.sh` passed: `1 passed in 486.71s`.
- `bash scripts/check_context_search_evaluations.sh` passed after the scoped vector-search fix: `4 passed in 73.68s`.
- `bash scripts/check_remote_safe_suite.sh` passed all nine default focused suites without the long proposal check: pilot readiness `18 passed in 58.56s`, deployment contracts `1 passed in 1.76s`, research workflow primitives `10 passed in 67.91s`, research planning contracts `3 passed in 66.68s`, write audit `7 passed in 3.29s`, workflow job controls `3 passed in 86.69s`, tool bridge contracts `10 passed in 2.20s`, GraphRAG-lite `2 passed in 2.91s`, and context search `4 passed in 70.95s`.

## 2026-06-13 - Structured Extraction Fallback Coverage

Implemented in progress:

- Added `test_structured_card_extraction_falls_back_without_model_config` to `scripts/check_research_workflow_primitives.sh` so the default remote-safe suite covers deterministic structured paper-card fallback when model credentials are absent.
- Updated README, top-level TODO, and handoff TODO so workflow primitive changes call out structured extraction fallback alongside local literature search, paper cards, gap/idea generation, novelty, related work, and dossier exports.
- Kept the change scoped to existing `.venv` tools and in-process pytest targets; it does not install dependencies, start services, or require external API access.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_research_workflow_primitives.sh` passed: `11 passed in 68.16s`.
- `bash scripts/check_remote_safe_suite.sh` passed all nine default focused suites: pilot readiness `18 passed in 56.23s`, deployment contracts `1 passed in 1.64s`, research workflow primitives `11 passed in 67.50s`, research planning contracts `3 passed in 68.42s`, write audit `7 passed in 3.98s`, workflow job controls `3 passed in 85.95s`, tool bridge contracts `10 passed in 2.17s`, GraphRAG-lite `2 passed in 2.83s`, and context search `4 passed in 66.84s`.

## 2026-06-13 - Research Status Capability Coverage

Implemented in progress:

- Added `test_research_status` to `scripts/check_pilot_readiness.sh` so the default remote-safe suite covers the `/research/status` capability contract.
- Updated README, top-level TODO, and handoff TODO so pilot-readiness changes call out status capability coverage alongside health/readiness, upload/API-key guardrails, first-run onboarding, and pilot reports.
- Kept the change scoped to existing `.venv` tools and in-process pytest targets; it does not install dependencies, start services, or require external API access.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_pilot_readiness.sh` passed: `19 passed in 59.05s`.
- `bash scripts/check_remote_safe_suite.sh` passed all nine default focused suites: pilot readiness `19 passed in 57.65s`, deployment contracts `1 passed in 1.70s`, research workflow primitives `11 passed in 69.16s`, research planning contracts `3 passed in 69.01s`, write audit `7 passed in 3.82s`, workflow job controls `3 passed in 87.72s`, tool bridge contracts `10 passed in 2.16s`, GraphRAG-lite `2 passed in 2.88s`, and context search `4 passed in 70.42s`.

## 2026-06-13 - Focused Test Coverage Guard

Implemented in progress:

- Added `scripts/check_focused_test_coverage.sh` as a fast guard that parses pytest tests and focused check scripts to ensure every pytest test target is assigned to a focused check.
- Added the coverage guard to the start of `scripts/check_remote_safe_suite.sh` so missing focused-check assignment fails before slower suites run.
- Linked the guard from README verification instructions, top-level TODO, and handoff TODO.
- Kept the script read-only over `tests/` and `scripts/check_*.sh`; it does not install dependencies, start services, or inspect secrets.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_remote_safe_suite.sh` passed the focused coverage guard plus all nine default focused suites: pilot readiness `19 passed in 58.79s`, deployment contracts `1 passed in 1.74s`, research workflow primitives `11 passed in 71.29s`, research planning contracts `3 passed in 67.87s`, write audit `7 passed in 3.59s`, workflow job controls `3 passed in 88.50s`, tool bridge contracts `10 passed in 2.19s`, GraphRAG-lite `2 passed in 2.81s`, and context search `4 passed in 77.04s`.

## 2026-06-13 - Remote Long Focused Suite

Implemented in progress:

- Added `scripts/check_remote_long_suite.sh` as the explicit aggregate for long focused checks that should stay out of the default remote-safe suite.
- Seeded the long suite with the focused-test coverage guard and the proposal contract check.
- Linked the long suite from README verification instructions, top-level TODO, and handoff TODO.
- Kept `scripts/check_remote_safe_suite.sh` focused on default no-service checks while preserving a clear command for longer release-style verification.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_remote_long_suite.sh` passed: focused coverage guard reported `All pytest tests are covered by focused check scripts`, and proposal contracts passed `1 passed in 489.28s`.

## 2026-06-13 - Focused Suite Contract Guard

Implemented in progress:

- Added `scripts/check_suite_contracts.sh` as a fast guard for the intended default remote-safe versus long focused suite boundary.
- Added the suite contract guard to the start of `scripts/check_remote_safe_suite.sh` so long checks cannot drift into the default suite unnoticed.
- The guard requires default remote-safe checks to include the fast coverage guard and default focused scripts, forbids proposal/long-suite commands in the default suite, and requires the long suite to include coverage and proposal contracts.
- Linked the guard from README verification instructions, top-level TODO, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_suite_contracts.sh` passed: `Focused suite contracts are valid.`
- `bash scripts/check_remote_safe_suite.sh` passed the suite contract guard, focused coverage guard, and all nine default focused suites: pilot readiness `19 passed in 57.30s`, deployment contracts `1 passed in 1.64s`, research workflow primitives `11 passed in 72.27s`, research planning contracts `3 passed in 70.45s`, write audit `7 passed in 3.99s`, workflow job controls `3 passed in 88.70s`, tool bridge contracts `10 passed in 2.19s`, GraphRAG-lite `2 passed in 2.90s`, and context search `4 passed in 70.72s`.

## 2026-06-13 - Check Script Catalog Guard

Implemented in progress:

- Added `scripts/check_script_catalog.sh` as a fast guard that ensures every `scripts/check_*.sh` file is listed in README and follows the standard bash/root-directory preamble.
- Added the catalog guard to `scripts/check_remote_safe_suite.sh` after the suite-boundary guard and before pytest coverage mapping.
- Updated `scripts/check_suite_contracts.sh` so the default suite must include the catalog guard.
- Linked the catalog guard from README verification instructions, top-level TODO, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_script_catalog.sh` passed: `Check script catalog is synchronized.`
- `bash scripts/check_suite_contracts.sh` passed: `Focused suite contracts are valid.`
- `bash scripts/check_remote_safe_suite.sh` passed the suite contract guard, script catalog guard, focused coverage guard, and all nine default focused suites: pilot readiness `19 passed in 58.91s`, deployment contracts `1 passed in 1.66s`, research workflow primitives `11 passed in 69.75s`, research planning contracts `3 passed in 71.07s`, write audit `7 passed in 4.12s`, workflow job controls `3 passed in 89.37s`, tool bridge contracts `10 passed in 2.22s`, GraphRAG-lite `2 passed in 2.92s`, and context search `4 passed in 70.65s`.

## 2026-06-13 - Secret File Guard

Implemented in progress:

- Added `scripts/check_secret_file_guard.sh` as a fast guard for sensitive-looking tracked filenames and required ignore patterns.
- The guard allows `.env.example`, rejects tracked `.env`, `.env.*`, private-key/archive key suffixes, and filenames containing token/cookie/credential/secret markers.
- Added `*.pem`, `*.key`, `*.p12`, and `*.pfx` to `.gitignore` without reading or printing any sensitive file contents.
- Added the secret-file guard to `scripts/check_remote_safe_suite.sh` and updated `scripts/check_suite_contracts.sh` so default-suite composition requires it.
- Linked the guard from README verification instructions, top-level TODO, and handoff TODO.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_secret_file_guard.sh` passed: `Secret file guard passed.`
- `bash scripts/check_script_catalog.sh` passed: `Check script catalog is synchronized.`
- `bash scripts/check_suite_contracts.sh` passed: `Focused suite contracts are valid.`
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, and coverage guards plus all nine default focused suites: pilot readiness `19 passed in 60.89s`, deployment contracts `1 passed in 1.67s`, research workflow primitives `11 passed in 68.26s`, research planning contracts `3 passed in 69.90s`, write audit `7 passed in 4.06s`, workflow job controls `3 passed in 90.04s`, tool bridge contracts `10 passed in 2.16s`, GraphRAG-lite `2 passed in 2.84s`, and context search `4 passed in 71.07s`.

## 2026-06-13 - Handoff Document Consistency Guard

Implemented in progress:

- Added `scripts/check_handoff_docs.sh` as a fast guard for remote-first handoff document consistency.
- Added the handoff-doc guard to `scripts/check_remote_safe_suite.sh` after secret-file checks and updated `scripts/check_suite_contracts.sh` so the default suite requires it.
- Linked the guard from README verification instructions, top-level TODO, and handoff TODO.
- Kept the guard limited to repository documentation and did not read secrets, install dependencies, start services, or modify business code.
- Allowed `scripts/check_secret_file_guard.sh` in the secret-file guard whitelist so the filename guard does not flag its own checking script.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `bash scripts/check_secret_file_guard.sh` passed: `Secret file guard passed.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_suite_contracts.sh` passed: `Focused suite contracts are valid.`
- `bash scripts/check_script_catalog.sh` passed: `Check script catalog is synchronized.`
- `git --no-pager diff --check` passed with no whitespace errors.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, and coverage guards plus all nine default focused suites: pilot readiness `19 passed in 60.71s`, deployment contracts `1 passed in 1.63s`, research workflow primitives `11 passed in 70.63s`, research planning contracts `3 passed in 70.48s`, write audit `7 passed in 3.90s`, workflow job controls `3 passed in 88.35s`, tool bridge contracts `10 passed in 1.73s`, GraphRAG-lite `2 passed in 2.51s`, and context search `4 passed in 71.22s`.

## 2026-06-13 - Generated File Guard

Implemented in progress:

- Added `scripts/check_generated_file_guard.sh` as a fast guard against tracked generated artifacts, caches, virtualenvs, dependency folders, and build/coverage outputs.
- Added `node_modules/`, `.coverage`, `coverage.xml`, and `htmlcov/` to `.gitignore` alongside existing Python cache/build patterns.
- Added the generated-file guard to `scripts/check_remote_safe_suite.sh` and updated `scripts/check_suite_contracts.sh` so the default suite requires it.
- Linked the guard from README verification instructions, top-level TODO, and handoff TODO.
- Did not remove generated files from the working tree, read secrets, install dependencies, start services, or modify business code.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `bash scripts/check_generated_file_guard.sh` passed: `Generated file guard passed.`
- `bash scripts/check_suite_contracts.sh` passed: `Focused suite contracts are valid.`
- `bash scripts/check_script_catalog.sh` passed: `Check script catalog is synchronized.`
- `bash scripts/check_secret_file_guard.sh` passed: `Secret file guard passed.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `git --no-pager diff --check` passed with no whitespace errors.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `19 passed in 57.17s`, deployment contracts `1 passed in 1.65s`, research workflow primitives `11 passed in 69.78s`, research planning contracts `3 passed in 71.05s`, write audit `7 passed in 4.10s`, workflow job controls `3 passed in 90.21s`, tool bridge contracts `10 passed in 2.20s`, GraphRAG-lite `2 passed in 2.90s`, and context search `4 passed in 72.55s`.

## 2026-06-13 - Upload Filename Sanitization Test

Implemented in progress:

- Added a focused upload guardrail test that posts a text paper with a path-traversal filename and verifies only the basename is persisted under `PAPER_UPLOAD_DIR`.
- Added the new test to `scripts/check_pilot_readiness.sh` so upload filename sanitization stays in the no-service pilot-readiness suite.
- Did not change upload implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_upload_sanitizes_path_traversal_filename` passed: `1 passed in 3.64s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_pilot_readiness.sh` passed: `20 passed in 57.76s`.
- `git --no-pager diff --check` passed with no whitespace errors.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `20 passed in 58.26s`, deployment contracts `1 passed in 1.67s`, research workflow primitives `11 passed in 71.08s`, research planning contracts `3 passed in 69.64s`, write audit `7 passed in 3.91s`, workflow job controls `3 passed in 90.72s`, tool bridge contracts `10 passed in 2.23s`, GraphRAG-lite `2 passed in 3.11s`, and context search `4 passed in 68.99s`.

## 2026-06-13 - Upload UTF-8 Guardrail Test

Implemented in progress:

- Added a focused upload guardrail test that posts non-UTF-8 text bytes and verifies the API rejects the upload before writing the file.
- Added the new test to `scripts/check_pilot_readiness.sh` so text encoding validation stays in the no-service pilot-readiness suite.
- Updated `codex_handoff/03_TODO.md` to keep the completed pilot-readiness upload guardrail coverage synchronized.
- Did not change upload implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_upload_rejects_non_utf8_text_before_writing` passed: `1 passed in 3.56s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_pilot_readiness.sh` passed: `21 passed in 59.79s`.
- `git --no-pager diff --check` passed with no whitespace errors.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `21 passed in 60.03s`, deployment contracts `1 passed in 1.64s`, research workflow primitives `11 passed in 71.29s`, research planning contracts `3 passed in 86.16s`, write audit `7 passed in 3.84s`, workflow job controls `3 passed in 89.62s`, tool bridge contracts `10 passed in 2.18s`, GraphRAG-lite `2 passed in 3.08s`, and context search `4 passed in 72.29s`.

## 2026-06-13 - Markdown Upload Default Extension Test

Implemented in progress:

- Added a focused upload happy-path test that posts a Markdown paper and verifies the documented default `.md` extension is accepted, indexed, and produces evidence.
- Added the new test to `scripts/check_pilot_readiness.sh` so Markdown upload coverage stays in the no-service pilot-readiness suite.
- Updated `codex_handoff/03_TODO.md` to keep the completed pilot-readiness upload coverage synchronized.
- Did not change upload implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_upload_markdown_paper_uses_default_allowed_extension` passed: `1 passed in 3.75s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_pilot_readiness.sh` passed: `22 passed in 62.22s`.
- `git --no-pager diff --check` passed with no whitespace errors.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `22 passed in 60.20s`, deployment contracts `1 passed in 1.75s`, research workflow primitives `11 passed in 71.68s`, research planning contracts `3 passed in 70.26s`, write audit `7 passed in 3.98s`, workflow job controls `3 passed in 100.07s`, tool bridge contracts `10 passed in 2.19s`, GraphRAG-lite `2 passed in 2.92s`, and context search `4 passed in 70.19s`.

## 2026-06-13 - Empty Upload Guardrail Test

Implemented in progress:

- Added a focused upload guardrail test that posts an empty text file and verifies the API rejects it before writing the file.
- Added the new test to `scripts/check_pilot_readiness.sh` so empty-upload rejection stays in the no-service pilot-readiness suite.
- Updated `codex_handoff/03_TODO.md` to keep completed pilot-readiness upload coverage synchronized.
- Did not change upload implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_upload_rejects_empty_file_before_writing` passed: `1 passed in 3.67s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_pilot_readiness.sh` passed: `23 passed in 61.51s`.
- `git --no-pager diff --check` passed with no whitespace errors.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `23 passed in 62.67s`, deployment contracts `1 passed in 1.32s`, research workflow primitives `11 passed in 72.46s`, research planning contracts `3 passed in 72.41s`, write audit `7 passed in 3.95s`, workflow job controls `3 passed in 92.71s`, tool bridge contracts `10 passed in 2.28s`, GraphRAG-lite `2 passed in 2.90s`, and context search `4 passed in 73.22s`.

## 2026-06-13 - Upload Allowed Extension Override Test

Implemented in progress:

- Added a focused upload guardrail test that sets `PAPER_UPLOAD_ALLOWED_EXTENSIONS=txt`, posts a Markdown file, and verifies the API rejects it before writing the file.
- Added the new test to `scripts/check_pilot_readiness.sh` so extension override validation stays in the no-service pilot-readiness suite.
- Updated `codex_handoff/03_TODO.md` to keep completed pilot-readiness upload coverage synchronized.
- Did not change upload implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_upload_respects_allowed_extensions_override_before_writing` passed: `1 passed in 3.33s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_pilot_readiness.sh` passed: `24 passed in 60.07s`.
- `git --no-pager diff --check` passed with no whitespace errors.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `24 passed in 60.59s`, deployment contracts `1 passed in 1.67s`, research workflow primitives `11 passed in 73.84s`, research planning contracts `3 passed in 72.05s`, write audit `7 passed in 3.96s`, workflow job controls `3 passed in 91.74s`, tool bridge contracts `10 passed in 2.18s`, GraphRAG-lite `2 passed in 2.88s`, and context search `4 passed in 73.36s`.

## 2026-06-13 - Upload Extension Case Test

Implemented in progress:

- Added a focused upload happy-path test that posts an uppercase `.TXT` file and verifies extension matching remains case-insensitive while preserving the submitted filename.
- Added the new test to `scripts/check_pilot_readiness.sh` so extension case handling stays in the no-service pilot-readiness suite.
- Updated `codex_handoff/03_TODO.md` to keep completed pilot-readiness upload coverage synchronized.
- Did not change upload implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_upload_accepts_uppercase_allowed_extension` passed: `1 passed in 3.77s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_pilot_readiness.sh` passed: `25 passed in 67.85s`.
- `git --no-pager diff --check` passed with no whitespace errors.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 61.33s`, deployment contracts `1 passed in 1.71s`, research workflow primitives `11 passed in 73.96s`, research planning contracts `3 passed in 72.19s`, write audit `7 passed in 3.35s`, workflow job controls `3 passed in 91.99s`, tool bridge contracts `10 passed in 2.19s`, GraphRAG-lite `2 passed in 3.03s`, and context search `4 passed in 73.17s`.

## 2026-06-13 - Context Search Query Dedup Fixture

Implemented in progress:

- Added a deterministic context-search evaluation that repeats the same query marker three times and verifies retrieval reports the matched term once with a single lexical contribution.
- Added the new test to `scripts/check_context_search_evaluations.sh` so query-term deduplication stays covered before changing scoring weights.
- Updated `codex_handoff/03_TODO.md` to keep context-search evaluation coverage synchronized.
- Did not change retrieval implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_deduplicates_repeated_query_terms` passed: `1 passed in 4.77s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `5 passed in 74.38s`.
- `git --no-pager diff --check` passed with no whitespace errors.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 63.58s`, deployment contracts `1 passed in 1.65s`, research workflow primitives `11 passed in 74.20s`, research planning contracts `3 passed in 73.82s`, write audit `7 passed in 3.94s`, workflow job controls `3 passed in 94.36s`, tool bridge contracts `10 passed in 2.20s`, GraphRAG-lite `2 passed in 2.94s`, and context search `5 passed in 76.33s`.

## 2026-06-13 - Context Search Limit Clamp Fixture

Implemented in progress:

- Added a deterministic context-search evaluation that posts `limit: 0` and verifies the service clamps the request to one bounded result instead of returning zero or unbounded evidence.
- Added the new test to `scripts/check_context_search_evaluations.sh` so non-positive limit handling stays covered before changing scoring weights or graph expansion.
- Updated `codex_handoff/03_TODO.md` to keep context-search evaluation coverage synchronized.
- Did not change retrieval implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_clamps_non_positive_limit` passed: `1 passed in 4.50s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_context_search_evaluations.sh` passed: `6 passed in 76.41s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 61.00s`, deployment contracts `1 passed in 1.68s`, research workflow primitives `11 passed in 72.95s`, research planning contracts `3 passed in 73.64s`, write audit `7 passed in 4.11s`, workflow job controls `3 passed in 93.67s`, tool bridge contracts `10 passed in 2.18s`, GraphRAG-lite `2 passed in 3.08s`, and context search `6 passed in 76.39s`.

## 2026-06-13 - Context Search Large Limit Clamp Fixture

Implemented in progress:

- Added a deterministic context-search evaluation that creates 30 synthetic evidence rows and posts `limit: 99` to verify the service clamps large requests to 25 bounded evidence results.
- Added the new test to `scripts/check_context_search_evaluations.sh` so upper-limit handling stays covered before changing scoring weights or graph expansion.
- Updated `codex_handoff/03_TODO.md` to describe lower/upper limit-clamping coverage in the focused context-search check.
- Did not change retrieval implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_clamps_large_limit` passed: `1 passed in 4.86s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `7 passed in 78.88s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 66.54s`, deployment contracts `1 passed in 1.67s`, research workflow primitives `11 passed in 73.35s`, research planning contracts `3 passed in 72.78s`, write audit `7 passed in 3.74s`, workflow job controls `3 passed in 95.53s`, tool bridge contracts `10 passed in 2.18s`, GraphRAG-lite `2 passed in 2.90s`, and context search `7 passed in 79.46s`.

## 2026-06-13 - Context Search Graph Filter Normalization Fixture

Implemented in progress:

- Extended the deterministic graph-context search fixture to pass duplicate and blank `graph_edge_types` values and verify filtered graph expansion still returns only `paper_has_evidence` edges with zero graph noise.
- Updated `codex_handoff/03_TODO.md` to describe filter-normalization coverage in the focused context-search check.
- Did not change retrieval implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_returns_evidence_and_graph_context` passed: `1 passed in 53.19s`.
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `7 passed in 81.24s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 66.95s`, deployment contracts `1 passed in 1.81s`, research workflow primitives `11 passed in 74.41s`, research planning contracts `3 passed in 72.65s`, write audit `7 passed in 4.39s`, workflow job controls `3 passed in 95.37s`, tool bridge contracts `10 passed in 2.39s`, GraphRAG-lite `2 passed in 2.72s`, and context search `7 passed in 80.36s`.

## 2026-06-13 - Context Search No-Match Fixture

Implemented in progress:

- Added a deterministic no-match context-search evaluation that creates a scoped synthetic paper without evidence, gaps, or ideas and verifies the API returns empty context plus the stable no-match answer brief.
- Added the new test to `scripts/check_context_search_evaluations.sh` so negative scoped queries stay covered before changing scoring weights or graph expansion.
- Updated `docs/context_search_evaluation_plan.md` and `codex_handoff/03_TODO.md` to keep committed context-search evaluation coverage synchronized.
- Did not change retrieval implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_no_match_fixture` passed: `1 passed in 5.63s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `8 passed in 81.61s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 63.44s`, deployment contracts `1 passed in 1.68s`, research workflow primitives `11 passed in 75.05s`, research planning contracts `3 passed in 73.90s`, write audit `7 passed in 3.81s`, workflow job controls `3 passed in 95.88s`, tool bridge contracts `10 passed in 2.36s`, GraphRAG-lite `2 passed in 3.07s`, and context search `8 passed in 82.68s`.

## 2026-06-13 - Context Search Vector Rescue Fixture

Implemented in progress:

- Added a deterministic lexical-miss/vector-hit context-search evaluation that finds a stable local hash-vector collision token, creates evidence that does not contain the query term, and verifies vector retrieval still returns it with lexical/bonus/phrase contributions at zero.
- Added the new test to `scripts/check_context_search_evaluations.sh` so vector rescue behavior stays covered before changing scoring weights or embedding behavior.
- Updated `docs/context_search_evaluation_plan.md` and `codex_handoff/03_TODO.md` to keep committed context-search evaluation coverage synchronized.
- Did not change retrieval or embedding implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_vector_hit_rescues_lexical_miss` passed: `1 passed in 4.92s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `9 passed in 81.95s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 63.02s`, deployment contracts `1 passed in 1.66s`, research workflow primitives `11 passed in 75.26s`, research planning contracts `3 passed in 74.88s`, write audit `7 passed in 3.93s`, workflow job controls `3 passed in 97.58s`, tool bridge contracts `10 passed in 2.70s`, GraphRAG-lite `2 passed in 2.86s`, and context search `9 passed in 85.58s`.

## 2026-06-13 - Context Search Phrase Bonus Fixture

Implemented in progress:

- Added a deterministic exact-phrase context-search evaluation that creates evidence containing an ordered two-term query phrase and verifies lexical, bonus, phrase, and vector score-breakdown components remain visible and internally consistent.
- Added the new test to `scripts/check_context_search_evaluations.sh` so phrase bonus behavior stays covered before changing scoring weights.
- Updated `docs/context_search_evaluation_plan.md` and `codex_handoff/03_TODO.md` to keep committed context-search evaluation coverage synchronized.
- Did not change retrieval or embedding implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_exact_phrase_bonus_breakdown` passed: `1 passed in 4.97s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `10 passed in 84.47s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 64.31s`, deployment contracts `1 passed in 1.67s`, research workflow primitives `11 passed in 75.76s`, research planning contracts `3 passed in 73.99s`, write audit `7 passed in 3.92s`, workflow job controls `3 passed in 99.52s`, tool bridge contracts `10 passed in 2.20s`, GraphRAG-lite `2 passed in 2.89s`, and context search `10 passed in 85.44s`.

## 2026-06-13 - Context Search Evidence Bonus Fixture

Implemented in progress:

- Added a deterministic evidence-confidence context-search evaluation that creates evidence with separated query terms, confidence `0.73`, and verifies lexical, bonus, phrase, and vector score-breakdown components remain visible and internally consistent.
- Added the new test to `scripts/check_context_search_evaluations.sh` so evidence confidence bonus behavior stays covered before changing scoring weights.
- Updated `docs/context_search_evaluation_plan.md` and `codex_handoff/03_TODO.md` to keep committed context-search evaluation coverage synchronized.
- Did not change retrieval or embedding implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_evidence_confidence_bonus_breakdown` passed: `1 passed in 5.07s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `11 passed in 86.39s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 67.65s`, deployment contracts `1 passed in 1.66s`, research workflow primitives `11 passed in 75.69s`, research planning contracts `3 passed in 75.46s`, write audit `7 passed in 4.02s`, workflow job controls `3 passed in 108.53s`, tool bridge contracts `10 passed in 2.21s`, GraphRAG-lite `2 passed in 3.00s`, and context search `11 passed in 87.79s`.

## 2026-06-13 - Context Search Gap Bonus Fixture

Implemented in progress:

- Added a deterministic gap-feasibility context-search evaluation that creates a scoped research gap with feasibility `8.4` and verifies lexical, bonus, phrase, and vector score-breakdown components remain visible and internally consistent.
- Added the new test to `scripts/check_context_search_evaluations.sh` so gap feasibility bonus behavior stays covered before changing scoring weights.
- Updated `docs/context_search_evaluation_plan.md` and `codex_handoff/03_TODO.md` to keep committed context-search evaluation coverage synchronized.
- Did not change retrieval or embedding implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_gap_feasibility_bonus_breakdown` passed: `1 passed in 5.19s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `12 passed in 88.75s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 69.15s`, deployment contracts `1 passed in 1.76s`, research workflow primitives `11 passed in 77.22s`, research planning contracts `3 passed in 76.61s`, write audit `7 passed in 3.63s`, workflow job controls `3 passed in 98.92s`, tool bridge contracts `10 passed in 2.18s`, GraphRAG-lite `2 passed in 2.92s`, and context search `12 passed in 89.56s`.

## 2026-06-13 - Context Search Idea Bonus Fixture

Implemented in progress:

- Added a deterministic idea-overall-score context-search evaluation that creates a scoped research idea with `overall_score` `7.6` and verifies lexical, bonus, phrase, and vector score-breakdown components remain visible and internally consistent.
- Added the new test to `scripts/check_context_search_evaluations.sh` so idea score bonus behavior stays covered before changing scoring weights.
- Updated `docs/context_search_evaluation_plan.md` and `codex_handoff/03_TODO.md` to keep committed context-search evaluation coverage synchronized.
- Did not change retrieval or embedding implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_idea_overall_score_bonus_breakdown` passed: `1 passed in 4.69s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `13 passed in 90.99s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 67.06s`, deployment contracts `1 passed in 1.73s`, research workflow primitives `11 passed in 77.00s`, research planning contracts `3 passed in 78.57s`, write audit `7 passed in 4.19s`, workflow job controls `3 passed in 98.52s`, tool bridge contracts `10 passed in 2.22s`, GraphRAG-lite `2 passed in 2.97s`, and context search `13 passed in 89.89s`.

## 2026-06-13 - GraphRAG Duplicate Stats Fixture

Implemented in progress:

- Added a deterministic GraphRAG-lite stats test that creates two direct duplicate edges for the same source, target, and edge type, then verifies `/research/graph/stats` reports the edge type count and at least one duplicate edge group.
- Added the new test to `scripts/check_graph_rag_lite.sh` so duplicate-edge stat reporting stays covered with duplicate-edge reuse and graph link/stat fixtures.
- Updated `codex_handoff/03_TODO.md` to keep GraphRAG-lite focused coverage synchronized.
- Did not change graph implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/graph_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/graph_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_graph_stats_reports_duplicate_edge_groups` passed: `1 passed in 4.19s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_graph_rag_lite.sh` passed: `3 passed in 3.65s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 69.27s`, deployment contracts `1 passed in 1.66s`, research workflow primitives `11 passed in 80.00s`, research planning contracts `3 passed in 75.46s`, write audit `7 passed in 3.92s`, workflow job controls `3 passed in 84.04s`, tool bridge contracts `10 passed in 2.33s`, GraphRAG-lite `3 passed in 3.70s`, and context search `13 passed in 92.82s`.

## 2026-06-13 - GraphRAG Orphan Stats Fixture

Implemented in progress:

- Added a deterministic GraphRAG-lite stats test that creates one temporary orphan edge pointing at a missing target node, verifies `/research/graph/stats` reports at least one orphan edge, and cleans up the edge and source node before later graph stats fixtures run.
- Added the new test to `scripts/check_graph_rag_lite.sh` so orphan-edge stat reporting stays covered with duplicate-edge reuse, duplicate-edge stats, and graph link/stat fixtures.
- Updated `codex_handoff/03_TODO.md` to keep GraphRAG-lite focused coverage synchronized.
- Did not change graph implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/graph_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/graph_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_graph_stats_reports_orphan_edges_without_persisting_fixture` passed: `1 passed in 4.49s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_graph_rag_lite.sh` passed: `4 passed in 4.03s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 62.89s`, deployment contracts `1 passed in 1.66s`, research workflow primitives `11 passed in 79.49s`, research planning contracts `3 passed in 78.37s`, write audit `7 passed in 4.06s`, workflow job controls `3 passed in 100.26s`, tool bridge contracts `10 passed in 1.76s`, GraphRAG-lite `4 passed in 4.17s`, and context search `13 passed in 109.32s`.

## 2026-06-13 - Context Search Graph Paper Filter Fixture

Implemented in progress:

- Added a deterministic context-search evaluation that uploads two synthetic papers sharing the same query term, scopes search to one paper with `include_graph=true`, and verifies GraphRAG-lite nodes and `paper_has_evidence` edges do not leak the excluded paper or its evidence ids.
- Added the new test to `scripts/check_context_search_evaluations.sh` so graph paper-filter behavior stays covered before changing graph expansion or retrieval scoring.
- Updated `docs/context_search_evaluation_plan.md` and `codex_handoff/03_TODO.md` to keep committed context-search evaluation coverage synchronized.
- Did not change retrieval, graph, or embedding implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_graph_context_respects_paper_filter` passed: `1 passed in 5.43s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `14 passed in 96.04s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 68.15s`, deployment contracts `1 passed in 1.79s`, research workflow primitives `11 passed in 81.73s`, research planning contracts `3 passed in 78.56s`, write audit `7 passed in 4.10s`, workflow job controls `3 passed in 99.58s`, tool bridge contracts `10 passed in 2.26s`, GraphRAG-lite `4 passed in 4.31s`, and context search `14 passed in 92.31s`.

## 2026-06-13 - Context Search Graph Expansion Recall

Implemented in progress:

- Updated GraphRAG-lite context expansion to query seed-node-connected edges before falling back to the recent-edge evidence-id scan, so relevant older graph edges are not hidden by many newer unrelated edges.
- Added a deterministic context-search regression with one relevant older `paper_has_evidence` edge and 805 newer unrelated edges, then verified scoped graph search still returns the relevant edge and paper node.
- Added the new test to `scripts/check_context_search_evaluations.sh` and updated `docs/context_search_evaluation_plan.md` plus `codex_handoff/03_TODO.md` to keep graph expansion recall coverage synchronized.
- Did not install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_graph_expansion_keeps_relevant_edge_after_recent_noise` passed: `1 passed in 5.31s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `15 passed in 94.02s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 66.58s`, deployment contracts `1 passed in 1.78s`, research workflow primitives `11 passed in 78.75s`, research planning contracts `3 passed in 79.87s`, write audit `7 passed in 4.30s`, workflow job controls `3 passed in 103.93s`, tool bridge contracts `10 passed in 2.30s`, GraphRAG-lite `4 passed in 4.35s`, and context search `15 passed in 94.27s`.

## 2026-06-13 - Context Search Multi Edge Filter Fixture

Implemented in progress:

- Extended the deterministic context-search graph-context fixture to request multiple GraphRAG-lite workflow edge types at once and verify the response includes the selected `paper_has_evidence` and `gap_supported_by_evidence` families without admitting unrelated edge types.
- Updated `docs/context_search_evaluation_plan.md` and `codex_handoff/03_TODO.md` so committed context-search evaluation coverage reflects multi-edge-type filter checks.
- Did not change retrieval implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_returns_evidence_and_graph_context` passed: `1 passed in 57.63s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `15 passed in 97.85s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 68.99s`, deployment contracts `1 passed in 1.64s`, research workflow primitives `11 passed in 80.94s`, research planning contracts `3 passed in 80.38s`, write audit `7 passed in 3.84s`, workflow job controls `3 passed in 100.63s`, tool bridge contracts `10 passed in 2.21s`, GraphRAG-lite `4 passed in 4.29s`, and context search `15 passed in 97.59s`.

## 2026-06-14 - Context Search Edge Filter Whitespace Normalization

Implemented in progress:

- Normalized GraphRAG-lite context-search `graph_edge_types` by trimming whitespace before applying edge-type filters, while still dropping blank values and duplicates.
- Extended the existing graph-context fixture to pass blank, whitespace-padded, and tab-padded `paper_has_evidence` filters and verify the selected edge family is still returned without unrelated edge types.
- Updated `docs/context_search_evaluation_plan.md` and `codex_handoff/03_TODO.md` so committed context-search evaluation coverage reflects blank, duplicate, and whitespace filter normalization.
- Did not change response schemas, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_context_search_returns_evidence_and_graph_context` passed: `1 passed in 58.83s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_context_search_evaluations.sh` passed: `15 passed in 96.56s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `25 passed in 67.25s`, deployment contracts `1 passed in 1.83s`, research workflow primitives `11 passed in 79.27s`, research planning contracts `3 passed in 77.88s`, write audit `7 passed in 4.09s`, workflow job controls `3 passed in 101.21s`, tool bridge contracts `10 passed in 2.38s`, GraphRAG-lite `4 passed in 4.29s`, and context search `15 passed in 95.21s`.

## 2026-06-14 - Upload Allowed Extension Normalization Fixture

Implemented in progress:

- Added a deterministic pilot-readiness upload guardrail test for `PAPER_UPLOAD_ALLOWED_EXTENSIONS` values with whitespace, optional leading dots, and mixed case.
- Added the new test to `scripts/check_pilot_readiness.sh` so operator-friendly upload extension configuration stays covered before changing first-run upload behavior.
- Updated `codex_handoff/03_TODO.md` to keep upload guardrail coverage synchronized.
- Did not change upload implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/app.py backend/research/config.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/app.py backend/research/config.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_upload_allowed_extensions_override_normalizes_values` passed: `1 passed in 4.50s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_pilot_readiness.sh` passed: `26 passed in 67.89s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `26 passed in 67.89s`, deployment contracts `1 passed in 1.79s`, research workflow primitives `11 passed in 80.79s`, research planning contracts `3 passed in 78.75s`, write audit `7 passed in 3.87s`, workflow job controls `3 passed in 104.85s`, tool bridge contracts `10 passed in 2.27s`, GraphRAG-lite `4 passed in 4.38s`, and context search `15 passed in 97.23s`.

## 2026-06-14 - Upload Max Bytes Fallback Fixture

Implemented in progress:

- Added a deterministic pilot-readiness upload guardrail test for invalid `PAPER_UPLOAD_MAX_BYTES` values, verifying small Markdown uploads fall back to the default limit and still index successfully.
- Added the new test to `scripts/check_pilot_readiness.sh` so upload limit configuration fallback stays covered before changing first-run upload behavior.
- Updated `codex_handoff/03_TODO.md` to keep upload guardrail coverage synchronized.
- Did not change upload implementation, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/app.py backend/research/config.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/app.py backend/research/config.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_upload_invalid_max_bytes_falls_back_to_default_limit` passed: `1 passed in 3.63s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_pilot_readiness.sh` passed: `27 passed in 66.28s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `27 passed in 70.28s`, deployment contracts `1 passed in 1.60s`, research workflow primitives `11 passed in 80.67s`, research planning contracts `3 passed in 80.00s`, write audit `7 passed in 3.99s`, workflow job controls `3 passed in 100.43s`, tool bridge contracts `10 passed in 2.14s`, GraphRAG-lite `4 passed in 3.83s`, and context search `15 passed in 97.97s`.

## 2026-06-14 - Upload Non-Positive Max Bytes Fallback

Implemented in progress:

- Hardened upload size configuration so non-positive `PAPER_UPLOAD_MAX_BYTES` values fall back to the default upload limit instead of disabling size validation.
- Added a deterministic pilot-readiness upload guardrail test that temporarily lowers the default limit, sets `PAPER_UPLOAD_MAX_BYTES=-1`, and verifies an oversized text upload is rejected before writing.
- Added the new test to `scripts/check_pilot_readiness.sh` so upload limit fallback stays covered before changing first-run upload behavior.
- Updated `codex_handoff/03_TODO.md` to keep upload guardrail coverage synchronized.
- Did not install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/app.py backend/research/config.py backend/research/services/document_ingestion.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/app.py backend/research/config.py backend/research/services/document_ingestion.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_upload_non_positive_max_bytes_falls_back_to_default_limit` passed: `1 passed in 4.39s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_pilot_readiness.sh` passed: `28 passed in 70.30s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `28 passed in 70.34s`, deployment contracts `1 passed in 1.85s`, research workflow primitives `11 passed in 81.66s`, research planning contracts `3 passed in 79.99s`, write audit `7 passed in 3.99s`, workflow job controls `3 passed in 106.26s`, tool bridge contracts `10 passed in 2.39s`, GraphRAG-lite `4 passed in 4.46s`, and context search `15 passed in 100.23s`.

## 2026-06-14 - OpenAlex Literature Parser Fixture

Implemented in progress:

- Added a deterministic OpenAlex literature item parser fixture covering authorship extraction, venue, DOI URL preference, abstract reconstruction from `abstract_inverted_index`, score ordering, and metadata preservation.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so all configured external literature provider parsers have no-network contract coverage before changing literature search behavior.
- Updated `codex_handoff/03_TODO.md` to keep workflow primitive coverage synchronized.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_openalex_literature_item_parser` passed: `1 passed in 3.69s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `12 passed in 82.10s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `28 passed in 69.53s`, deployment contracts `1 passed in 1.75s`, research workflow primitives `12 passed in 81.44s`, research planning contracts `3 passed in 79.75s`, write audit `7 passed in 4.11s`, workflow job controls `3 passed in 104.80s`, tool bridge contracts `10 passed in 2.36s`, GraphRAG-lite `4 passed in 4.44s`, and context search `15 passed in 102.07s`.

## 2026-06-14 - Literature Provider Config Normalization Fixture

Implemented in progress:

- Added a deterministic no-network literature provider config fixture covering OpenAlex/arXiv/Semantic Scholar aliases, duplicate removal, and unknown provider filtering.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so external provider configuration stays covered before changing literature search behavior.
- Updated `codex_handoff/03_TODO.md` to keep workflow primitive coverage synchronized.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_external_literature_provider_config_normalization` passed: `1 passed in 3.21s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `13 passed in 82.86s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `28 passed in 69.23s`, deployment contracts `1 passed in 1.64s`, research workflow primitives `13 passed in 82.38s`, research planning contracts `3 passed in 81.42s`, write audit `7 passed in 3.86s`, workflow job controls `3 passed in 105.75s`, tool bridge contracts `10 passed in 2.21s`, GraphRAG-lite `4 passed in 4.57s`, and context search `15 passed in 99.00s`.

## 2026-06-14 - Literature Provider Partial Status Fixture

Implemented in progress:

- Added a deterministic no-network external literature search fixture covering mixed provider outcomes: OpenAlex and Semantic Scholar return results while arXiv raises a request timeout.
- Verified partial external search keeps successful provider results and reports the failed provider in the status string.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so external provider status aggregation stays covered before changing literature search behavior.
- Updated `codex_handoff/03_TODO.md` to keep workflow primitive coverage synchronized.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_external_literature_search_returns_partial_status` passed: `1 passed in 3.62s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `14 passed in 81.99s`.
- `bash scripts/check_remote_safe_suite.sh` passed the suite, catalog, secret, handoff-doc, generated-file, and coverage guards plus all nine default focused suites: pilot readiness `28 passed in 70.97s`, deployment contracts `1 passed in 1.77s`, research workflow primitives `14 passed in 82.62s`, research planning contracts `3 passed in 81.75s`, write audit `7 passed in 3.89s`, workflow job controls `3 passed in 104.39s`, tool bridge contracts `10 passed in 2.35s`, GraphRAG-lite `4 passed in 4.25s`, and context search `15 passed in 97.27s`.

## 2026-06-14 - Literature Provider Failed Status Fixture

Implemented in progress:

- Added a deterministic no-network external literature search fixture covering the all-provider-failed path: OpenAlex raises a connection error and arXiv raises an XML parse error.
- Verified failed external search returns no items and reports each provider failure in the status string.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so external provider failure status aggregation stays covered before changing literature search behavior.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_external_literature_search_reports_failed_status` passed: `1 passed in 4.02s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `15 passed in 83.22s`.
- The remote safe suite was completed as its documented component scripts after the first aggregate run lost the SSH connection during a long no-output window: suite contracts passed, script catalog passed, secret file guard passed, handoff docs passed, generated file guard passed, focused coverage passed, pilot readiness `28 passed in 69.40s`, deployment contracts `1 passed in 1.67s`, research workflow primitives `15 passed in 83.22s`, research planning contracts `3 passed in 82.15s`, write audit `7 passed in 3.88s`, workflow job controls `3 passed in 104.83s`, tool bridge contracts `10 passed in 2.16s`, GraphRAG-lite `4 passed in 4.31s`, and context search `15 passed in 99.31s`.

## 2026-06-14 - Literature Provider Completed And Not Configured Status Fixtures

Implemented in progress:

- Added deterministic no-network external literature search fixtures for `not_configured` and all-provider-success `completed` status aggregation.
- Verified unknown/unsupported provider configuration returns no external items with `not_configured` status.
- Verified OpenAlex, arXiv, and Semantic Scholar success paths keep provider results and report `completed` status without calling external APIs.
- Added the new tests to `scripts/check_research_workflow_primitives.sh` so external provider status aggregation stays covered before changing literature search behavior.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_external_literature_search_reports_not_configured_status tests/test_app.py::test_external_literature_search_reports_completed_status` passed: `2 passed in 3.05s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `17 passed in 82.29s`.
- The remote safe suite was completed as its documented component scripts: suite contracts passed, script catalog passed, secret file guard passed, handoff docs passed, generated file guard passed, focused coverage passed, pilot readiness `28 passed in 69.93s`, deployment contracts `1 passed in 1.63s`, research workflow primitives `17 passed in 82.29s`, research planning contracts `3 passed in 80.49s`, write audit `7 passed in 3.95s`, workflow job controls `3 passed in 107.41s`, tool bridge contracts `10 passed in 2.21s`, GraphRAG-lite `4 passed in 3.98s`, and context search `15 passed in 101.39s`.

## 2026-06-14 - Literature Search Empty Query Guard Fixture

Implemented in progress:

- Added a deterministic API-level literature search guard fixture for empty/punctuation-only queries.
- Verified `/research/literature/search` returns HTTP 400 with `Query must contain at least one searchable term` instead of running local or external search.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so literature search input validation stays covered before changing search behavior.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py backend/research/routes.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py backend/research/routes.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_literature_search_rejects_empty_query` passed: `1 passed in 4.15s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `18 passed in 83.32s`.
- The remote safe suite was completed as its documented component scripts: suite contracts passed, script catalog passed, secret file guard passed, handoff docs passed, generated file guard passed, focused coverage passed, pilot readiness `28 passed in 74.67s`, deployment contracts `1 passed in 1.77s`, research planning contracts `3 passed in 82.51s`, write audit `7 passed in 4.13s`, workflow job controls `3 passed in 106.66s`, tool bridge contracts `10 passed in 2.30s`, GraphRAG-lite `4 passed in 4.26s`, and context search `15 passed in 101.18s`.

## 2026-06-14 - Literature Search Limit And Ranking Fixture

Implemented in progress:

- Added a deterministic no-network literature search service fixture covering query-term deduplication, high-limit clamping, original query forwarding to external search, and combined local/external result ranking by score.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so literature search limit/ranking behavior stays covered before changing search behavior.
- Updated `codex_handoff/03_TODO.md` to keep workflow primitive coverage synchronized.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_literature_search_clamps_limit_and_sorts_combined_results` passed: `1 passed in 3.50s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `19 passed in 81.95s`.
- The remote safe suite was completed as its documented component scripts: suite contracts passed, script catalog passed, secret file guard passed, handoff docs passed, generated file guard passed, focused coverage passed, pilot readiness `28 passed in 69.70s`, deployment contracts `1 passed in 1.65s`, research planning contracts `3 passed in 85.58s`, write audit `7 passed in 3.53s`, workflow job controls `3 passed in 113.36s`, tool bridge contracts `10 passed in 2.15s`, GraphRAG-lite `4 passed in 4.26s`, and context search `15 passed in 102.36s`.

## 2026-06-14 - Literature Search Low Limit Truncation Fixture

Implemented in progress:

- Added a deterministic no-network literature search service fixture covering non-positive limit clamping to one result, final result truncation, score ordering, and the `not_requested` external status when external search is not requested.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so literature search lower-bound limit behavior stays covered before changing search behavior.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_literature_search_clamps_low_limit_and_truncates_results` passed: `1 passed in 3.72s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `20 passed in 83.47s`.
- The remote safe suite was completed as its documented component scripts: suite contracts passed, script catalog passed, secret file guard passed, generated file guard passed, pilot readiness `28 passed in 72.47s`, deployment contracts `1 passed in 1.72s`, research planning contracts `3 passed in 84.26s`, write audit `7 passed in 4.11s`, workflow job controls `3 passed in 108.24s`, tool bridge contracts `10 passed in 2.31s`, GraphRAG-lite `4 passed in 4.32s`, and context search `15 passed in 101.26s`.

## 2026-06-14 - Semantic Scholar Parser Fallback Fixture

Implemented in progress:

- Added a deterministic no-network Semantic Scholar parser fixture covering missing `paperId`, DOI fallback source ids, untitled paper fallback, empty-author filtering, missing venue/url defaults, abstract truncation, score offset, and metadata preservation.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so Semantic Scholar parser fallback behavior stays covered before changing external literature parsing.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_semantic_scholar_literature_item_parser_fallbacks` passed: `1 passed in 3.71s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `21 passed in 83.90s`.
- The remote safe suite was completed as its documented component scripts: suite contracts passed, script catalog passed, secret file guard passed, generated file guard passed, pilot readiness `28 passed in 68.46s`, deployment contracts `1 passed in 1.76s`, research planning contracts `3 passed in 85.30s`, write audit `7 passed in 4.13s`, workflow job controls `3 passed in 106.83s`, tool bridge contracts `10 passed in 2.20s`, GraphRAG-lite `4 passed in 4.42s`, and context search `15 passed in 101.68s`.

## 2026-06-14 - OpenAlex Parser Fallback Fixture

Implemented in progress:

- Added a deterministic no-network OpenAlex parser fixture covering display-name title fallback, id URL fallback, empty-author filtering, missing venue/year/abstract defaults, score floor behavior, and metadata preservation.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so OpenAlex parser fallback behavior stays covered before changing external literature parsing.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_openalex_literature_item_parser_fallbacks` passed: `1 passed in 3.57s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `22 passed in 85.58s`.
- The remote safe suite was completed as its documented component scripts: suite contracts passed, script catalog passed, secret file guard passed, generated file guard passed, pilot readiness `28 passed in 70.65s`, deployment contracts `1 passed in 1.77s`, research planning contracts `3 passed in 83.58s`, write audit `7 passed in 4.19s`, workflow job controls `3 passed in 107.55s`, tool bridge contracts `10 passed in 2.43s`, GraphRAG-lite `4 passed in 4.56s`, and context search `15 passed in 104.92s`.

## 2026-06-14 - arXiv Parser Fallback Fixture

Implemented in progress:

- Added a deterministic no-network arXiv parser fixture covering untitled preprint fallback, invalid published-date year handling, empty-author filtering, empty category handling, abstract normalization/truncation, score floor behavior, and metadata preservation.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so arXiv parser fallback behavior stays covered before changing external literature parsing.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_arxiv_literature_item_parser_fallbacks` passed: `1 passed in 4.00s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `23 passed in 90.12s`.
- The remote safe suite was completed as its documented component scripts: suite contracts passed, script catalog passed, secret file guard passed, generated file guard passed, pilot readiness `28 passed in 72.47s`, deployment contracts `1 passed in 1.63s`, research planning contracts `3 passed in 85.05s`, write audit `7 passed in 3.88s`, workflow job controls `3 passed in 105.60s`, tool bridge contracts `10 passed in 2.21s`, GraphRAG-lite `4 passed in 4.23s`, and context search `15 passed in 104.00s`.

## 2026-06-14 - OpenAlex Inverted Index Abstract Fixture

Implemented in progress:

- Added a deterministic no-network OpenAlex inverted-index abstract reconstruction fixture covering position ordering, duplicate-position overwrite behavior, and 1200-character truncation.
- Added the new test to `scripts/check_research_workflow_primitives.sh` so OpenAlex abstract reconstruction stays covered before changing external literature parsing.
- Did not call external APIs, install dependencies, start services, read secrets, or modify production data.
- Preserved the two pre-existing untracked root documents.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_openalex_inverted_index_abstract_reconstruction_edges` passed: `1 passed in 3.61s`.
- `bash scripts/check_focused_test_coverage.sh` passed: `All pytest tests are covered by focused check scripts.`
- `bash scripts/check_handoff_docs.sh` passed: `Handoff documents are synchronized.`
- `bash scripts/check_research_workflow_primitives.sh` passed: `24 passed in 85.33s`.
- The remote safe suite was completed as its documented component scripts: suite contracts passed, script catalog passed, secret file guard passed, generated file guard passed, pilot readiness `28 passed in 69.38s`, deployment contracts `1 passed in 1.72s`, research planning contracts `3 passed in 83.73s`, write audit `7 passed in 4.03s`, workflow job controls `3 passed in 108.64s`, tool bridge contracts `10 passed in 2.20s`, GraphRAG-lite `4 passed in 4.24s`, and context search `15 passed in 103.31s`.

## 2026-06-14 - Related Work Service Contract Coverage

Implemented in progress:

- Added no-network service-level contract tests for related-work query cleaning, default query fallback, query length clamping, missing external-search actions, row sorting/truncation, and literature metadata preservation.
- Added the new tests and `backend/research/services/related_work_service.py` lint coverage to `scripts/check_research_workflow_primitives.sh`.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` passed after formatting the new tests.
- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py` passed.
- Focused related-work service pytest passed: `3 passed in 3.25s`.
- `bash scripts/check_research_workflow_primitives.sh` passed: `27 passed in 85.49s`.
- Fast guards passed: focused test coverage, suite contracts, script catalog, handoff docs, secret file guard, generated file guard, and `git --no-pager diff --check`.
- The remote safe suite was completed as its documented component scripts: pilot readiness `28 passed in 76.87s`, deployment contracts `1 passed in 1.79s`, research planning contracts `3 passed in 85.29s`, write audit `7 passed in 4.00s`, workflow job controls `3 passed in 111.31s`, tool bridge contracts `10 passed in 2.43s`, GraphRAG-lite `4 passed in 4.31s`, and context search `15 passed in 102.34s`.

## 2026-06-14 - Novelty Service Contract Coverage

Implemented in progress:

- Added no-network service-level contract tests for novelty overlap scoring, external overlap status handling, missing-search actions, risk levels, and recommended actions.
- Added the new tests and `backend/research/services/novelty_service.py` lint coverage to `scripts/check_research_workflow_primitives.sh`.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` passed after formatting the new tests.
- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py` passed.
- Focused novelty service pytest passed after fixture correction: `3 passed in 3.62s`.
- `bash scripts/check_research_workflow_primitives.sh` passed: `30 passed in 89.98s`.
- Fast guards passed: focused test coverage, suite contracts, script catalog, handoff docs, secret file guard, generated file guard, and `git --no-pager diff --check`.
- The remote safe suite was completed as its documented component scripts: pilot readiness `28 passed in 70.82s`, deployment contracts `1 passed in 1.65s`, research planning contracts `3 passed in 86.70s`, write audit `7 passed in 3.65s`, workflow job controls `3 passed in 109.64s`, tool bridge contracts `10 passed in 2.35s`, GraphRAG-lite `4 passed in 4.17s`, and context search `15 passed in 106.07s`.

## 2026-06-15 - Structured Extraction Prompt Contract Coverage

Implemented in progress:

- Added a no-network prompt-construction contract test for structured paper-card extraction evidence limits, per-evidence text truncation, and schema hint presence.
- Added the new test and `backend/research/services/structured_extraction_service.py` lint coverage to `scripts/check_research_workflow_primitives.sh`.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` passed.
- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py backend/research/services/structured_extraction_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py backend/research/services/structured_extraction_service.py` passed.
- Focused structured-extraction prompt pytest passed: `1 passed in 4.27s`.
- `bash scripts/check_research_workflow_primitives.sh` passed: `31 passed in 88.24s`.
- Fast guards passed: focused test coverage, suite contracts, script catalog, handoff docs, secret file guard, generated file guard, and `git --no-pager diff --check`.
- The remote safe suite was completed as its documented component scripts: pilot readiness `28 passed in 77.03s`, deployment contracts `1 passed in 1.72s`, research planning contracts `3 passed in 87.89s`, write audit `7 passed in 4.07s`, workflow job controls `3 passed in 131.51s`, tool bridge contracts `10 passed in 2.17s`, GraphRAG-lite `4 passed in 4.53s`, and context search `15 passed in 100.64s`.

## 2026-06-15 - Gap And Idea Service Contract Coverage

Implemented in progress:

- Added no-network service-level contract tests for gap title building, importance/unsolved explanations, possible approaches, idea variant generation, text shortening, and gap/evidence lineage preservation.
- Added the new tests and `backend/research/services/gap_service.py` plus `backend/research/services/idea_service.py` lint coverage to `scripts/check_research_workflow_primitives.sh`.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` passed.
- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py backend/research/services/structured_extraction_service.py backend/research/services/gap_service.py backend/research/services/idea_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py backend/research/services/structured_extraction_service.py backend/research/services/gap_service.py backend/research/services/idea_service.py` passed.
- Focused gap/idea service pytest passed: `2 passed in 4.29s`.
- `bash scripts/check_research_workflow_primitives.sh` passed: `33 passed in 87.57s`.
- Fast guards passed: focused test coverage, suite contracts, script catalog, handoff docs, secret file guard, generated file guard, and `git --no-pager diff --check`.
- The remote safe suite was completed as its documented component scripts: pilot readiness `28 passed in 76.30s`, deployment contracts `1 passed in 1.63s`, research planning contracts `3 passed in 86.28s`, write audit `7 passed in 3.92s`, workflow job controls `3 passed in 116.21s`, tool bridge contracts `10 passed in 2.42s`, GraphRAG-lite `4 passed in 4.50s`, and context search `15 passed in 107.65s`.

## 2026-06-15 - Paper Card Heuristic Contract Coverage

Implemented in progress:

- Added service-level contract tests for paper-card heuristic evidence-field mapping, problem fallback behavior, keyword collection, and missing input errors.
- Added the new tests and `backend/research/services/paper_card_service.py` lint coverage to `scripts/check_research_workflow_primitives.sh`.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` passed after formatting the new tests.
- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py backend/research/services/structured_extraction_service.py backend/research/services/gap_service.py backend/research/services/idea_service.py backend/research/services/paper_card_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py backend/research/services/structured_extraction_service.py backend/research/services/gap_service.py backend/research/services/idea_service.py backend/research/services/paper_card_service.py` passed.
- Focused paper-card service pytest passed: `2 passed in 4.91s`.
- `bash scripts/check_research_workflow_primitives.sh` passed: `35 passed in 87.53s`.
- Fast guards passed: focused test coverage, suite contracts, script catalog, handoff docs, secret file guard, generated file guard, and `git --no-pager diff --check`.
- The remote safe suite was completed as its documented component scripts: pilot readiness `28 passed in 66.84s`, deployment contracts `1 passed in 1.68s`, research planning contracts `3 passed in 84.31s`, write audit `7 passed in 3.79s`, workflow job controls `3 passed in 110.86s`, tool bridge contracts `10 passed in 2.52s`, GraphRAG-lite `4 passed in 4.30s`, and context search `15 passed in 114.28s`.

## 2026-06-15 - Review And Experiment Service Contract Coverage

Implemented in progress:

- Added a service-level contract test for review and experiment-plan creation, missing idea errors, idea status progression, copied experiment fields, and list retrieval.
- Added the new test and `backend/research/services/review_service.py` plus `backend/research/services/experiment_service.py` lint coverage to `scripts/check_research_workflow_primitives.sh`.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` passed.
- `.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py backend/research/services/structured_extraction_service.py backend/research/services/gap_service.py backend/research/services/idea_service.py backend/research/services/paper_card_service.py backend/research/services/review_service.py backend/research/services/experiment_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py backend/research/services/structured_extraction_service.py backend/research/services/gap_service.py backend/research/services/idea_service.py backend/research/services/paper_card_service.py backend/research/services/review_service.py backend/research/services/experiment_service.py` passed.
- Focused review/experiment service pytest passed: `1 passed in 3.96s`.
- `bash scripts/check_research_workflow_primitives.sh` passed: `36 passed in 88.61s`.
- Fast guards passed: focused test coverage, suite contracts, script catalog, handoff docs, secret file guard, generated file guard, and `git --no-pager diff --check`.
- The remote safe suite was completed as its documented component scripts: pilot readiness `28 passed in 74.61s`, deployment contracts `1 passed in 1.79s`, research planning contracts `3 passed in 90.20s`, write audit `7 passed in 4.09s`, workflow job controls `3 passed in 114.38s`, tool bridge contracts `10 passed in 2.17s`, GraphRAG-lite `4 passed in 4.01s`, and context search `15 passed in 107.17s`.

## 2026-06-15 - Proposal Service Contract Coverage

Implemented in progress:

- Added no-network service-level contract tests for proposal draft section synthesis, proposal readiness scoring/missing-evidence decisions, and proposal revision action generation.
- Added the new tests and proposal service lint coverage to `scripts/check_research_proposal_contracts.sh`.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` passed after formatting the new tests.
- `.venv/bin/ruff check tests/test_app.py backend/research/routes.py backend/research/services/proposal_service.py backend/research/services/proposal_review_service.py backend/research/services/proposal_revision_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/routes.py backend/research/services/proposal_service.py backend/research/services/proposal_review_service.py backend/research/services/proposal_revision_service.py` passed.
- Focused proposal service pytest passed: `3 passed in 3.68s`.
- `bash scripts/check_research_proposal_contracts.sh` passed: `4 passed in 623.39s`; the original proposal end-to-end test is the dominant long-suite bottleneck.
- `bash scripts/check_remote_long_suite.sh` passed: focused coverage plus proposal contracts, `4 passed in 592.72s`.
- `bash scripts/check_remote_safe_suite.sh` passed. Pytest metrics inside the remote-safe suite: pilot readiness `28 passed in 73.73s`, deployment contracts `1 passed in 1.66s`, research workflow primitives `36 passed in 87.63s`, research planning contracts `3 passed in 87.88s`, write audit `7 passed in 3.12s`, workflow job controls `3 passed in 110.76s`, tool bridge contracts `10 passed in 2.20s`, GraphRAG-lite `4 passed in 4.34s`, and context search `15 passed in 104.03s`.
- Test-effect metrics for this slice: 3 new no-network proposal service contract tests, proposal focused suite increased from 1 to 4 tests, and default remote-safe pytest coverage remained green across 107 selected tests.

## 2026-06-15 - Proposal And Delivery Loop Test Split

Implemented in progress:

- Renamed the long proposal end-to-end test to `test_project_delivery_loop_bundles_proposal_to_pilot_handoff` so its project-delivery scope is explicit.
- Kept `scripts/check_research_proposal_contracts.sh` focused on proposal service contracts and added `scripts/check_project_delivery_loop.sh` for the long end-to-end delivery loop.
- Added the new long check to `scripts/check_remote_long_suite.sh`, `scripts/check_suite_contracts.sh`, and the README check-script catalog.
- Preserved the two pre-existing untracked root documents and did not touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff format tests/test_app.py` passed.
- `.venv/bin/ruff check tests/test_app.py backend/research/routes.py backend/research/services/proposal_service.py backend/research/services/proposal_review_service.py backend/research/services/proposal_revision_service.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py backend/research/routes.py backend/research/services/proposal_service.py backend/research/services/proposal_review_service.py backend/research/services/proposal_revision_service.py` passed.
- Split proposal-focused checks from the full delivery loop: `bash scripts/check_research_proposal_contracts.sh` passed with `3 passed in 3.27s`, compared with the prior proposal suite runtime of `4 passed in 623.39s`.
- Added and verified `bash scripts/check_project_delivery_loop.sh`: `1 passed in 639.78s`, preserving the full proposal-to-pilot handoff coverage as an explicit long check.
- `bash scripts/check_remote_long_suite.sh` passed with focused coverage, proposal contracts `3 passed in 1.69s`, and delivery loop `1 passed in 627.79s`.
- `bash scripts/check_remote_safe_suite.sh` passed. Pytest metrics inside the remote-safe suite: pilot readiness `28 passed in 76.37s`, deployment contracts `1 passed in 1.70s`, research workflow primitives `36 passed in 91.14s`, research planning contracts `3 passed in 84.67s`, write audit `7 passed in 4.02s`, workflow job controls `3 passed in 113.52s`, tool bridge contracts `10 passed in 2.15s`, GraphRAG-lite `4 passed in 4.28s`, and context search `15 passed in 107.51s`.
- Test-effect metrics for this slice: proposal-focused feedback now runs in seconds, full delivery-loop coverage remains available in the long suite, and default remote-safe pytest coverage remained green across 107 selected tests.


## 2026-06-15 - Isolated Project Delivery Loop Test Data

Implemented in progress:

- Made `scripts/check_project_delivery_loop.sh` use a per-run ignored test data directory for `RESEARCH_DB_URL` and `PAPER_UPLOAD_DIR` instead of the accumulated remote development database.
- Forced `EXTERNAL_LITERATURE_SEARCH_ENABLED=false` for the delivery-loop check so `.env` or remote runtime settings cannot turn the test into a network-dependent run.
- Added a research execution plan setup step inside `test_project_delivery_loop_bundles_proposal_to_pilot_handoff`, removing its hidden dependency on historical database state.
- Changed the delivery-loop and long-suite tail calls to `exec` so nested shell wrappers do not leave pytest hanging after the test process completes.
- Preserved the two pre-existing untracked root documents and did not read or print any `.env` or secret values.

Verification completed:

- Historical default database scale that explained the old project-level scan cost: 5123 papers, 18898 evidences, 5999 gaps, 6888 ideas, 3555 experiment plans, 17975 research tasks, and 60007 graph edges.
- Before isolation, `bash scripts/check_project_delivery_loop.sh` passed in `1 passed in 639.78s`; the long suite delivery-loop segment passed in `1 passed in 627.79s`.
- During isolation, the test failed fast on a clean database with `readiness_level=nearly_ready` and missing `Research execution plan`, proving the old pass depended on historical remote data.
- After adding the research plan setup, the isolated direct pytest run passed: `1 passed in 10.03s`.
- `PROJECT_DELIVERY_LOOP_TIMEOUT_SECONDS=60 bash scripts/check_project_delivery_loop.sh` passed: `1 passed in 7.99s`.
- `bash scripts/check_research_proposal_contracts.sh` passed: `3 passed in 1.71s`.
- `bash scripts/check_remote_long_suite.sh` passed with focused coverage, proposal contracts `3 passed in 1.81s`, and delivery loop `1 passed in 8.43s`.
- `bash scripts/check_remote_safe_suite.sh` passed. Pytest metrics inside the remote-safe suite: pilot readiness `28 passed in 11.99s`, deployment contracts `1 passed in 1.78s`, research workflow primitives `36 passed in 7.25s`, research planning contracts `3 passed in 4.25s`, write audit `7 passed in 3.91s`, workflow job controls `3 passed in 3.81s`, tool bridge contracts `10 passed in 2.27s`, GraphRAG-lite `4 passed in 3.22s`, and context search `15 passed in 8.42s`.
- Test-effect metrics for this slice: delivery-loop check dropped from about 10.7 minutes to under 10 seconds, long-suite delivery-loop coverage is now isolated and repeatable, and default remote-safe pytest coverage remained green across 107 selected tests.


## 2026-06-15 - Bundle Readiness Transition Contract

Implemented in progress:

- Added an explicit project-bundle readiness transition assertion inside `test_project_delivery_loop_bundles_proposal_to_pilot_handoff`.
- The delivery loop now verifies that a fully prepared handoff without a research execution plan reports `nearly_ready`, a readiness score below 1.0, `Research execution plan` in `missing_required`, and a `research_plan` quick action before the plan is created.
- The same test then creates the research plan and verifies the final `delivery_ready` state, keeping the hidden historical-data dependency closed.
- Preserved the two pre-existing untracked root documents and did not read or print any `.env` or secret values.

Verification completed:

- `PROJECT_DELIVERY_LOOP_TIMEOUT_SECONDS=60 bash scripts/check_project_delivery_loop.sh` passed: `1 passed in 10.16s`.
- `bash scripts/check_remote_long_suite.sh` passed with focused coverage, proposal contracts `3 passed in 1.67s`, and delivery loop `1 passed in 8.36s`.
- `bash scripts/check_remote_safe_suite.sh` passed. Pytest metrics inside the remote-safe suite: pilot readiness `28 passed in 14.51s`, deployment contracts `1 passed in 1.72s`, research workflow primitives `36 passed in 7.75s`, research planning contracts `3 passed in 4.90s`, write audit `7 passed in 4.02s`, workflow job controls `3 passed in 4.77s`, tool bridge contracts `10 passed in 2.22s`, GraphRAG-lite `4 passed in 3.01s`, and context search `15 passed in 9.01s`.
- Test-effect metrics for this slice: one more user-visible readiness transition is covered in the isolated delivery-loop check, and default remote-safe pytest coverage remained green across 107 selected tests.


## 2026-06-15 - Product Effect Smoke Evaluation

Implemented in progress:

- Ran the existing end-to-end smoke workflow in an isolated in-process mode to evaluate product-level behavior rather than only unit-test coverage.
- Ran the same smoke workflow against a temporary real HTTP `uvicorn` service on `127.0.0.1:18081`, using isolated SQLite and upload directories under `data/test-runs/`.
- Added `docs/product_effect_report.md` to summarize current product target, smoke metrics, strengths, gaps, readiness estimate, and recommended next steps.
- Did not read or print `.env`, token, cookie, password, private key, or credential files; the temporary HTTP service was closed by `timeout` and no service process was left running.

Verification completed:

- In-process smoke passed with service readiness `ready`, Workbench available, `119` tool-manifest entries, `119` MCP bridge tools, `3` gaps, `6` ideas, proposal review `ready_for_advisor_review` at score `0.92`, experiment analysis `supports_hypothesis`, project bundle `71` files, project-bundle readiness `delivery_ready` at score `1.0`, and `100` graph nodes / `100` graph edges in the final summary.
- Real HTTP smoke passed against temporary `uvicorn` with the same key metrics: service readiness `ready`, Workbench available, `3` gaps, `6` ideas, proposal review `ready_for_advisor_review`, readiness decision `needs_targeted_work`, quality-gate decision `de_risk_novelty`, advisor chat intent `risk_review`, project bundle `71` files, project-bundle readiness `delivery_ready` at score `1.0`, and `100` graph nodes / `100` graph edges.
- The temporary HTTP server shut down cleanly after `timeout`; `pgrep` found no remaining `uvicorn`, `smoke_api`, pytest, or check-suite processes.
- Test-effect metrics for this slice: the product is now verified in both TestClient and real HTTP modes with isolated data, moving the project from pure engineering validation toward demo-readiness validation.


## 2026-06-15 - Product Smoke Runbook

Implemented in progress:

- Added `scripts/check_product_effect_smoke.sh`, an isolated product-effect smoke entrypoint that defaults to a per-run SQLite database and upload directory under `data/test-runs/`.
- Added `docs/demo_runbook.md` with safe in-process and temporary HTTP smoke workflows, expected indicators, baseline metrics, and demo-readiness interpretation.
- Updated the README check-script catalog and verification section so the product-effect smoke is discoverable.
- Preserved the two pre-existing untracked root documents and did not read or print any `.env` or secret values.

Verification completed:

- `PRODUCT_EFFECT_SMOKE_TIMEOUT_SECONDS=300 bash scripts/check_product_effect_smoke.sh` passed with isolated test data and external literature search disabled by default.
- Key metrics from the new script: service readiness `ready`, Workbench available, `119` tool-manifest entries, `119` MCP bridge tools, `3` gaps, `6` ideas, proposal review `ready_for_advisor_review` at score `0.92`, experiment analysis `supports_hypothesis`, project bundle `71` files, project-bundle readiness `delivery_ready` at score `1.0`, and `100` graph nodes / `100` graph edges.
- Test-effect metrics for this slice: product-effect smoke is now a repeatable check script and demo runbook entry instead of an ad hoc command sequence.


## 2026-06-15 - Workbench Product Surface Contract

Implemented in progress:

- Extended `test_workbench_static_assets_are_served` to verify the Workbench main product path exposes stable navigation sections from Pilot Launch through Dossier.
- Added CSS surface assertions for the Workbench shell, grid layout, controls grid, and responsive breakpoint so the static product entrypoint keeps a desktop/mobile layout contract.
- Preserved the two pre-existing untracked root documents and did not read or print any `.env` or secret values.

Verification completed:

- `bash scripts/check_pilot_readiness.sh` passed: `28 passed in 79.36s`.
- `bash scripts/check_remote_safe_suite.sh` passed. Pytest metrics inside the remote-safe suite: pilot readiness `28 passed in 78.48s`, deployment contracts `1 passed in 1.68s`, research workflow primitives `36 passed in 100.98s`, research planning contracts `3 passed in 100.35s`, write audit `7 passed in 3.59s`, workflow job controls `3 passed in 122.56s`, tool bridge contracts `10 passed in 2.22s`, GraphRAG-lite `4 passed in 4.45s`, and context search `15 passed in 111.76s`.
- Test-effect metrics for this slice: the user-visible Workbench shell now has a focused product-surface contract, and default remote-safe pytest coverage remained green across 107 selected tests.


## 2026-06-15 - Representative Markdown Product Smoke

Implemented in progress:

- Added representative paper fixture support to `scripts/smoke_api.py` through `--paper-file` and exposed it in `scripts/check_product_effect_smoke.sh` as `PRODUCT_EFFECT_SMOKE_PAPER_FILE=/path/to/paper.md`.
- Updated README and `docs/demo_runbook.md` so the product-effect smoke can be run against a realistic local paper fixture, not only the built-in deterministic smoke paper.
- Improved Markdown ingestion so ATX headings such as `## Limitations` are normalized before section detection.
- Added `Future Work` / `Future Directions` / `Next Steps` as explicit section patterns that map to `future_work` evidence and application-gap mining.
- Added `test_markdown_gap_sections_are_mined_from_headings` and registered it in `scripts/check_research_workflow_primitives.sh`, including ruff coverage for `document_ingestion.py`.
- Preserved the two pre-existing untracked root documents and did not read or print any `.env`, token, cookie, password, private key, or credential values.

Verification completed:

- Targeted regression test passed with isolated SQLite/upload directories: `tests/test_app.py::test_markdown_gap_sections_are_mined_from_headings` -> `1 passed in 4.29s`.
- Representative Markdown product-effect smoke passed with `PRODUCT_EFFECT_SMOKE_PAPER_FILE=/tmp/raa_gap_rich_paper.md`: service readiness `ready`, Workbench available, `119` tool-manifest entries, `119` bridge tools, `3` gaps, `6` ideas, proposal review `ready_for_advisor_review` at score `0.92`, experiment analysis `supports_hypothesis`, evidence ledger coverage `0.24`, project bundle `71` files, project-bundle readiness `delivery_ready` at score `1.0`, and `100` graph nodes / `100` graph edges.
- Default product-effect smoke still passed after the ingestion change: service readiness `ready`, Workbench available, `3` gaps, `6` ideas, proposal review score `0.92`, project bundle `71` files, project-bundle readiness score `1.0`, and `100` graph nodes / `100` graph edges.
- `bash scripts/check_script_catalog.sh` passed: check script catalog is synchronized.
- `bash scripts/check_research_workflow_primitives.sh` passed after registering the new test: `37 passed in 99.98s`.
- `bash scripts/check_remote_safe_suite.sh` passed. Pytest metrics inside the remote-safe suite: pilot readiness `28 passed in 99.28s`, deployment contracts `1 passed in 1.35s`, research workflow primitives `37 passed in 90.24s`, research planning contracts `3 passed in 95.83s`, write audit `7 passed in 4.72s`, workflow job controls `3 passed in 153.72s`, tool bridge contracts `10 passed in 2.25s`, GraphRAG-lite `4 passed in 4.44s`, and context search `15 passed in 110.32s`.
- Test-effect metrics for this slice: representative Markdown papers with explicit Limitations/Future Work sections now produce mined gaps in both a focused regression test and the full product smoke, raising the selected remote-safe pytest coverage from 107 to 108 tests.


## 2026-06-15 - Product Effect Scorecard

Implemented in progress:

- Added `build_product_effect_scorecard` to `scripts/smoke_api.py` so every product smoke reports an overall product-effect score, band, weighted dimension scores, pass/fail checks, and failed-check names.
- Added `product_effect_score`, `product_effect_band`, and `product_effect_scorecard` to the smoke JSON summary.
- Added `test_product_effect_scorecard_separates_quality_from_completion` so the scorecard distinguishes completed workflow/delivery paths from weaker evidence and claim-validation quality signals.
- Registered the new scorecard test in `scripts/check_research_workflow_primitives.sh` and added `scripts/smoke_api.py` to that script's ruff checks.
- Updated README, `docs/demo_runbook.md`, and `docs/product_effect_report.md` with scorecard interpretation and current baseline metrics.
- Preserved the two pre-existing untracked root documents and did not read or print any `.env`, token, cookie, password, private key, or credential values.

Verification completed:

- Targeted scorecard and Markdown gap tests passed with isolated SQLite/upload directories: `2 passed in 4.35s`.
- `bash scripts/check_focused_test_coverage.sh` passed: all pytest tests are covered by focused check scripts.
- `timeout 240 bash scripts/check_research_workflow_primitives.sh` passed: `38 passed in 91.67s`.
- Default product-effect smoke passed with scorecard metrics: overall `0.8754`, band `pilot_effective`, foundation `1.0`, research workflow `1.0`, quality signal `0.5018`, delivery loop `1.0`, failed checks `[]`.
- Representative Markdown product-effect smoke passed with `PRODUCT_EFFECT_SMOKE_PAPER_FILE=/tmp/raa_gap_rich_paper.md`: overall `0.8854`, band `pilot_effective`, foundation `1.0`, research workflow `1.0`, quality signal `0.5418`, delivery loop `1.0`, `3` gaps, `6` ideas, proposal review score `0.92`, evidence ledger coverage `0.24`, project bundle readiness score `1.0`, and `100` graph nodes / `100` graph edges.
- `bash scripts/check_remote_safe_suite.sh` passed. Pytest metrics inside the remote-safe suite: pilot readiness `28 passed in 74.55s`, deployment contracts `1 passed in 1.30s`, research workflow primitives `38 passed in 90.11s`, research planning contracts `3 passed in 89.22s`, write audit `7 passed in 3.90s`, workflow job controls `3 passed in 114.61s`, tool bridge contracts `10 passed in 2.19s`, GraphRAG-lite `4 passed in 4.43s`, and context search `15 passed in 111.19s`.
- Product-effect interpretation for this slice: the product is now measurably pilot-effective at backend workflow completion, while the quality-signal dimension remains the main gap to improve next.


## 2026-06-15 - Mixed Claim Validation Smoke

Implemented in progress:

- Updated `scripts/smoke_api.py` so the product-effect smoke records mixed claim-validation outcomes: one `needs_more_evidence` result and one `supported` result.
- Adjusted the product-effect scorecard so claim-validation quality is driven by recorded result count plus readiness/quality-gate claim-validation scores, not by rewarding a single needs-more-evidence status.
- Added a quality-dimension guard to score bands: `demo_ready` now requires overall score `>= 0.9` and quality signal `>= 0.70`; otherwise high-completion runs remain `pilot_effective`.
- Updated the scorecard regression test to preserve that quality gate semantics.
- Preserved the two pre-existing untracked root documents and did not read or print any `.env`, token, cookie, password, private key, or credential values.

Verification completed:

- Targeted scorecard and Markdown gap tests passed with isolated SQLite/upload directories: `2 passed in 3.85s`.
- Default product-effect smoke passed with mixed claim validation: `2` claim-validation result events, `1` supported claim, `1` needs-more-evidence claim, readiness claim-validation score `0.675`, quality-gate claim-validation score `0.675`, readiness score `0.6859`, quality-gate score `0.699`, top ranked idea score `3.665`, product-effect score `0.9056`, band `pilot_effective`, quality signal `0.6225`, and failed checks `[]`.
- Representative Markdown product-effect smoke passed with mixed claim validation: evidence ledger coverage `0.24`, readiness claim-validation score `0.675`, quality-gate score `0.699`, product-effect score `0.9156`, band `pilot_effective`, quality signal `0.6625`, `3` gaps, `6` ideas, project-bundle readiness score `1.0`, and `100` graph nodes / `100` graph edges.
- `bash scripts/check_research_workflow_primitives.sh` passed after the mixed-validation update: `38 passed in 92.65s`.
- `bash scripts/check_script_catalog.sh`, `bash scripts/check_handoff_docs.sh`, and `git diff --check` passed.
- `bash scripts/check_remote_safe_suite.sh` passed. Pytest metrics inside the remote-safe suite: pilot readiness `28 passed in 75.28s`, deployment contracts `1 passed in 1.36s`, research workflow primitives `38 passed in 94.75s`, research planning contracts `3 passed in 88.33s`, write audit `7 passed in 3.93s`, workflow job controls `3 passed in 111.01s`, tool bridge contracts `10 passed in 2.17s`, GraphRAG-lite `4 passed in 4.39s`, and context search `15 passed in 111.45s`.
- Product-effect interpretation for this slice: mixed claim validation improved the quality-signal dimension while keeping the overall band honest; the remaining path to `demo_ready` is improving evidence coverage and claim support quality above the `0.70` quality-signal gate.


## 2026-06-15 - Source Paper Evidence Context

Implemented in progress:

- Updated `IdeaService` so generated ideas carry a bounded set of evidence IDs from the source paper, preserving the gap-triggering evidence first and then adding prioritized context evidence such as limitations, future work, problems, results, and methods.
- Added `test_idea_service_carries_source_paper_evidence_context` to ensure source-paper evidence is carried into ideas without leaking evidence from unrelated papers.
- Registered the new test in `scripts/check_research_workflow_primitives.sh`.
- Updated context-search score-breakdown tests so random local-vector collisions may yield `0.0` vector contribution while still requiring lexical/bonus/phrase totals to match the visible score.
- Updated `docs/demo_runbook.md` and `docs/product_effect_report.md` with the new backend demo-ready product-effect metrics.
- Preserved the two pre-existing untracked root documents and did not read or print any `.env`, token, cookie, password, private key, or credential values.

Verification completed:

- Targeted idea-service evidence context tests passed with isolated SQLite/upload directories: `2 passed in 4.11s`.
- Default product-effect smoke passed with broader source-paper evidence context: evidence ledger coverage `0.44`, readiness score `0.7791`, quality-gate score `0.725`, readiness claim-validation score `0.675`, top ranked idea score `3.785`, product-effect score `0.9289`, band `demo_ready`, quality signal `0.7157`, `3` gaps, `6` ideas, project-bundle readiness score `1.0`, and `100` graph nodes / `100` graph edges.
- Representative Markdown product-effect smoke passed with broader source-paper evidence context: evidence ledger coverage `0.49`, claim-validation support count `3`, readiness score `0.7791`, quality-gate score `0.725`, product-effect score `0.931`, band `demo_ready`, quality signal `0.724`, `3` gaps, `6` ideas, project-bundle readiness score `1.0`, and `100` graph nodes / `100` graph edges.
- `bash scripts/check_context_search_evaluations.sh` passed after the score-breakdown stability adjustment: `15 passed in 111.41s`.
- `bash scripts/check_remote_safe_suite.sh` passed. Pytest metrics inside the remote-safe suite: pilot readiness `28 passed in 76.78s`, deployment contracts `1 passed in 1.39s`, research workflow primitives `39 passed in 96.59s`, research planning contracts `3 passed in 94.20s`, write audit `7 passed in 4.19s`, workflow job controls `3 passed in 115.60s`, tool bridge contracts `10 passed in 2.14s`, GraphRAG-lite `4 passed in 4.56s`, and context search `15 passed in 108.51s`.
- Product-effect interpretation for this slice: the backend workflow is now demo-ready by the product-effect scorecard, while Workbench browser inspection, human scientific review, external literature quality, and production hardening remain outside this backend-only score.

## 2026-06-16 - Workbench Demo Path Contract

Implemented in progress:

- Attempted a browser-level Workbench inspection through a temporary isolated `uvicorn` service and SSH tunnel, then stopped both temporary processes after the in-app browser policy rejected direct access to the forwarded `127.0.0.1:18082` target.
- Added `test_workbench_user_path_contract_supports_pilot_demo_loop` to verify the Workbench page has an ordered pilot demo path from Pilot Launch through Onboarding, Ingest, Workflow, Profile, Search, Advisor, Jobs, and Dossier.
- The new contract also verifies the controls needed for paper intake, async workflow launch, project context, advisor support, execution tracking, and delivery closeout are present as a coherent product path.
- Registered the new Workbench path contract in `scripts/check_pilot_readiness.sh`, increasing the pilot readiness focused check from `28` selected tests to `29`.
- Preserved the two pre-existing untracked root documents and did not read or print any `.env`, token, cookie, password, private key, or credential values.

Verification completed:

- Targeted Workbench user-path contract passed: `tests/test_app.py::test_workbench_user_path_contract_supports_pilot_demo_loop` -> `1 passed in 4.28s`.
- Workbench static asset and user-path tests passed together: `2 passed in 4.39s`.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check tests/test_app.py` passed.
- `bash -n scripts/check_pilot_readiness.sh` passed.
- `bash scripts/check_focused_test_coverage.sh` passed: all pytest tests are covered by focused check scripts.
- `bash scripts/check_pilot_readiness.sh` passed: `29 passed in 86.63s`.
- Product-effect interpretation for this slice: Workbench is still pending true human/browser visual inspection, but its static product path now has a focused regression guard that protects the demo flow from paper ingest to delivery closeout.

## 2026-06-16 - Real HTTP Product-Effect Baseline

Implemented in progress:

- Ran the product-effect smoke against a temporary real `uvicorn` service on `127.0.0.1:18083` using an isolated SQLite database and isolated paper upload directory under `data/test-runs/`.
- Confirmed the temporary service was stopped after the smoke and that no `uvicorn`, smoke, pytest, or focused-check process remained running.
- Updated `docs/product_effect_report.md` so the Real HTTP Smoke section matches the latest source-paper evidence context baseline instead of the older pre-demo-ready metrics.
- Preserved the two pre-existing untracked root documents and did not read or print any `.env`, token, cookie, password, private key, or credential values.

Verification completed:

- `PRODUCT_EFFECT_SMOKE_BASE_URL=http://127.0.0.1:18083 bash scripts/check_product_effect_smoke.sh` passed with exit code `0`.
- Real HTTP service readiness was `ready`, Workbench available was `true`, tool manifest count was `119`, and MCP bridge tool count was `119`.
- Workflow metrics: `3` gaps, `6` ideas, `6` novelty checks, `6` experiment plans, proposal review `ready_for_advisor_review` at score `0.92`, and experiment analysis `supports_hypothesis`.
- Quality metrics: evidence ledger coverage `0.44`, readiness score `0.7791`, quality-gate score `0.725`, readiness claim-validation score `0.675`, and quality-gate claim-validation score `0.675`.
- Delivery metrics: project bundle `71` files, readiness level `delivery_ready`, bundle readiness score `1.0`, research plan items `3`, plan tasks `9`, graph context `100` nodes / `100` edges.
- Product-effect scorecard: overall `0.9289`, band `demo_ready`, foundation `1.0`, research workflow `1.0`, quality signal `0.7157`, delivery loop `1.0`, failed checks `[]`.
- Product-effect interpretation for this slice: the backend is now demo-ready not only in TestClient/in-process mode, but also through a temporary real HTTP FastAPI service.

## 2026-06-16 - Typed Evidence Routing And Packet Task Pinning

Implemented in progress:

- Added typed evidence-to-claim routing in `IdeaEvidenceLedgerService` so claims can use conservative evidence-type matches when word overlap is too weak, for example method claims using method/dataset/problem evidence and novelty claims using limitation/future-work/comparison evidence.
- Added a focused regression test proving source-paper evidence supports multiple ledger claims without leaking evidence from unrelated papers.
- Updated research-packet open-task selection so latest experiment-analysis, decision-memo, evidence-ledger, and claim-validation queue tasks are pinned into the packet before filling the remaining task list by priority.
- Added a crowded-task regression test proving the latest evidence-ledger task remains visible in the research packet even when more than 20 higher-priority tasks exist.
- Registered the new tests and `evidence_ledger_service.py` in `scripts/check_research_workflow_primitives.sh`.
- Updated `docs/demo_runbook.md` and `docs/product_effect_report.md` with the new default, representative Markdown, and real HTTP product-effect baselines.
- Preserved the two pre-existing untracked root documents and did not read or print any `.env`, token, cookie, password, private key, or credential values.

Verification completed:

- Targeted typed-evidence and research-packet tests passed together: `2 passed in 5.08s`.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check tests/test_app.py backend/research/services/evidence_ledger_service.py backend/research/routes.py` passed.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check tests/test_app.py backend/research/services/evidence_ledger_service.py backend/research/routes.py` passed.
- `bash scripts/check_focused_test_coverage.sh` passed: all pytest tests are covered by focused check scripts.
- `bash scripts/check_research_workflow_primitives.sh` passed: `41 passed in 99.14s`.
- Default product-effect smoke passed after the research-packet regression was fixed: evidence ledger coverage `0.54`, readiness score `0.7791`, quality-gate score `0.725`, product-effect score `0.9331`, band `demo_ready`, quality signal `0.7323`, `3` gaps, `6` ideas, project-bundle readiness score `1.0`, and `100` graph nodes / `100` graph edges.
- Representative Markdown product-effect smoke passed: evidence ledger coverage `0.59`, claim-validation support count `3`, product-effect score `0.9352`, band `demo_ready`, quality signal `0.7407`, `3` gaps, `6` ideas, project-bundle readiness score `1.0`, and `100` graph nodes / `100` graph edges.
- Real HTTP product-effect smoke passed against a temporary `uvicorn` service on `127.0.0.1:18084` with exit code `0`: evidence ledger coverage `0.54`, product-effect score `0.9331`, band `demo_ready`, quality signal `0.7323`, project bundle `71` files, and graph context `100` nodes / `100` edges.
- `bash scripts/check_remote_safe_suite.sh` passed. Pytest metrics inside the remote-safe suite: pilot readiness `29 passed in 88.51s`, deployment contracts `1 passed in 1.40s`, research workflow primitives `41 passed in 95.44s`, research planning contracts `3 passed in 92.65s`, write audit `7 passed in 3.87s`, workflow job controls `3 passed in 114.38s`, tool bridge contracts `10 passed in 2.60s`, GraphRAG-lite `4 passed in 4.61s`, and context search `15 passed in 111.08s`.
- Product-effect interpretation for this slice: quality-signal moved from `0.7157` to `0.7323` on the default smoke and from `0.724` to `0.7407` on the representative Markdown smoke, while the research packet now keeps evidence follow-up work visible under heavy task load.

## 2026-06-18 - Workbench Reload State Restoration

Implemented in progress:

- Cleaned the two accidental untracked pager log files from the previous remote inspection while preserving the two historical untracked root documents.
- Started a temporary isolated FastAPI service on `127.0.0.1:18085` with its own SQLite database and paper upload directory under `data/test-runs/`.
- Ran the product-effect smoke against the temporary real HTTP service and confirmed the backend workflow remained `demo_ready`.
- Inspected Workbench through an SSH tunnel and browser session. The page loaded with Pilot Launch, Jobs, and Dossier controls, but a refreshed browser session could not load the latest dossier because Workbench did not restore `latestIdeaId` from completed jobs.
- Added Workbench state restoration from the latest completed job so refreshed sessions recover active paper, job id, latest idea id, latest experiment plan id, and latest novelty check id from `/research/jobs`.
- Added a `loadDossier` fallback that fetches recent jobs before showing the missing-idea empty state.
- Added an explicit success message after loading a dossier by idea id.
- Added Workbench asset version query strings so browsers pick up the updated static JavaScript and CSS after deployment.
- Added static Workbench assertions covering job-state restoration and asset versioning.
- Preserved `.env`, token, cookie, password, private key, and credential secrecy.

Verification completed:

- Temporary service health returned `ok` and readiness returned `ready`.
- Real HTTP product-effect smoke passed against `127.0.0.1:18085` with `product_effect_score=0.9331`, band `demo_ready`, `tool_manifest_count=119`, `project_bundle_file_count=71`, and release review outcome signoff evidence present.
- Browser inspection confirmed the cache-busted Workbench script restored the active paper from the latest completed job after page reload.
- Dossier preview loading was verified in the browser against the smoke-generated idea dossier.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check tests/test_app.py` passed.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check tests/test_app.py` passed after formatting.
- Focused Workbench pytest passed: `2 passed in 3.33s`.
- `bash scripts/check_pilot_readiness.sh` passed: `29 passed in 68.05s`.

Product-effect interpretation for this slice: the backend demo baseline still holds, and the Workbench is now more robust for a realistic pilot/demo session where the browser is refreshed after a workflow has already completed. Remaining customer-pilot work should focus on human UX polish, project scoping, durable queue/worker policy, backup/restore scripting, and deployment hardening rather than adding more delivery-chain endpoints.

## 2026-06-18 - Workbench Latest Workflow Continuation

- Added a first-screen Latest Workflow continuation band above Pilot Launch so a refreshed Workbench session shows the recovered job, status, active paper, and latest idea without requiring the operator to scroll into Jobs or Dossier.
- Wired the continuation band to `refreshJobs`, `loadDossier`, queued workflow status, job polling, job artifact loading, and completed-job restoration so the browser UI stays aligned with the latest workflow state.
- Added static Workbench contract coverage for the continuation band, cache-busted assets, continuation controls, mobile layout styles, and JavaScript state rendering hooks.

## 2026-06-18 - Dossier Primary Action Surface

- Added a Dossier primary action bar for the common demo path: load dossier, related work, proposal draft, experiment run, research packet, and project bundle.
- Moved the long Dossier control surface behind an Advanced Actions disclosure while preserving the existing button ids and event handlers for the full workflow surface.
- Extended Workbench static contracts to protect the primary Dossier controls, Advanced Actions disclosure, cache-busted assets, responsive styles, and quick-action JavaScript bindings.

## 2026-06-18 - Workbench Pilot Path Stage Rail

- Added a first-screen Pilot Path stage rail between Latest Workflow and Pilot Launch so the operator can jump through Setup, Evidence, Generate, Review, Dossier, and Delivery without scanning the full navigation list.
- Added responsive Pilot Path styling and cache-busted Workbench assets for the new stage rail.
- Extended Workbench static contracts to protect the Pilot Path nav link, stage ordering, labels, styles, and placement before Pilot Launch.

## 2026-06-18 - Cockpit Pilot Task Sequence

- Extended the project cockpit response with a `pilot_task_sequence` that maps Setup, Evidence, Generate, Review, Dossier, and Delivery to status, detail, Workbench anchor, API action, and task owner type.
- Added a Pilot Task Sequence section to cockpit Markdown exports so handoff artifacts include the same real-pilot execution lane shown in Workbench.
- Wired Workbench Pilot Path rendering to `cockpit.pilot_task_sequence` while preserving the static stage rail as a fallback.

## 2026-06-18 - Evidence Ledger Quality Signals

- Added evidence-ledger quality signals for direct evidence links, context evidence links, linked evidence type coverage, and linked source-paper coverage.
- Updated evidence-ledger coverage scoring so representative-paper quality depends more on direct claim support plus evidence type/source diversity instead of raw evidence volume alone.
- Added Evidence Quality Signals to evidence-ledger Markdown exports and regression coverage for typed evidence routing quality metadata.

## 2026-06-18 - Workbench-First Demo Target Decision

- Updated the demo runbook baseline to the latest isolated in-process product-effect smoke: overall `0.9352`, band `demo_ready`, quality signal `0.7407`, and evidence-ledger coverage `0.59`.
- Set the primary demo target to Workbench-first, with API-first and MCP/tool-consumer paths reserved for technical integration audiences.
- Documented the remaining qualitative review gate: real or representative paper outputs still need human review for generated gaps, ideas, evidence-ledger claims, and claim-validation actions.
## 2026-06-18 - Pilot Operational Preflight

Implemented in progress:

- Added `scripts/check_pilot_operational_preflight.sh`, a read-only pilot hardening preflight that checks required runtime files, Workbench assets, remote-safe scripts, deployment and migration docs, `.env.example` keys, compose persistence, healthcheck wiring, git metadata, and remote development tools.
- The preflight reports whether a real `.env` exists without opening or printing it. Default mode tolerates development worktree changes as warnings; `PILOT_PREFLIGHT_STRICT_GIT=true` enforces clean `main` checkout alignment with `origin/main` for approved deployment windows.
- Wired the preflight into `scripts/check_remote_safe_suite.sh`, `scripts/check_suite_contracts.sh`, README verification docs, deployment checklist/runbook, and deployment contract tests.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_pilot_operational_preflight.sh` passed in default development mode, warning only on current uncommitted implementation files and missing production `.env`.
- `git --no-pager diff --check` passed.
- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed after formatting the touched test file.
- `bash scripts/check_script_catalog.sh` passed.
- `bash scripts/check_suite_contracts.sh` passed.
- `bash scripts/check_deployment_contracts.sh` passed: `1 passed`.
- `bash scripts/check_remote_safe_suite.sh` passed, including the new preflight stage and all default focused checks.

## 2026-06-18 - External Literature Readiness Signal

Implemented in progress:

- Added an `external_literature_search` check to `GET /health/ready` so pilot operators can see whether optional external literature search is disabled, correctly configured, or blocked by invalid providers or missing base URLs.
- Kept the check non-networked and credential-safe: it validates provider names and base URL presence only, without outbound requests or secret exposure.
- Added `external_literature_readiness_check` to the research status capability list.
- Updated the pilot readiness suite, README capability list, deployment checklist, and deployment docs.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff check backend/app.py backend/research/routes.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/app.py backend/research/routes.py tests/test_app.py` passed after formatting `backend/app.py` and `tests/test_app.py`.
- Focused pytest passed: `tests/test_app.py::test_health_ready_checks_database_and_storage`, `tests/test_app.py::test_health_ready_checks_external_literature_configuration`, and `tests/test_app.py::test_research_status` (`3 passed`).
- `bash scripts/check_pilot_readiness.sh` passed: `30 passed`.

## 2026-06-18 - Default Project Scope Compatibility Contract

Implemented in progress:

- Added `GET /research/project/scope`, a read-only compatibility endpoint that reports the active `default` project id, the `X-Research-Assistant-Project` header contract, compatibility mode, supported project ids, and warnings when a non-default project id is requested before migrations exist.
- Added `ProjectScopeResponse`, `default_project_scope_contract` status capability, and `get_project_scope` tool-manifest entry.
- Updated smoke assertions, pilot readiness coverage, README, and `docs/user_project_scoping_design.md` so clients do not mistake project ids for secrets or authorization.
- Re-ran the isolated product-effect smoke after the manifest change; tool manifest and MCP bridge now expose `120` tools, while the overall product-effect score remains `0.9352` / `demo_ready`.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff check backend/research/schemas.py backend/research/routes.py tests/test_app.py scripts/smoke_api.py` passed.
- `.venv/bin/ruff format --check backend/research/schemas.py backend/research/routes.py tests/test_app.py scripts/smoke_api.py` passed after formatting schema and test files.
- Focused pytest passed for research status, project scope, and tool manifest contract: `3 passed`.
- `bash scripts/check_tool_bridge_contracts.sh` passed: `10 passed`.
- `bash scripts/check_pilot_readiness.sh` passed: `31 passed`.
- `bash scripts/check_product_effect_smoke.sh` passed with `tool_manifest_count=120`, `tool_bridge_count=120`, `product_effect_score=0.9352`, and band `demo_ready`.
- `bash scripts/check_remote_safe_suite.sh` passed after the scope contract and smoke documentation updates.

## 2026-06-18 - Health Build Metadata

Implemented in progress:

- Added non-secret build metadata to `GET /health` and `GET /health/ready`, using `APP_COMMIT_SHA` or `GIT_COMMIT_SHA` when provided and `unknown` otherwise.
- Added `APP_COMMIT_SHA=local` to `.env.example` and wired `APP_COMMIT_SHA` through `docker-compose.yml` for pilot deployment traceability.
- Updated deployment docs and tests so operators verify the health payload commit against the intended deployed commit before sharing Workbench.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff check backend/app.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/app.py tests/test_app.py` passed after formatting `tests/test_app.py`.
- Focused pytest passed for health, health readiness build metadata, and deployment artifacts: `3 passed`.
- `bash scripts/check_deployment_contracts.sh` passed: `1 passed`.
- `bash scripts/check_pilot_readiness.sh` passed: `32 passed`.
- `bash scripts/check_product_effect_smoke.sh` passed with health/readiness build metadata, `tool_manifest_count=120`, `tool_bridge_count=120`, `product_effect_score=0.9352`, and band `demo_ready`.

## 2026-06-18 - Backup Restore Contract Check

Implemented in progress:

- Added `scripts/check_backup_restore_contracts.sh`, a read-only contract check for persistent `/app/data` volume wiring, backup/restore docs, migration backup requirements, and operator-approval guardrails.
- Wired the check into `scripts/check_remote_safe_suite.sh`, `scripts/check_suite_contracts.sh`, and README verification docs.
- Kept the script non-destructive: it does not run Docker, stop services, copy data, restore volumes, modify databases, or read secrets.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_backup_restore_contracts.sh` passed.
- `bash scripts/check_script_catalog.sh` passed.
- `bash scripts/check_suite_contracts.sh` passed.

## 2026-06-18 - MCP Project Scope Forwarding

Implemented in progress:

- Added `BridgeScope` to `scripts/mcp_http_bridge.py` so MCP/tool clients can forward the non-secret active project id with `X-Research-Assistant-Project`.
- Added `--project-id`, `--project-header`, `MCP_BRIDGE_PROJECT_ID`, `MCP_BRIDGE_PROJECT_HEADER`, `RESEARCH_ASSISTANT_PROJECT_ID`, and `RESEARCH_ASSISTANT_PROJECT_HEADER` support.
- Included project-scope forwarding state in bridge health-check JSON without treating project ids as secrets or authorization.
- Added `mcp_bridge_project_scope_forwarding` to the status capability list and updated README/deployment docs.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff check scripts/mcp_http_bridge.py tests/test_mcp_http_bridge.py tests/test_app.py backend/research/routes.py` passed.
- `.venv/bin/ruff format --check scripts/mcp_http_bridge.py tests/test_mcp_http_bridge.py tests/test_app.py backend/research/routes.py` passed after formatting `scripts/mcp_http_bridge.py`.
- `.venv/bin/python scripts/mcp_http_bridge.py --help` showed the new `--project-id` and `--project-header` options.
- Focused pytest passed for MCP bridge tests and research status: `10 passed`.
- `bash scripts/check_tool_bridge_contracts.sh` passed: `11 passed`.

## 2026-06-18 - Workbench Project Scope Forwarding

Implemented in progress:

- Added a Workbench project-scope control that stores a non-secret project id preference separately from the API key.
- Updated Workbench request headers so `/research/*` calls forward `X-Research-Assistant-Project` alongside the API key when configured.
- Refreshed static asset cache versions, README summary text, deployment notes, static Workbench assertions, and project-scoping design notes.
- Synchronized the pilot operational preflight README token with the project-scope-aware Workbench wording.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_workbench_static_assets_are_served` passed: `1 passed in 5.01s`.
- `bash scripts/check_pilot_readiness.sh` passed: `32 passed in 96.21s`.
- `bash scripts/check_pilot_operational_preflight.sh` passed in development mode with only expected worktree and missing-production-`.env` warnings.
- `bash scripts/check_remote_safe_suite.sh` passed.

## 2026-06-18 - Workbench Project Scope Status Signal

Implemented in progress:

- Added `workbench_project_scope_forwarding` to `/research/status` implemented capabilities so operators and tool clients can see that browser Workbench requests forward the active project scope.
- Added status regression coverage while preserving the existing default-project and MCP scope capability signals.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff check backend/research/routes.py tests/test_app.py scripts/smoke_api.py` passed.
- `.venv/bin/ruff format --check backend/research/routes.py tests/test_app.py scripts/smoke_api.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_research_status` passed: `1 passed in 4.49s`.
- `bash scripts/check_product_effect_smoke.sh` passed with `tool_manifest_count=120`, `tool_bridge_count=120`, `product_effect_score=0.9352`, and band `demo_ready`.

## 2026-06-18 - Database Storage Readiness Signal

Implemented in progress:

- Added a `database_storage` check to `GET /health/ready` so deployments can see whether SQLite database storage is persistent and whether the database parent directory exists and is writable.
- Kept external database deployments non-blocking by reporting non-SQLite storage as not app-managed instead of requiring a local file path.
- Updated health readiness tests and deployment documentation without reading secrets, starting services, running migrations, or modifying production data.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff check backend/app.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/app.py tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_health_ready_checks_database_and_storage tests/test_app.py::test_deployment_artifacts_document_customer_runtime` passed: `2 passed in 4.23s`.
- `bash scripts/check_deployment_contracts.sh` passed: `1 passed in 4.25s`.
- `bash scripts/check_remote_safe_suite.sh` passed after the health readiness and deployment documentation updates.

## 2026-06-18 - API Key Auth Readiness Signal

Implemented in progress:

- Added an `api_key_auth` check to `GET /health/ready` so deployments that enable API-key protection without a configured key report `not_ready` before Workbench or MCP clients hit `/research/*` failures.
- Kept the readiness payload secret-safe: it reports enabled/configured/header state and a generic error, never the API key value.
- Added regression coverage for default disabled auth, enabled auth with a configured key, and enabled auth with no configured key.
- Updated deployment documentation so operators verify `api_key_auth.ok=true` when API-key protection is enabled.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff check backend/app.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/app.py tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_health_ready_checks_database_and_storage tests/test_app.py::test_health_ready_reports_missing_api_key_when_auth_is_enabled tests/test_app.py::test_optional_api_key_guard_protects_research_routes tests/test_app.py::test_deployment_artifacts_document_customer_runtime` passed: `4 passed in 5.20s`.
- `bash scripts/check_deployment_contracts.sh` passed: `1 passed in 3.83s`.
- `bash scripts/check_focused_test_coverage.sh` passed after adding the new readiness test to `scripts/check_pilot_readiness.sh`.
- `bash scripts/check_remote_safe_suite.sh` passed, including `33` pilot readiness tests.

## 2026-06-18 - Request ID Response Header

Implemented in progress:

- Added a request-id middleware that returns the configured request-id header on normal health, Workbench, and research API responses.
- Ensured API-key guard errors also include a request id, so missing/invalid-key failures can be reported without exposing secrets.
- Updated write-operation audit to reuse the same request id that is returned to the client.
- Added regression coverage and registered the new test in the pilot readiness script.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff check backend/app.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/app.py tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_request_id_header_is_returned_for_health_and_auth_errors tests/test_app.py::test_optional_api_key_guard_protects_research_routes tests/test_app.py::test_write_operation_audit_jsonl_records_sanitized_metadata tests/test_app.py::test_deployment_artifacts_document_customer_runtime` passed: `4 passed in 5.01s`.
- `bash scripts/check_focused_test_coverage.sh` passed after registering the request-id test in `scripts/check_pilot_readiness.sh`.
- `bash scripts/check_deployment_contracts.sh` passed: `1 passed in 3.81s`.
- `bash scripts/check_remote_safe_suite.sh` passed, including `34` pilot readiness tests.

## 2026-06-18 - Workbench Asset Readiness Signal

Implemented in progress:

- Added a `workbench_assets` check to `GET /health/ready` so deployments fail readiness when the browser Workbench entrypoint or core static assets are missing.
- Kept the check file-system only: it verifies `index.html`, `app.js`, and `styles.css` exist without starting services or reading secrets.
- Updated readiness and deployment contract tests plus deployment/architecture documentation.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff check backend/app.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/app.py tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_health_ready_checks_database_and_storage tests/test_app.py::test_workbench_static_assets_are_served tests/test_app.py::test_deployment_artifacts_document_customer_runtime` passed: `3 passed in 4.49s`.
- `bash scripts/check_deployment_contracts.sh` passed: `1 passed in 3.83s`.
- `bash scripts/check_remote_safe_suite.sh` passed, including `34` pilot readiness tests.

## 2026-06-18 - Model Provider Configuration Readiness Signal

Implemented in progress:

- Added a non-blocking `model_provider_configuration` check to `GET /health/ready` so operators can see whether main, extraction, and judge roles are configured for external models or deterministic fallback.
- Kept the payload credential-safe: it reports boolean model/base-url/API-key configuration state and never prints API key values or base URLs.
- Updated readiness tests and deployment documentation so pilot checks include model-provider mode visibility without making outbound network requests.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff check backend/app.py tests/test_app.py` passed.
- `.venv/bin/ruff format --check backend/app.py tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_health_ready_checks_database_and_storage tests/test_app.py::test_deployment_artifacts_document_customer_runtime` passed: `2 passed in 4.34s`.
- `bash scripts/check_deployment_contracts.sh` passed: `1 passed in 3.91s`.
- `bash scripts/check_remote_safe_suite.sh` passed, including `34` pilot readiness tests.

## 2026-06-18 - Workbench Runtime Readiness Strip

Implemented in progress:

- Added a compact Workbench sidebar readiness strip sourced from `/health/ready` so browser users can see database, storage, auth, Workbench-asset, model-provider, and external-literature readiness at a glance.
- Kept the UI status-only and cache-busted Workbench assets so deployments pick up the updated JavaScript and CSS.
- Added static Workbench assertions for the new DOM hook, styles, JavaScript renderer, and health readiness fetch.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_workbench_static_assets_are_served tests/test_app.py::test_health_ready_checks_database_and_storage` passed: `2 passed in 4.45s`.
- `bash scripts/check_remote_safe_suite.sh` passed, including `34` pilot readiness tests.

## 2026-06-18 - Workbench Request ID Signal

Implemented in progress:

- Updated Workbench API helpers to capture the `X-Request-ID` response header from health, readiness, research API, and authenticated download calls.
- Appended a short request id to the Workbench connection and error text so browser users can report failures with an operator-correlatable id.
- Cache-busted Workbench assets and added static assertions for the request-id helper path.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `.venv/bin/ruff check tests/test_app.py` passed.
- `.venv/bin/ruff format --check tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_workbench_static_assets_are_served` passed: `1 passed in 4.23s`.
- `bash scripts/check_remote_safe_suite.sh` passed, including `34` pilot readiness tests and product smoke coverage with `15 passed in 131.27s`.

## 2026-06-18 - Runtime Readiness Status Capability

Implemented in progress:

- Added `runtime_readiness_signals` to the `/research/status` implemented capability list so clients can discover that deployment readiness checks are present without calling `/health/ready` first.
- Added status-test coverage and updated README and technical design documentation for the capability surface.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check backend/research/routes.py tests/test_app.py` passed.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check backend/research/routes.py tests/test_app.py` passed.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/test_app.py::test_research_status` passed: `1 passed in 5.05s`.
- `bash scripts/check_remote_safe_suite.sh` passed, including `34` pilot readiness tests and product smoke coverage with `15 passed in 128.13s`.

## 2026-06-18 - Request ID Header Readiness

Implemented in progress:

- Added a non-secret `request_id_header` check to `/health/ready` so operators can verify the configured request-id response header name.
- Updated Workbench to learn the configured request-id header from readiness before displaying short request ids in connection and error states.
- Added a Req ID readiness badge, cache-busted Workbench assets, and expanded backend/static/documentation assertions.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check backend/app.py tests/test_app.py` passed.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check backend/app.py tests/test_app.py` passed.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/test_app.py::test_health_ready_checks_database_and_storage tests/test_app.py::test_request_id_header_is_returned_for_health_and_auth_errors tests/test_app.py::test_workbench_static_assets_are_served tests/test_app.py::test_deployment_artifacts_document_customer_runtime` passed: `4 passed in 5.12s`.
- `bash scripts/check_remote_safe_suite.sh` passed, including `34` pilot readiness tests and product smoke coverage with `15 passed in 127.39s`.

## 2026-06-18 - Workbench Scope Contract Status

Implemented in progress:

- Updated Workbench to call `/research/project/scope` after an API key is available and display the requested project id, active project id, and compatibility/isolation status.
- Refreshed scope status after saving the API key or project id so browser users can see that current project ids are non-secret compatibility hints, not isolation guarantees.
- Cache-busted Workbench assets, added static assertions, and updated README and technical design documentation.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check tests/test_app.py` passed.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check tests/test_app.py` passed.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/test_app.py::test_workbench_static_assets_are_served tests/test_app.py::test_project_scope_reports_default_compatibility_boundary` passed: `2 passed in 4.65s`.
- `bash scripts/check_remote_safe_suite.sh` passed, including `34` pilot readiness tests and product smoke coverage with `15 passed in 126.54s`.

## 2026-06-18 - Representative Paper Review Protocol

Implemented in progress:

- Added `docs/representative_paper_review.md` as the human review protocol and findings template for a real representative-paper pilot review.
- Documented required inputs, review steps, qualitative findings, exit criteria, and non-goals so the project does not mistake synthetic smoke results for human acceptance.
- Wired the protocol into `scripts/check_handoff_docs.sh` and updated README/TODO references.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_remote_safe_suite.sh` passed, including `34` pilot readiness tests and product smoke coverage with `15 passed in 127.52s`.

## 2026-06-18 - Representative Review Status Capability

Implemented in progress:

- Added `representative_paper_review_protocol` to `/research/status` implemented capabilities so clients can discover the human-review gate.
- Added status-test coverage and updated README and technical design documentation.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check backend/research/routes.py tests/test_app.py` passed.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check backend/research/routes.py tests/test_app.py` passed.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/test_app.py::test_research_status` passed: `1 passed in 4.25s`.
- `bash scripts/check_remote_safe_suite.sh` passed, including `34` pilot readiness tests and product smoke coverage with `15 passed in 125.69s`.

## 2026-06-18 - MCP Bridge Request ID Errors

Implemented in progress:

- Updated `scripts/mcp_http_bridge.py` so backend HTTP errors include a short request id when the response carries the configured request-id header.
- Added unit coverage for HTTPError request-id extraction and updated README, deployment, and technical design documentation.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `bash scripts/check_tool_bridge_contracts.sh` passed: `12 passed in 2.26s`.
- `bash scripts/check_remote_safe_suite.sh` passed, including `34` pilot readiness tests and product smoke coverage with `15 passed in 125.65s`.

## 2026-06-19 - Representative Paper Review Records

Implemented in progress:

- Added `RepresentativePaperReviewRecordCreate` and persisted representative-paper human review records as `ResearchBrief` artifacts with scope `representative_paper_review`.
- Added API and tool-manifest entries for recording, listing, loading, and Markdown-exporting representative-paper review records.
- Added `/research/status` capability `representative_paper_review_records` so clients can distinguish the protocol from persisted review evidence.
- Updated README, TODO, and the representative-paper protocol with the new record workflow.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `python3 -m compileall backend/research/schemas.py backend/research/routes.py tests/test_app.py` passed.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check backend/research/routes.py backend/research/schemas.py tests/test_app.py` passed.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check backend/research/routes.py backend/research/schemas.py tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_research_status tests/test_app.py::test_tool_manifest_lists_mcp_ready_research_tools tests/test_app.py::test_representative_paper_review_records_persist_and_export_markdown` passed: `3 passed in 3.34s`.
- `bash scripts/check_handoff_docs.sh` passed.
- `bash scripts/check_tool_bridge_contracts.sh` passed: `12 passed in 1.76s`.
- `bash scripts/check_pilot_readiness.sh` passed: `35 passed in 107.38s`.
- `bash scripts/check_remote_safe_suite.sh` passed, including `35` pilot readiness tests and product smoke coverage with `15 passed in 144.98s`.

## 2026-06-20 - Sparse Heading Paper Gap Fallback

Implemented in progress:

- Preserved pre-reference body text as a `full_text` section when section detection only finds a later heading such as `REFERENCES`.
- Added a conservative gap-mining fallback that turns claim evidence into an evaluation gap when no limitation, future-work, or problem evidence exists for the requested paper.
- Added regression coverage for PDFs/text extractions that expose only a references heading while still carrying useful preamble/body text.
- Validated the fix against the GeoToken representative paper: the run moved from `workflow returned no gaps` to a completed `pilot_effective` smoke with `1` gap, `2` ideas, and product-effect score `0.8131`.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check backend/research/services/document_ingestion.py backend/research/services/gap_service.py tests/test_app.py` passed.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check backend/research/services/document_ingestion.py backend/research/services/gap_service.py tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_upload_preserves_preamble_when_only_reference_heading_matches tests/test_app.py::test_markdown_gap_sections_are_mined_from_headings tests/test_app.py::test_upload_text_paper` passed: `3 passed in 5.31s`.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `bash scripts/check_research_workflow_primitives.sh` passed: `42 passed in 114.12s`.
- `bash scripts/check_remote_safe_suite.sh` passed, including `35` pilot readiness tests, `42` workflow primitive tests, and product smoke coverage with `15 passed in 129.34s`.

## 2026-06-20 - Roman Heading Geolocalization Gap Richness

Implemented in progress:

- Extended section heading detection to recognize Roman numeral prefixes such as `I. INTRODUCTION`, compact headings such as `II. RELATEDWORK`, and Roman-numbered conclusion/experiment headings common in IEEE-style PDFs.
- Changed gap mining to top up sparse problem/limitation/future-work evidence with claim evidence until `max_gaps` is reached, so papers with useful claims but few explicit limitation headings still produce multiple evaluation gaps.
- Added regression coverage for Roman numeral sparse headings and claim-evidence gap top-up.
- Validated the improvement against GeoToken: the representative smoke now completes with `3` gaps, `6` ideas, product-effect score `0.9386`, band `demo_ready`, and no failed scorecard checks.
- Preserved the two pre-existing untracked root documents and did not read or touch secrets or `.env` content.

Verification completed:

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check backend/research/services/document_ingestion.py backend/research/services/gap_service.py tests/test_app.py` passed.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check backend/research/services/document_ingestion.py backend/research/services/gap_service.py tests/test_app.py` passed.
- `.venv/bin/pytest -q tests/test_app.py::test_upload_preserves_preamble_when_only_reference_heading_matches tests/test_app.py::test_upload_detects_roman_heading_sections_and_claim_gap_topup tests/test_app.py::test_markdown_gap_sections_are_mined_from_headings` passed: `3 passed in 7.32s`.
- `bash scripts/check_focused_test_coverage.sh` passed.
- `bash scripts/check_research_workflow_primitives.sh` passed: `43 passed in 148.31s`.
- `bash scripts/check_remote_safe_suite.sh` passed, including `35` pilot readiness tests, `43` workflow primitive tests, and product smoke coverage with `15 passed in 168.67s`.
