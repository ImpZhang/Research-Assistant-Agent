# Real Paper Evaluation Report

Date: 2026-06-29

This report summarizes the real-provider, real-PDF evaluation rounds for the local Research Assistant Agent and the latest 12-paper strict geolocalization evaluation set after the current embedding-model switch.

## Provider Status

Current explicit provider status after the `text-embedding-v1` switch:

- `text-embedding-v1`: passed the explicit smoke with 1536-dimensional vectors.
- One-paper strict real-paper smoke passed on GeoRanker with `text-embedding-v1`, `47` external embeddings, provider fallback warnings `0`, and benchmark completed `1 / 1`; report `outputs/evaluations/text_embedding_smoke/real_paper_eval_20260629_122451.json`.
- `qwen3-32b` main/extraction/judge and `qwen3-rerank`: currently blocked in this local account by DashScope `AllocationQuota.FreeTierOnly`, so a full strict qwen3-rerank external run is an operator quota/payment-mode task rather than a code-completeness claim.
- Historical `multimodal-embedding-v1`: passed with 1024-dimensional vectors and remains useful compatibility evidence.

Implementation notes:

- DashScope Qwen3 non-streaming chat calls require `enable_thinking=false`.
- `text-embedding-v1` uses DashScope native text-embedding fallback when the compatible `/embeddings` endpoint rejects the request, and external rebuilds now batch/truncate provider inputs.
- `multimodal-embedding-v1` uses DashScope native multimodal embedding behavior when needed.
- `qwen3-rerank` uses DashScope native text-rerank fallback.

## Latest Strict Twelve-Paper Verification

On 2026-06-29 Asia/Shanghai time, the evaluation set was expanded from the four-paper core to 12 representative geolocalization/place-recognition papers. The run used `multimodal-embedding-v1`, `--require-external-embeddings`, async workflow polling, retrieval-mode comparison, and the guarded `json-metrics-smoke` benchmark profile.

- Report: `outputs/evaluations/real_paper_eval_20260628_160429.json`.
- Completed papers: 12 / 12.
- Failed papers: 0.
- Workflow recovered count: 0.
- Embedding model: `multimodal-embedding-v1`.
- Embedding dimension: 1024.
- Total embedding indexed: 99.
- Provider fallback warnings: 0.
- Context searches with evidence: 12 / 12 papers.
- Retrieval comparison coverage: 36 queries, 27 top-evidence overlaps.
- Benchmark runs/completed: 12 / 12.
- Experiment run source: `benchmark_profile`.
- Proposal review decision: `ready_for_advisor_review` for all 12 papers.

The current evaluation set covers distance-aware ranking, RAG/multimodal foundation-model geolocalization, hierarchical token prediction, reasoning/RL, retrieval-based geolocalization, street-level MLLM+RAG, cross-view geolocalization, and classic place recognition.

## RAG v1 Retrieval Hardening Pass

On 2026-06-29, the retrieval layer was upgraded from `lexical_vector_graph_rag_lite_v0` to `lexical_vector_multi_query_section_compression_rerank_graph_rag_lite_v1`.

Implemented:

- deterministic query rewrite and multi-query retrieval variants;
- bounded external-provider vector variants to avoid multiplying embedding calls;
- section-aware chunk context for parent/neighbor evidence;
- compressed evidence snippets on returned chunks, evidence, gaps, and ideas;
- larger pre-rerank candidate pools before top-k truncation;
- structured table, figure-caption, and quantitative-result evidence extraction during ingestion;
- provider HTTP retry/backoff for retryable 429/5xx/network failures;
- text-hash embedding cache reuse across owners for repeated local evaluations.

Validation results:

