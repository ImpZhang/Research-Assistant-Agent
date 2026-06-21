# Geolocalization Manual SOTA Review Draft

Review date: 2026-06-21
Remote commit: `cfc409d Compact external literature generated queries`
Representative review record: `539e9028aa364ce58da8a4e0e2254b2b`

## Decision

The operator approved the OpenAlex + arXiv + manual-review path instead of blocking the pilot workflow on a real Semantic Scholar API key. Semantic Scholar support remains implemented through `SEMANTIC_SCHOLAR_API_KEY`, but unauthenticated live requests currently return a rate-limit status.

This review treats automated external-provider search as screening evidence only. It does not certify that generated research ideas are scientifically novel or state-of-the-art.

## Latest Automated Evidence

Four representative geolocalization smokes were run with external literature enabled and providers `openalex,arxiv,semantic_scholar`.

| Paper | Score | Band | Evidence-ledger coverage | External status |
| --- | ---: | --- | ---: | --- |
| GeoRanker | 0.9505 | demo_ready | 0.9333 | `partial:openalex:completed,arxiv:completed,semantic_scholar:rate_limited:HTTPError_429` |
| G3 | 0.9468 | demo_ready | 0.8517 | `partial:openalex:completed,arxiv:completed,semantic_scholar:rate_limited:HTTPError_429` |
| GeoToken | 0.9485 | demo_ready | 0.8933 | `partial:openalex:completed,arxiv:completed,semantic_scholar:rate_limited:HTTPError_429` |
| Recognition through Reasoning | 0.9485 | demo_ready | 0.8933 | `partial:openalex:completed,arxiv:completed,semantic_scholar:rate_limited:HTTPError_429` |

Average product-effect score: `0.9486` / `demo_ready`.
Average evidence-ledger coverage: `0.8929`.
Raw smoke JSON: `/tmp/raa_external_smokes_8a86504`.

## Manual SOTA Screening Table

| Work | Date / venue signal | Main idea | Benchmarks named by source | Claimed SOTA signal | Review implication |
| --- | --- | --- | --- | --- | --- |
| G3: An Effective and Adaptive Framework for Worldwide Geolocalization Using Large Multi-Modality Models | 2024, NeurIPS paper source | RAG-style geo-alignment, geo-diversification, and geo-verification with large multimodality models | IM2GPS3k, YFCC4k | Source says experiments verify superiority over prior SOTA methods | Useful representative baseline for RAG-style worldwide geolocalization, but no longer sufficient as the latest SOTA boundary by itself. Source: https://arxiv.org/abs/2405.14702 |
| GeoRanker: Distance-Aware Ranking for Worldwide Image Geolocalization | 2025, NeurIPS signal | Distance-aware ranking with LVLM query-candidate interaction and multi-order distance loss | IM2GPS3K, YFCC4K | Source says it achieves SOTA on IM2GPS3K and YFCC4K and significantly outperforms current best methods | Strong 2025 representative ranking baseline and useful for testing whether the assistant can detect ranking/distance-loss contributions. Source: https://arxiv.org/abs/2505.13731 |
| Recognition through Reasoning / GLOBE | 2025, NeurIPS signal | RL-style LVLM optimization for localizability, visual-cue reasoning, and geolocation accuracy | Diverse geolocalization tasks, MP16-Reason mentioned by source | Source says GLOBE outperforms SOTA open-source LVLMs and improves reasoning trajectories | Useful for reasoning-centric geolocalization review; should not be collapsed into retrieval-only baselines. Source: https://arxiv.org/abs/2506.14674 |
| GeoToken: Hierarchical Geolocalization via Next Token Prediction | 2025, ICDM signal | Autoregressive S2-cell hierarchy with beam/multi-sample inference | Im2GPS3k, YFCC4k | Source says MLLM-free version improves up to 13.9%, and MLLM-augmented version sets SOTA across all metrics | Useful for hierarchical token prediction baseline; manual review must compare against both MLLM-free and MLLM-augmented settings. Source: https://arxiv.org/abs/2511.01082 |
| GeoRouter: Dynamic Paradigm Routing for Worldwide Image Geolocalization | 2026 arXiv | Dynamic routing between retrieval and generation paradigms with distance-aware preference objective | IM2GPS3k, YFCC4k | Source says it significantly outperforms SOTA baselines | Exact benchmark follow-up marks this as the strongest checked closed-world/non-web boundary on IM2GPS3K and YFCC4K in this pass. Source: https://arxiv.org/abs/2603.24376 |
| DualGeo: A Dual-View Framework for Worldwide Image Geo-localization | 2026 ICME signal | Segmentation + image feature fusion, dual-view contrastive learning, clustering rerank, LMM coordinate prediction | IM2GPS, IM2GPS3k, YFCC4k | Source claims street-level and city-level gains over SOTA | Exact benchmark follow-up shows fine-grained gains over selected baselines, but not a reset of the overall closed-world boundary. Source: https://arxiv.org/abs/2604.25533 |
| GeoSearch: Web-Scale Reverse Image Search and Image Matching | 2026 SIGIR signal | Web-scale reverse image search added to RAG pipeline, image matching and confidence gating | Im2GPS3k, YFCC4k | Source claims superiority under leakage-aware evaluation | Exact benchmark follow-up keeps this as a separate web-scale/leakage-aware boundary rather than merging it into the closed-world leaderboard. Source: https://arxiv.org/abs/2604.25390 |
| TransGeoCLIP / Location Attention with LMMs | 2026 arXiv | Location-attention GPS encoding, CLIP image-text-GPS embedding, retrieval-augmented LMM inference | IM2GPS, IM2GPS3k, YFCC4k, YFCC26k | Source claims street-level gains over SOTA across named datasets | Exact benchmark follow-up shows gains over G3 but lower standard IM2GPS3K/YFCC4K rows than GeoRanker/GeoRouter, so it does not reset the checked boundary. Source: https://arxiv.org/abs/2606.08918 |


