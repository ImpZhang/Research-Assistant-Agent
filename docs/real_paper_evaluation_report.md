# Real Paper Evaluation Report

Date: 2026-06-29

This report summarizes the real-provider, real-PDF evaluation rounds for the local Research Assistant Agent and the latest 12-paper strict geolocalization evaluation set after the current embedding-model switch.

## Provider Status

Current explicit provider smoke passed for all configured roles on 2026-06-28:

- `qwen3-32b`: main, extraction, and judge roles passed.
- `multimodal-embedding-v1`: passed with 1024-dimensional vectors.
- `qwen3-rerank`: passed and ranked the relevant smoke document first.

Implementation notes:

- DashScope Qwen3 non-streaming chat calls require `enable_thinking=false`.
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