- `bash scripts/check_context_search_evaluations.sh`: passed, including 52 focused tests and the local geolocalization benchmark smoke.
- Realistic gold retrieval: passed on 20 reviewer-style hard questions over 12 papers, primary hit@8 `0.6500`, primary MRR `0.3780`, replay pass `0.6500`.
- Full 12-paper end-to-end workflow with local retrieval embeddings: completed `12 / 12`, benchmark completed `12 / 12`, context evidence coverage `12 / 12`, retrieval comparison `36 / 36` queries, final report `outputs/evaluations/rag_v1_final_local_embedding/real_paper_eval_20260629_065445.json`.
- External embedding strict pass was partially verified as `11 / 12` in `outputs/evaluations/rag_v1_full/real_paper_eval_20260629_054621.json`; GeoRanker failed there because the local `.env` upload limit was 10 MiB while the PDF is 12.5 MB.
- GeoRanker then completed as a strict external-embedding single-paper rerun with `multimodal-embedding-v1`, benchmark completed `1 / 1`, report `outputs/evaluations/rag_v1_georanker_rerun/real_paper_eval_20260629_060847.json`.

Operational boundary:

- A clean single-run strict external-embedding `12 / 12` pass was not repeated after multiple consecutive provider-heavy evaluations because the external embedding provider began returning fallback-triggering failures. The code now has bounded query variants, retry/backoff, and cache reuse, but a production operator should still pace large real-provider evaluation batches or use local embeddings for repeated workflow regression runs.
- The local embedding full pass is therefore the authoritative full-chain regression result for this round; the external reports verify provider wiring and expose rate-limit/capacity behavior rather than proving unlimited batch throughput.

## Evaluated Papers

| Paper | Status | Sections | Chunks | Evidence | Gaps | Ideas | Embeddings | Readiness | Quality Gate | Proposal Review |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| GeoRanker | completed | 7 | 49 | 6 | 1 | 1 | 8 | 0.6839 | 0.5936 | ready_for_advisor_review |
| G3 | completed | 11 | 64 | 9 | 1 | 1 | 11 | 0.6839 | 0.5936 | ready_for_advisor_review |
| GeoToken | completed | 6 | 39 | 6 | 1 | 1 | 8 | 0.6839 | 0.5936 | ready_for_advisor_review |
| Recognition through Reasoning | completed | 10 | 61 | 9 | 1 | 1 | 11 | 0.6839 | 0.5936 | ready_for_advisor_review |
| Img2Loc | completed | 9 | 28 | 9 | 1 | 1 | 11 | 0.6839 | 0.5936 | ready_for_advisor_review |
| PIGEON | completed | 6 | 39 | 5 | 1 | 1 | 7 | 0.6839 | 0.5936 | ready_for_advisor_review |
| Street-Level Geolocalization with MLLM+RAG | completed | 2 | 48 | 2 | 1 | 1 | 4 | 0.6839 | 0.5936 | ready_for_advisor_review |
| Vision-Language Reasoning for Geolocalization | completed | 10 | 39 | 9 | 1 | 1 | 11 | 0.6839 | 0.5936 | ready_for_advisor_review |
| GEOMR | completed | 6 | 41 | 6 | 1 | 1 | 8 | 0.6839 | 0.5936 | ready_for_advisor_review |
| HADGEO | completed | 8 | 20 | 7 | 1 | 1 | 9 | 0.6839 | 0.5936 | ready_for_advisor_review |
| CAMP | completed | 2 | 50 | 2 | 1 | 1 | 4 | 0.6839 | 0.5936 | ready_for_advisor_review |
| NetVLAD | completed | 6 | 42 | 5 | 1 | 1 | 7 | 0.6839 | 0.5936 | ready_for_advisor_review |

Combined metrics:

- Completed papers: 12 / 12.
- Total gaps: 12.
- Total ideas: 12.
- Total external embeddings indexed: 99.
- Average readiness: 0.6839.
- Average quality gate: 0.5936.
- Context search returned evidence and graph context for every tested query.
- Retrieval traces included both `vector` and `rerank` matched terms in real runs.

Report access:

- Local JSON/Markdown outputs live under `outputs/evaluations/`.
- API summaries are available at `GET /research/evaluations/real-paper/reports`.
- The latest report can be loaded from the Workbench Real Eval panel.

## Generated Idea Quality

