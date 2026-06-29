---
name: hybrid-context-search
description: Retrieve grounded research context from local chunks, evidence, gaps, ideas, embeddings, rerank scores, and GraphRAG-lite edges. Use when an agent needs source-backed context for answering questions, advisor chat, SOTA review, proposal writing, or replaying retrieval bad cases.
---

# Hybrid Context Search

## Purpose

Find source-backed context without relying on a single retrieval mode. The current local baseline combines lexical scoring, deterministic query variants, SQLite-backed vector rows, optional external embeddings/rerank, section-aware chunk context, compressed evidence snippets, and GraphRAG-lite neighborhood expansion.

## Backing APIs And Tools

- `POST /research/context/search`
- Tool manifest name: `search_research_context`
- SQLite model: `ResearchEmbedding.vector_json`
- Graph models: `ResearchNode`, `ResearchEdge`

## Workflow

1. Normalize the user question into a concise retrieval query.
2. Let the retrieval service generate bounded query variants; do not manually expand into many provider-heavy searches unless an evaluation miss justifies it.
3. Pass relevant `paper_ids` or `idea_id` filters when the user is asking about a known artifact.
4. Request graph context when lineage, task links, evidence ledgers, or related ideas matter.
5. Prefer cited chunks/evidence and `compressed_evidence` snippets over generated summaries when composing an answer.
6. Report gaps when search returns weak or missing evidence; do not fill missing citations with model guesses.

## Safety Boundaries

- Do not expose raw API keys or `.env` values in retrieval traces.
- Do not treat vector similarity as proof; use it as candidate recall.
- Do not treat compressed snippets as the full source; use them as evidence spans linked back to chunks/evidence.
- Keep SQLite as the default local store unless measured scale or latency justifies Milvus, Qdrant, pgvector, or another vector database.

## Failure Handling

- If lexical search misses but vector hits exist, cite the vector-rescued chunks and note the weaker lexical match.
- If filters remove all results, retry only with explicit operator intent or return a scoped no-match result.
- If external embedding providers rate-limit, prefer the local hash baseline for regression runs and preserve strict external runs for smaller provider checks.
- Save recurring misses as replay cases once replay tooling is available.

## Verification

- Run `bash scripts/check_context_search_evaluations.sh` after retrieval, embedding, rerank, graph-expansion, SOTA, or benchmark-evidence changes.
- Run `bash scripts/check_graph_rag_lite.sh` after graph node/edge behavior changes.
