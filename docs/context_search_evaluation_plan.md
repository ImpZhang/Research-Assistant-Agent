# Context Search Evaluation Plan

This document defines how to evaluate and calibrate context search before introducing a full GraphRAG indexing/community-summary pipeline. It is design-only: it does not run evaluation jobs, read secrets, change data, start services, add dependencies, or modify deployment behavior.

## Purpose

Context search now combines lexical scoring, local hash-vector hits, optional GraphRAG-lite neighbor expansion, edge-type filters, stable ranking tie-breaks, and per-result score breakdowns. The next improvement should be evidence-led calibration, not arbitrary weight changes.

This plan defines the minimum evaluation harness needed to decide whether scoring changes improve research usefulness.

## Current Retrieval Contract

`POST /research/search/context` returns:

- matched evidence records;
- matched research gaps;
- matched ideas;
- GraphRAG-lite nodes and edges when `include_graph=true`;
- optional edge filtering through `graph_edge_types`;
- per-result `score_breakdown` values for lexical, bonus, phrase, and vector contributions;
- a short deterministic answer brief.

The public retrieval method remains `lexical_vector_graph_rag_lite_v0`.

## Evaluation Questions

Evaluate changes against these questions:

- Does the top evidence actually support the query?
- Do top gaps and ideas connect to the same research intent as the query?
- Does graph expansion add useful lineage instead of unrelated graph noise?
- Do vector hits rescue relevant items that lexical matching misses?
- Do score breakdowns explain ranking decisions clearly enough for Workbench, MCP bridge, and external planner consumers?
- Does edge-type filtering reduce noise without hiding critical context?

## Dataset Shape

Use small, committed, non-sensitive fixtures first:

- synthetic papers with known evidence/gap/idea targets;
- query strings with expected evidence ids, gap ids, idea ids, or edge types;
- negative queries that should return little or no context;
- graph-heavy queries where graph neighbor expansion is expected to help;
- lexical-miss/vector-hit cases.

Do not use private customer data, `.env` values, API keys, cookies, private notes, or raw confidential papers in committed fixtures.

## Metrics

Start with deterministic ranking metrics:

- `hit_at_1` for expected evidence/gap/idea ids;
- `hit_at_3` and `hit_at_5` for broader context relevance;
- `mrr` for expected primary artifacts;
- `graph_edge_hit_rate` for expected edge types;
- `graph_noise_rate` for unrelated or unknown edge types returned with filters;
- `score_breakdown_coverage` to ensure each result exposes lexical/bonus/phrase/vector keys;
- `score_breakdown_total_match_rate` to ensure per-result score breakdown totals match visible scores within rounding tolerance;
- `paper_filter_leak_rate` to ensure scoped context searches do not return evidence, gaps, or ideas from excluded papers;
- `empty_query_guard_rate` for invalid or too-short queries.

Later, if model-backed judging is introduced, it must be optional and secret-safe.

## Calibration Rules

Do not change scoring weights unless an evaluation fixture shows a problem:

- Increase lexical weight only when exact query terms are under-ranked despite being relevant.
- Increase vector weight only when semantic matches are consistently missed by lexical scoring.
- Adjust bonus fields only when artifact-specific confidence/quality signals correlate with better human judgment.
- Adjust graph expansion only when graph edges are useful but underrepresented, or noisy and overrepresented.
- Keep stable tie-breaks unless they contradict measured relevance.

Every scoring change should include before/after metrics in the progress log.

## Test Harness Direction

A first implementation should be a local test or script that:

1. Loads synthetic fixture papers through the existing API or service layer.
2. Runs the literature-to-ideas workflow with deterministic fallbacks.
3. Rebuilds local hash embeddings for fixture artifacts.
4. Runs configured context-search queries.
5. Compares returned ids, edge types, and score breakdowns against expected fixtures.
6. Prints aggregate metrics and fails on regressions.

Prefer pytest fixtures for small deterministic checks. Add a script only if metric output becomes too large for unit tests. Committed fixtures now cover evidence hit@k, MRR, graph edge hit/noise checks, multi-edge-type filter checks, score breakdown coverage, idea overall-score bonus scoring, gap feasibility bonus scoring, evidence confidence bonus scoring, exact phrase bonus scoring, score breakdown total consistency, paper-filter leak checks, graph paper-filter leak checks, graph expansion recall under recent-edge noise, no-match scoped queries, lexical-miss/vector-hit rescue, and `empty_query_guard_rate` for empty, too-short, and punctuation-only queries. Run `bash scripts/check_context_search_evaluations.sh` as the focused remote check before changing scoring or graph-expansion behavior.

## Operational Guardrails

- Do not run live-server evaluation without operator confirmation if it starts services or writes to production-like data.
- Do not run external model judging unless credentials and privacy rules are explicit.
- Do not commit real customer papers or private annotations.
- Do not tune against a single happy-path query.
- Keep evaluation fixtures small enough for focused CI and remote-first development.

## Acceptance Criteria

A retrieval calibration change is ready when:

- focused evaluation tests pass;
- the changed scoring behavior improves or preserves relevant metrics;
- score breakdowns still sum to the visible score within rounding tolerance;
- context-search API compatibility is preserved;
- README, technical design, TODO, and progress log describe the change;
- no secrets or private data are introduced.

## Open Questions

- Should retrieval evaluation live only in pytest, or also in `scripts/` for operator reports?
- What minimum fixture set represents the first customer pilot domain?
- Should Workbench expose score breakdowns visually, or keep them API-only for now?
- Should graph edge filtering be evaluated per edge type or per workflow artifact family?
- When project/user scoping lands, should retrieval evaluation include cross-project isolation checks?
