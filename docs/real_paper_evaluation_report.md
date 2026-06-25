# Real Paper Evaluation Report

Date: 2026-06-25

This report summarizes the first real-provider, real-PDF evaluation round for the local Research Assistant Agent.

## Provider Status

The explicit provider smoke passed for all configured roles:

- `qwen3-32b`: main, extraction, and judge roles passed.
- `qwen3-vl-embedding`: passed with 2560-dimensional vectors.
- `qwen3-rerank`: passed and ranked the relevant smoke document first.

Implementation notes:

- DashScope Qwen3 non-streaming chat calls require `enable_thinking=false`.
- `qwen3-vl-embedding` uses DashScope native multimodal embedding fallback.
- `qwen3-rerank` uses DashScope native text-rerank fallback.

## Evaluated Papers

| Paper | Status | Sections | Chunks | Evidence | Gaps | Ideas | Embeddings | Readiness | Quality Gate | Proposal Review |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| G3 | completed | 11 | 64 | 9 | 1 | 1 | 11 | 0.6221 | 0.5587 | ready_for_advisor_review |
| GeoToken | completed | 6 | 39 | 6 | 1 | 1 | 8 | 0.7021 | 0.5811 | ready_for_advisor_review |
| Recognition through Reasoning | completed | 10 | 61 | 9 | 1 | 1 | 11 | 0.6221 | 0.5587 | ready_for_advisor_review |

Combined metrics:

- Completed papers: 3 / 3.
- Total gaps: 3.
- Total ideas: 3.
- Total external embeddings indexed: 30.
- Average readiness: 0.6488.
- Average quality gate: 0.5662.
- Context search returned evidence and graph context for every tested query.
- Retrieval traces included both `vector` and `rerank` matched terms in real runs.

Report access:

- Local JSON/Markdown outputs live under `outputs/evaluations/`.
- API summaries are available at `GET /research/evaluations/real-paper/reports`.
- The latest report can be loaded from the Workbench Real Eval panel.

## Generated Idea Quality

The structured idea prompt upgrade improved specificity. For example, GeoToken changed from a generic accuracy idea to:

> Region-Balanced Hard Negative Mining for Hierarchical Image Geolocalization

The current generated ideas are now better anchored to geolocalization evaluation slices, but they remain pre-SOTA-review candidates.

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

Remaining hardening:

1. Enable live external-search providers in production settings and require completed evidence packages before final signoff.
2. Add optional page-image/figure-aware PDF evidence extraction for scanned or figure-heavy geolocalization papers.
3. Populate project-local benchmark ground truth and prediction artifacts, then replace smoke-profile executions with repeated measured geolocalization runs.
