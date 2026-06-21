# Geolocalization Manual SOTA Review Draft

Review date: 2026-06-21
Remote commit: `8a86504 Classify external literature rate limits`
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
| GeoRouter: Dynamic Paradigm Routing for Worldwide Image Geolocalization | 2026 arXiv | Dynamic routing between retrieval and generation paradigms with distance-aware preference objective | IM2GPS3k, YFCC4k | Source says it significantly outperforms SOTA baselines | Important newer 2026 boundary; any current SOTA claim must consider paradigm routing. Source: https://arxiv.org/abs/2603.24376 |
| DualGeo: A Dual-View Framework for Worldwide Image Geo-localization | 2026 ICME signal | Segmentation + image feature fusion, dual-view contrastive learning, clustering rerank, LMM coordinate prediction | IM2GPS, IM2GPS3k, YFCC4k | Source claims street-level and city-level gains over SOTA | Important newer 2026 boundary; requires checking exact benchmark tables before claims. Source: https://arxiv.org/abs/2604.25533 |
| GeoSearch: Web-Scale Reverse Image Search and Image Matching | 2026 SIGIR signal | Web-scale reverse image search added to RAG pipeline, image matching and confidence gating | Im2GPS3k, YFCC4k | Source claims superiority under leakage-aware evaluation | Important because it changes the evaluation framing: leakage-aware/open-world retrieval may invalidate simple closed-world comparisons. Source: https://arxiv.org/abs/2604.25390 |
| TransGeoCLIP / Location Attention with LMMs | 2026 arXiv | Location-attention GPS encoding, CLIP image-text-GPS embedding, retrieval-augmented LMM inference | IM2GPS, IM2GPS3k, YFCC4k, YFCC26k | Source claims street-level gains over SOTA across named datasets | Latest source found in this pass; current SOTA claims should be treated as unsettled until its tables and assumptions are checked. Source: https://arxiv.org/abs/2606.08918 |

## Interpretation

The representative paper set is good for testing the assistant's workflow because it spans retrieval/RAG, ranking, reasoning/RL, and hierarchical-token paradigms. However, the 2026 literature search shows that the scientific frontier is moving past the original four-paper set.

The current project result should therefore be described as:

- workflow/product-effect smoke: `demo_ready`
- external-provider screening: OpenAlex and arXiv complete; Semantic Scholar rate-limited without key
- SOTA status: not certified
- novelty status: requires manual table-level judgment before any scientific claim

## Manual Review Checklist Before SOTA Claims

1. Extract exact benchmark tables for IM2GPS, IM2GPS3k, YFCC4k, YFCC26k, MP16-family datasets, and MP16-Reason where applicable.
2. Separate closed-world retrieval, open-world web search, MLLM-augmented, MLLM-free, reasoning/RL, and hierarchical-token settings.
3. Compare metrics by distance threshold rather than only by a single aggregate score.
4. Check leakage-aware evaluation assumptions, especially for Flickr-derived benchmarks and web-scale reverse image search.
5. Mark whether each generated idea is a new method, a recombination of recent methods, an evaluation protocol, or a product workflow improvement.
6. Keep `pilot_acceptable_with_follow_up` until at least one reviewer signs off on the manual SOTA table.

## Follow-up Actions

- Inspect the generated related-work matrix and missing-evidence actions for each representative smoke.
- Create a durable benchmark table if this project needs to make external scientific claims.
- Optionally rerun with a real Semantic Scholar API key later; this is useful, but no longer blocks the current pilot workflow.
- Do not present product-effect smoke scores as SOTA evidence.
