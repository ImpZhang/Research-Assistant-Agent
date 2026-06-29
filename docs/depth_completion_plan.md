# Depth Completion Plan

This document records the next deepening pass after the 12-paper real workflow, RAG v1 retrieval hardening, realistic hard-question evaluation, and workflow lineage checkpoint work.

## Current Judgment

The project should not add heavy RAG infrastructure just to look more advanced. The current default remains local-first SQLite with optional external embedding/rerank providers. The useful next work is to make existing evaluation, lineage, and failure analysis deeper and easier to repeat.

## Completion Status

This pass completed the P0 items below:

- Added realistic RAG miss analysis and regenerated `data/evaluation/geoloc_12paper/realistic_miss_analysis.json` / `.md`.
- Added committed local pipeline profiles in `configs/local_pipeline_profiles.json`, including quick smoke, realistic RAG eval, miss analysis, workflow lineage smoke, full strict text-embedding eval, and one-paper strict text-embedding smoke.
- Extended artifact lineage to downstream proposal/review/memo/audit/ledger/benchmark artifacts through standalone lineage records.
- Made `scripts/check_model_provider_config.py` load the local `.env` safely while still reporting only variable names and readiness flags.
- Added DashScope native fallback, batching, and truncation for `text-embedding-v1`; the one-paper strict text-embedding smoke passed with `47` external embeddings and `0` provider fallbacks.
- Added near-tie diversity-aware final ranking for context search. The realistic 12-paper metric stayed stable at primary hit@8 `0.65`, MRR `0.3780`, replay pass `0.65`; the remaining 7 misses are now explicitly classified.

The full strict `qwen3-rerank` profile remains blocked by current provider quota: the explicit real-provider smoke reports DashScope `AllocationQuota.FreeTierOnly` for main/extraction/judge/rerank, while `text-embedding-v1` itself passes and returns 1536-dimensional vectors.

## P0 Work To Complete Now

1. RAG miss analysis
   - Input: `data/evaluation/geoloc_12paper/realistic_quality_report.json`, `realistic_gold_questions.jsonl`, and `realistic_failure_replay_cases.jsonl`.
   - Output: JSON and Markdown reports that classify every realistic primary miss.
   - Required categories: paper recall miss, same-paper wrong evidence, supporting-over-primary confusion, query term gap, section/evidence granularity issue, and candidate competition.
   - Goal: explain why `primary_hit@8` is `0.6500` instead of just reporting the number.

2. Pipeline profiles
   - Add committed local pipeline profiles for common evaluation modes.
   - Profiles should make `quick_smoke`, `rag_realistic_eval`, `rag_miss_analysis`, `workflow_lineage_smoke`, and `strict_text_embedding_eval` reproducible without memorizing long commands.
   - Profiles must not read or print secrets.

3. Lineage coverage beyond the main workflow
   - Keep the existing `WorkflowStageRun`/`WorkflowArtifact` tables.
   - Add helper coverage for downstream artifacts generated after idea creation: proposal draft, proposal review, decision memo, assumption audit, evidence ledger, experiment/benchmark run packets, and replay/eval reports.
   - Goal: artifacts outside the first literature-to-ideas workflow should still be visible in a unified lineage vocabulary.

4. Text embedding strict-eval readiness
   - The default template now uses `text-embedding-v1`.
   - Run or preflight a strict external evaluation profile with `text-embedding-v1`.
   - If provider quota/rate limits block the run, save a clear blocked report instead of silently treating local fallback as strict external success.

## P1 Work After This Pass

- Add manual review metadata for realistic gold labels: reviewer, reviewed_at, confidence, dispute status, and revision notes.
- Add a Workbench panel for lineage/miss-analysis summaries instead of relying only on JSON.
- Add full DAG resume semantics across jobs, not only same-job checkpoint reuse.
- Add Alembic migrations after dependency/migration operations are explicitly approved.

## Explicit Non-Goals

- Do not add Milvus/Qdrant/pgvector yet. Current corpus size and local-first target still make SQLite reasonable.
- Do not rewrite the stable service-layer workflow into LangGraph.
- Do not make external provider calls implicit in normal tests.
- Do not claim SOTA or production reliability from smoke benchmark packets.

## Interview Framing

After this pass, the project should be described as:

> A local-first research Agent workflow that combines RAG v1 retrieval, realistic hard-question evaluation, miss taxonomy, trace/replay, workflow checkpointing, artifact lineage, and reproducible pipeline profiles. The focus is not only generation quality, but recoverability, reproducibility, and debugging of AI research workflows.
