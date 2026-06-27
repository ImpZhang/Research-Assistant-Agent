---
name: benchmark-evaluation
description: Prepare, run, compare, and validate local benchmark evidence for research ideas. Use when an agent needs geolocalization JSONL benchmark smokes, benchmark profiles, guarded command execution, benchmark run packets, or metric comparisons for SOTA readiness.
---

# Benchmark Evaluation

## Purpose

Generate reproducible benchmark evidence without turning arbitrary shell execution into the default path. The local baseline supports profile discovery, guarded command execution, JSONL geolocalization metrics, and comparison briefs.

## Backing APIs And Tools

- `GET /research/benchmark-profiles`
- `POST /research/experiment-plans/{plan_id}/benchmark-run`
- `POST /research/experiment-plans/{plan_id}/benchmark-run/execute`
- `POST /research/experiment-runs/compare`
- Tool manifest names: `list_benchmark_profiles`, `create_benchmark_run_packet`, `execute_benchmark_command`, `compare_benchmark_runs`
- Scripts: `scripts/prepare_local_geoloc_benchmark.py`, `scripts/benchmark_geoloc_predictions.py`, `scripts/check_local_geoloc_benchmark_smoke.sh`

## Workflow

1. Inspect benchmark profile readiness before running anything.
2. Prepare local data/profile manifests under project-local `data/`, `configs/`, and `outputs/`.
3. Prefer dry-run packets or temporary smoke fixtures until real prediction files are available.
4. Execute only allowlisted command-argument lists through the guarded runner when explicitly enabled.
5. Compare benchmark runs and link comparison evidence back to SOTA readiness.

## Safety Boundaries

- Do not run shell strings or unreviewed arbitrary commands.
- Do not commit local datasets, prediction files, model weights, or generated benchmark outputs.
- Do not use benchmark smoke metrics as scientific evidence; smokes verify plumbing only.

## Failure Handling

- If profiles are missing data or prediction paths, report runnable=false and prepare ignored local fixtures.
- If predictions are incomplete, preserve missing-prediction counts in metrics.
- If command execution is disabled, create a benchmark packet instead of trying to bypass the guard.

## Verification

- Run `bash scripts/check_local_geoloc_benchmark_smoke.sh` for the local JSONL scoring harness.
- Run `bash scripts/check_context_search_evaluations.sh` after benchmark-readiness or SOTA-evidence changes.
- Run `bash scripts/check_deployment_contracts.sh` after changing benchmark profile configuration or guarded runner deployment settings.
