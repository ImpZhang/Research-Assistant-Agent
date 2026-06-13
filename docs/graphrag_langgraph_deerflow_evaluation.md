# GraphRAG, LangGraph, And DeerFlow Revisit

This document records the Priority 6 revisit for heavier graph retrieval and workflow orchestration. It is design-only: it does not add dependencies, change runtime behavior, start services, run migrations, or replace the current workflow implementation.

## Decision Summary

Keep the current GraphRAG-lite and service-layer workflow architecture for now.

- Do not introduce a full GraphRAG indexing/community-summary pipeline yet.
- Do not refactor the existing literature-to-ideas workflow into LangGraph just because the dependency exists.
- Do not migrate the project into DeerFlow.
- Keep the stable FastAPI routes, SQLAlchemy artifacts, job traces, tool manifest, and MCP bridge contract as the integration boundary.

The next upgrade should be incremental: improve GraphRAG-lite retrieval quality and observability first, then introduce LangGraph for a new isolated workflow only when resumable DAG behavior is required. Treat DeerFlow as a future external planner/tool consumer, not the core runtime.

## Current Implementation Observations

Current graph storage is intentionally lightweight:

- `ResearchNode` stores `node_type`, `label`, `canonical_key`, and JSON payload.
- `ResearchEdge` stores source/target node ids, `edge_type`, weight, evidence ids, and JSON payload.
- `GraphService` provides thin node/edge list and create helpers.
- `ArtifactGraphService` writes traceability edges as artifacts are created, including proposal, review, task, experiment, evidence-ledger, cockpit, triage, bundle, release, feedback, acceptance, review outcome, and signoff relationships.

Current context retrieval is also lightweight:

- `RetrievalService.search_context` combines lexical scoring, local hash-vector hits, and GraphRAG-lite neighbor expansion.
- The public retrieval method is labeled `lexical_vector_graph_rag_lite_v0`.
- `POST /research/search/context` returns scored evidence, gaps, ideas, graph nodes, graph edges, and an answer brief.
- `GET /research/graph/nodes` and `GET /research/graph/edges` expose read-only graph inspection.
- Tests and smoke coverage assert context search, graph nodes, graph edges, and many artifact-specific graph edge types.

Current workflow orchestration is service-layer first:

- `WorkflowService` runs the literature-to-ideas sequence and updates a `jobs` row.
- Async execution currently uses FastAPI `BackgroundTasks`; durable queue migration is documented separately in `docs/workflow_queue_design.md`.
- `backend/research/graphs/__init__.py` is currently only a placeholder for future LangGraph workflow modules.
- `pyproject.toml` includes LangChain and LangGraph dependencies, but the current production path is not a full LangGraph runtime graph.

## Why Full GraphRAG Is Not Next

Full GraphRAG is attractive for global corpus structure, community summaries, and multi-hop questions over a large document set. The current project does not yet show the operational need for that complexity.

Reasons to defer:

- Current first-pilot value comes from artifact traceability and customer-facing workflow state, not corpus-scale community detection.
- GraphRAG-lite already gives deterministic lineage for papers, evidence, gaps, ideas, tasks, claims, releases, and signoff artifacts.
- A full indexing pipeline would introduce more data movement, background jobs, storage decisions, and rebuild semantics before migration tooling is settled.
- The current corpus and test flow are small enough that local lexical/vector retrieval plus graph expansion is easier to reason about and verify.

## When Full GraphRAG Becomes Worth It

Revisit full GraphRAG when at least two of these are true:

- The corpus spans many projects, domains, or hundreds/thousands of papers.
- Users need global summaries of clusters, methods, datasets, claims, or research communities.
- Query quality is limited by local neighbor expansion rather than evidence extraction or artifact coverage.
- Operators accept an offline indexing pipeline with rebuild schedules, storage policy, and monitoring.
- The product needs cross-project synthesis, not just single-project lineage and handoff.

## LangGraph Recommendation

LangGraph remains a good fit for future stateful workflows, but the next step should not be a wholesale rewrite.

Use LangGraph when a new workflow needs:

- Explicit resumable DAG state.
- Human-in-the-loop gates.
- Streaming stage events.
- Branching or parallel agent/tool execution.
- Checkpointing that is clearer than the current `jobs` table progress model.

Do not use LangGraph just to wrap existing linear service calls. The current workflow already has stable routes, tests, job traces, and artifact outputs. A premature refactor would add risk without improving pilot value.

Recommended LangGraph path:

1. Keep existing routes and response contracts unchanged.
2. Choose one new workflow that benefits from DAG semantics.
3. Implement it behind a service boundary, not directly in route handlers.
4. Persist outputs through existing SQLAlchemy models and graph edges.
5. Add job trace, smoke, and Workbench compatibility before expanding to other workflows.

## DeerFlow Recommendation

Do not migrate into DeerFlow.

DeerFlow-style long-horizon planning may become useful for automatic deep research reports, multi-tool web research, or sandboxed agent execution. That is different from the current first-pilot product, which is a structured research workflow backend with stable APIs and traceable artifacts.

Treat DeerFlow as a possible external consumer later:

- It can read `/research/tools/manifest` or `/research/tools/mcp-spec`.
- It can call stable HTTP/MCP bridge tools.
- It should not own the database schema, artifact lineage, or core workflow state.
- It should not bypass API-key, audit, admin, or tool side-effect policy.

## Near-Term Improvements Before Heavy Frameworks

Prefer these smaller improvements first:

- Add graph edge quality checks for duplicate or orphan edges.
- Continue graph stats/readiness reporting beyond the initial `/research/graph/stats` node/edge, orphan, and duplicate counts.
- Continue edge quality hardening beyond new-write duplicate edge reuse, including historical duplicate cleanup only after backup/migration policy is explicit.
- Improve retrieval scoring and ranking explainability.
- Continue bounded graph-neighborhood controls beyond the initial `graph_edge_types` filter, such as depth controls and owner/project scope after scoping is implemented.
- Add tests for graph expansion limits and high-cardinality edge sets.
- Document the graph edge taxonomy as it stabilizes.

These improvements preserve the current lightweight architecture while making a future full GraphRAG migration easier.

## Migration Guardrails

Any heavier graph/orchestration migration must preserve:

- Existing FastAPI routes and response contracts unless a versioned replacement is introduced.
- Existing `ResearchNode` and `ResearchEdge` lineage enough for old artifacts to remain readable.
- Existing job polling and artifact hydration contracts.
- Secret-safe behavior: no raw API keys, tokens, cookies, private keys, `.env` values, or sensitive request bodies in graph payloads, job metadata, prompts, or logs.
- Operator approval before dependency sync, migrations, worker services, external crawlers, or deployment restarts.

## Acceptance Criteria For A Future Revisit

A future P6 implementation round should only start when:

- A concrete user problem cannot be solved with current GraphRAG-lite retrieval and artifact lineage.
- The operator confirms data migration, backup, and deployment implications.
- The design identifies which API contracts stay stable.
- Tests define retrieval quality or workflow durability improvements that the heavier framework must deliver.
- Rollback or coexistence strategy is documented.

## Open Questions

- What corpus size should trigger offline graph indexing?
- Should graph statistics be part of `/health/ready` or a read-only `/research/status` capability?
- Should the first LangGraph workflow be a new deep-research report workflow instead of refactoring literature-to-ideas?
- Should DeerFlow integration be tested through MCP bridge tools or direct HTTP tool manifest consumption?
- What graph edge taxonomy should be frozen before project/user scoping is implemented?
