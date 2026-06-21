# Geolocalization Benchmark SOTA Table

Review date: 2026-06-21
Source project commit when drafted: `cfc409d Compact external literature generated queries`

This table is a source-anchored follow-up to `docs/geolocalization_manual_sota_review.md`. It separates product workflow readiness from scientific benchmark claims. Product-effect smokes can show that the Research Assistant Agent workflow is usable; they do not prove that a generated research idea is novel or state-of-the-art.

## Metric

The common metric is localization accuracy: the percentage of predictions whose geodesic error is within 1 km, 25 km, 200 km, 750 km, and 2500 km. In the tables below, each tuple is ordered as:

`1km / 25km / 200km / 750km / 2500km`

## Source And Comparability Rules

Numbers below were extracted from primary arXiv HTML tables on 2026-06-21. The arXiv HTML files were inspected from `/tmp/raa_sota_pdfs/*.html` during this review.

Do not merge these settings into one leaderboard without a written caveat:

- Standard closed-world or MP16-family retrieval/RAG settings on IM2GPS3K and YFCC4K.
- MLLM-assisted/free-generation settings, where the external model changes the comparison surface.
- Reasoning-specific evaluation such as MP16-Reason-Test.
- Web-scale/open-world or leakage-aware evaluation such as GeoSearch with OSV-5M and reverse image search.

## Standard IM2GPS3K And YFCC4K Boundary