## Exact Benchmark Follow-up

A durable table-level follow-up now lives in `docs/geolocalization_benchmark_sota_table.md`. The main conclusion from that extraction is:

- GeoRouter is the strongest checked closed-world/non-web boundary on IM2GPS3K and YFCC4K among the primary sources extracted in this pass.
- GeoSearch is a separate web-scale/leakage-aware boundary and must not be merged into the closed-world leaderboard without caveats.
- GLOBE/MP16-Reason-Test is a reasoning-specific boundary, not a direct replacement for IM2GPS3K/YFCC4K closed-world accuracy.
- Product-effect smoke scores remain workflow readiness evidence, not scientific SOTA evidence.

## Interpretation

The representative paper set is good for testing the assistant's workflow because it spans retrieval/RAG, ranking, reasoning/RL, and hierarchical-token paradigms. However, the 2026 literature search shows that the scientific frontier is moving past the original four-paper set.

The current project result should therefore be described as:

- workflow/product-effect smoke: `demo_ready`
- external-provider screening: OpenAlex and arXiv complete; Semantic Scholar rate-limited without key
- SOTA status: not certified
- novelty status: requires manual table-level judgment before any scientific claim

## Manual Review Checklist Before SOTA Claims

1. Use `docs/geolocalization_benchmark_sota_table.md` as the current exact-table boundary, and update it when new IM2GPS, IM2GPS3k, YFCC4k, YFCC26k, MP16-family, or MP16-Reason sources are added.
2. Separate closed-world retrieval, open-world web search, MLLM-augmented, MLLM-free, reasoning/RL, and hierarchical-token settings.
3. Compare metrics by distance threshold rather than only by a single aggregate score.
4. Check leakage-aware evaluation assumptions, especially for Flickr-derived benchmarks and web-scale reverse image search.
5. Mark whether each generated idea is a new method, a recombination of recent methods, an evaluation protocol, or a product workflow improvement.
6. Keep `pilot_acceptable_with_follow_up` until at least one reviewer signs off on the manual SOTA table.

## Implementation Follow-up From Artifact Inspection

Inspection of the external-provider smokes found that related-work refreshes could send 1600-character generated idea descriptions to external providers. This could make OpenAlex return HTTP 400 and could produce contradictory statuses such as `failed:openalex:completed,...` when one provider completed without items and another provider timed out. The external literature service now compacts generated external queries to short content-term searches and treats any completed provider as a partial external search rather than a full failure.

A GeoRanker external smoke after this change scored `0.9483` / `demo_ready` with no failed checks, and the related-work matrix reported `partial:openalex:completed,arxiv:failed:ReadTimeout,semantic_scholar:rate_limited:HTTPError_429` instead of a contradictory failed status.

## Follow-up Actions

- Inspect the generated related-work matrix and missing-evidence actions for each representative smoke.
- Keep `docs/geolocalization_benchmark_sota_table.md` current before making external scientific claims.
- Optionally rerun with a real Semantic Scholar API key later; this is useful, but no longer blocks the current pilot workflow.
- Do not present product-effect smoke scores as SOTA evidence.