The structured idea prompt upgrade improved specificity. For example, GeoToken changed from a generic accuracy idea to:

> Region-Balanced Hard Negative Mining for Hierarchical Image Geolocalization

The 12-paper run generated one candidate idea per paper and completed proposal review, benchmark-backed experiment analysis, decision memo, and assumption audit for every paper. The current generated ideas are anchored to geolocalization evaluation slices, but several converge on region-balanced hard-negative mining. That is acceptable for a strict workflow smoke, but idea-diversity evaluation should be added before claiming strong research creativity.

## Evaluation Set Caveats

- The 12-paper run proves the local workflow is no longer a cherry-picked three-paper smoke, but it is still a small evaluation set rather than a statistical benchmark.
- A few PDFs expose publisher-header/title-noise behavior during structured title extraction, especially proceedings or journal front-matter heavy files. The workflow still completed, but query-evidence labeling should include title-extraction and section-header bad cases.
- Street-Level Geolocalization and CAMP produced only two extracted sections/evidence records each, which is useful evidence that PDF extraction quality still needs page/figure/table-aware hardening.
- The next credibility step is a labeled retrieval set: 50-80 query-evidence pairs across these 12 papers plus 20-30 replay bad cases for citation mismatch, context miss, noisy title extraction, weak evidence, benchmark-artifact gaps, and worker/retry edge cases.

## Remaining Blockers

The system consistently reports:

- high novelty/collision risk;
- four related-work searches still missing;
- one high-risk assumption still open.

This is the correct production boundary: the workflow can produce a grounded candidate and supporting artifacts, but it should not claim final novelty or SOTA without manual/current-literature review.

## Next Production Hardening

Implemented after the first evaluation round:

- Added report list/detail API endpoints for local real-paper evaluation artifacts.
- Added a Workbench Real Eval panel for loading the latest report into the dossier preview.
- Added evaluator-side retrieval comparison between configured retrieval and a local hash/no-rerank baseline.
- Added manual SOTA review packages that persist novelty/related-work collision evidence, missing searches, review queries, and Markdown checklists.
- Added SOTA external-search evidence packages that persist review-query search statuses, local/external result summaries, missing searches, and signoff readiness.
- Added manual SOTA signoff records that persist the reviewer decision, linked external-search evidence package, effective external-search completion state, nearest work, linked benchmark runs, final novelty claim, limitations, and blockers.
- Added benchmark run packets so dry-run or real-mode benchmark evidence can be recorded as first-class experiment runs with dataset, split, baseline, primary metric, command, artifacts, and reproducibility notes.
- Added a guarded local benchmark command runner that is disabled by default, executes command-argument lists without a shell when enabled, captures stdout/stderr/metrics, and stores artifacts under `outputs/benchmark-runs/`.
- Added a benchmark profile registry plus `scripts/benchmark_geoloc_predictions.py` so Workbench can discover runnable profiles, report missing local benchmark files, and execute a real geolocalization JSONL harness when ground truth and prediction files are present.
- Added benchmark run comparison briefs so repeated measured runs can be compared by metric delta and saved as auditable Markdown evidence.
- Added benchmark evidence readiness checks so completed runs and comparison briefs can gate manual SOTA signoff.
- Added benchmark evidence readiness task generation so missing benchmark runs, comparison briefs, artifacts, or regression follow-ups can enter the task board.
- Surfaced benchmark evidence readiness inside SOTA review packages and SOTA signoff manual-gate summaries.

Remaining hardening:

1. Enable live external-search providers in production settings and require completed evidence packages before final signoff.
2. Add optional page-image/figure-aware PDF evidence extraction for scanned or figure-heavy geolocalization papers.
3. Build the 50-80 item query-evidence evaluation set and 20-30 bad-case replay set from the current 12-paper corpus.
4. Populate larger project-local benchmark ground truth and prediction artifacts, then use `scripts/run_geoloc_benchmark_pipeline.py` plus benchmark profile execution for repeated measured geolocalization runs.