| Work | Primary source table | Setting note | IM2GPS3K | YFCC4K | Review implication |
| --- | --- | --- | --- | --- | --- |
| G3 | [arXiv 2405.14702, Table 1](https://arxiv.org/html/2405.14702) | NeurIPS 2024 RAG-style geolocalization. | 16.65 / 40.94 / 55.56 / 71.24 / 84.68 | 23.99 / 35.89 / 46.98 / 64.26 / 78.15 | Good representative workflow paper, but no longer the current benchmark boundary. |
| GeoRanker | [arXiv 2505.13731, Table 1](https://arxiv.org/html/2505.13731) | Distance-aware ranking after candidate generation. | 18.79 / 45.05 / 61.49 / 76.31 / 89.29 | 32.94 / 43.54 / 54.32 / 69.79 / 82.45 | Strong 2025 boundary and still competitive against later non-web papers. |
| GeoToken | [arXiv 2511.01082, Table I](https://arxiv.org/html/2511.01082) | MLLM-free hierarchical token prediction. | 16.8 / 39.6 / 53.8 / 70.8 / 85.0 | 24.3 / 35.3 / 46.6 / 64.2 / 78.6 | Important paradigm, but its unassisted table does not surpass GeoRanker. |
| GeoToken free-generation | [arXiv 2511.01082, Table II](https://arxiv.org/html/2511.01082) | Gemini-2.0-Flash MLLM-assisted setting. | 19.0 / 46.0 / 60.1 / 76.6 / 88.8 | 25.4 / 38.5 / 51.4 / 68.0 / 81.0 | Better on IM2GPS3K street/city than GeoRanker, but mixed elsewhere and model-assisted. |
| GeoRouter | [arXiv 2603.24376, Table 1](https://arxiv.org/html/2603.24376) | Dynamic routing between retrieval and generation. | 20.82 / 50.48 / 65.73 / 80.35 / 90.66 | 32.98 / 46.01 / 57.52 / 72.02 / 83.02 | Current strongest closed-world/non-web boundary among sources extracted in this pass. |
| DualGeo | [arXiv 2604.25533, Table I](https://arxiv.org/html/2604.25533) | Dual-view segmentation/RGB framework plus LMM refinement. | 17.25 / 41.47 / 55.76 / 71.71 / 85.05 | 27.49 / 36.45 / 45.03 / 61.58 / 75.92 | Improves over selected baselines on fine-grained metrics, but does not reset the overall boundary. |
| TransGeoCLIP | [arXiv 2606.08918, Table I](https://arxiv.org/html/2606.08918) | Location-attention GPS encoding plus LMM reasoning. | 17.72 / 42.17 / 56.80 / 71.71 / 86.12 | 31.17 / 41.09 / 51.84 / 67.75 / 81.01 | Stronger than G3 on the named table, but behind GeoRanker/GeoRouter on these benchmarks. |

## Reasoning-Specific Boundary

| Work | Primary source table | Dataset / setting | Accuracy tuple | Review implication |
| --- | --- | --- | --- | --- |
| GLOBE-7B | [arXiv 2506.14674, Table 2](https://arxiv.org/html/2506.14674) | MP16-Reason-Test | 17.99 / 62.85 / 73.83 / 86.68 / 92.52 | This is the relevant boundary for reasoning-trajectory or localizability-supervision claims. |
| GLOBE-7B | [arXiv 2506.14674, Table 2](https://arxiv.org/html/2506.14674) | IM2GPS3K | 9.84 / 40.18 / 56.19 / 71.45 / 82.38 | Not a standard closed-world SOTA claim for IM2GPS3K street-level accuracy. |

## Web-Scale And Leakage-Aware Boundary

| Work | Primary source table | Setting | IM2GPS3K / Im2GPS3k | YFCC4K | Review implication |
| --- | --- | --- | --- | --- | --- |
| GeoSearch + GeoRanker | [arXiv 2604.25390, Table 1](https://arxiv.org/html/2604.25390) | OSV-5M database, reverse image search, leakage-aware evaluation. | 23.56 / 55.06 / 67.10 / 79.81 / 89.59 | 17.50 / 35.19 / 48.19 / 63.36 / 79.28 | Strong open-world/web boundary, but not directly comparable to closed-world MP16-family tables. |
| GeoSearch + G3 | [arXiv 2604.25390, Table 1](https://arxiv.org/html/2604.25390) | OSV-5M database, reverse image search, leakage-aware evaluation. | 23.49 / 54.92 / 66.87 / 79.58 / 89.42 | 17.53 / 35.21 / 48.19 / 63.49 / 79.85 | Best YFCC4K row in GeoSearch's leakage-aware table, but much lower than closed-world GeoRouter/GeoRanker YFCC4K rows because the setting is different. |
| GeoSearch | [arXiv 2604.25390, Table 2](https://arxiv.org/html/2604.25390) | Im2GPS3k under data leakage comparison. | 23.56 / 55.06 / 67.10 / 79.81 / 89.59 | N/A | Useful warning that leakage protocol can materially change claims. |

## Current SOTA Interpretation

For the standard closed-world IM2GPS3K/YFCC4K table extracted here, GeoRouter is the strongest boundary among the checked primary sources. GeoRanker remains an important 2025 baseline, and GeoToken's MLLM-assisted row is competitive on some IM2GPS3K thresholds but does not dominate across both datasets.

For web-scale or leakage-aware claims, GeoSearch must be reviewed separately. It reaches higher fine-grained Im2GPS3k values than the closed-world rows, but its reverse-image-search/open-world setup changes the problem definition.

For reasoning-centric claims, GLOBE/MP16-Reason-Test is a separate boundary. Its reasoning benchmark result should not be used as a direct replacement for IM2GPS3K/YFCC4K closed-world accuracy.

## Impact On This Project

The current Research Assistant Agent result should be described as:

- Workflow/product-effect smoke: `demo_ready`.
- External-provider screening: OpenAlex and arXiv usable; unauthenticated Semantic Scholar is rate-limited unless `SEMANTIC_SCHOLAR_API_KEY` is configured.
- Scientific SOTA status: not certified by the product smoke.
- Manual SOTA boundary: table-level evidence now exists for the current representative geolocalization area.

Before presenting any generated idea as SOTA, compare it explicitly against GeoRouter for closed-world benchmark claims, GeoSearch for web-scale/leakage-aware claims, and GLOBE for reasoning-specific claims.
