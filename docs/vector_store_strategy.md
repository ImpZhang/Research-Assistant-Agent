# Vector Store Strategy

This document defines the current local vector-store boundary for the personal Research Assistant Agent target.

## Current Implementation

The project does not require Milvus, Qdrant, pgvector, or another external vector database for the current local single-operator workflow.

Current retrieval storage is:

- relational SQLite for source artifacts and metadata;
- `ResearchEmbedding.vector_json` rows for evidence, gap, and idea vectors;
- deterministic `local_hash_embedding_v0` vectors when no external embedding provider is configured;
- optional external embedding vectors when `RETRIEVAL_EMBEDDING_PROVIDER=auto` or `external` and `EMBEDDER`, `EMBEDDER_BASE_URL`, and `EMBEDDER_API_KEY` are configured;
- optional learned rerank when `RETRIEVAL_RERANK_PROVIDER=auto` or `external` and rerank settings are configured.

This keeps clone-to-run setup simple: a user can run the agent with only SQLite and still get lexical/vector/GraphRAG-lite retrieval. Learned embedding and rerank providers improve quality without adding a local vector database service.

## Why Not Milvus By Default

Milvus is not the default local dependency because the current product target is a personal local agent, not a hosted multi-user retrieval platform.

Defaulting to Milvus would add:

- another service to install, run, back up, and diagnose;
- extra disk and memory overhead for small personal collections;
- service lifecycle and volume cleanup risks;
- a harder clone-to-run path for users who only want paper ingestion, idea generation, and local benchmark flow.

For the current scale, SQLite vector rows plus application-side cosine scoring are easier to inspect, back up, and remove cleanly.

## When To Migrate

Introduce Milvus, Qdrant, pgvector, or another dedicated vector store only after one or more of these become measured bottlenecks:

- more than roughly 50k-100k indexed research objects in a single local checkout;
- context-search latency remains too high after query/result limits and indexing improvements;
- multi-project or multi-user isolation becomes a real product requirement;
- visual/page-image embeddings require large multimodal vector collections;
- filtered vector search needs database-native ANN indexes rather than application-side scoring;
- local backup/restore requirements can cover the vector service volume safely.

Before migration, add a retrieval evaluation fixture that compares current SQLite vector rows against the proposed vector store on hit@k, MRR, latency, and backup complexity.

## Migration Shape

If a dedicated vector store becomes necessary, keep it optional:

- preserve SQLite `ResearchEmbedding` as the portable local baseline;
- add a provider interface rather than hard-coding Milvus into workflow services;
- keep `scripts/check_local_doctor.sh` useful when the external vector store is absent;
- store enough metadata in SQLite to rebuild external vector collections;
- document backup/restore for the vector service before enabling it in any default suite.

Milvus Lite can be useful for local experiments, but it should not become the default until file-locking, cleanup, and backup behavior are boring for this repository. Milvus Standalone is more appropriate for a hosted or shared service target, which is currently out of scope.

## Current Operator Commands

Rebuild the local embedding index through the API:

```http
POST /research/embeddings/rebuild
```

Check provider readiness without printing secrets:

```bash
python3 scripts/check_model_provider_config.py
```

Run retrieval and context-search focused checks before changing vector scoring, embedding behavior, or rerank behavior:

```bash
bash scripts/check_context_search_evaluations.sh
```

For a fresh clone, no vector database setup step is required.
