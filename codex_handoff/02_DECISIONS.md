# Decisions

This file records major decisions already made so a new Codex does not reopen settled questions without reason.

## Decision 1: Build A New Project Instead Of Merely Extending SuperMew

Decision:

- Create a new project named `Research-Assistant-Agent`.
- Use the previous `super-mew` RAG project as background/context, not as the final architecture.

Why:

- The user felt the existing RAG-only implementation was too elementary and toy-like.
- A serious research assistant needs workflow, artifact persistence, task generation, review loops, and handoff packages.

Implication:

- Do not collapse the project back into a single chatbot/RAG endpoint.
- New features should strengthen the research workflow and project execution loop.

## Decision 2: Backend-First Architecture

Decision:

- Build the core as a FastAPI backend with durable artifacts and stable HTTP APIs.
- Keep the static Workbench as a pilot UI.

Why:

- The research assistant needs many structured artifacts and long-lived state.
- Backend APIs are easier to expose to future frontend, MCP clients, and external planners.
- A backend-first system can be verified with automated tests and smoke workflows.

Implication:

- Add behavior to services/routes/schemas first.
- Workbench should call existing APIs rather than duplicate logic.
- Avoid putting business rules only in frontend JavaScript.

## Decision 3: Deterministic Fallbacks Are Required

Decision:

- The system must run without model credentials.
- OpenAI-compatible model calls should have deterministic local fallbacks.

Why:

- Development and tests should not require paid or unstable external model access.
- Customer pilots may need safe fallback behavior.
- Smoke tests must be repeatable.

Implication:

- Do not make core tests depend on real LLM calls.
- When adding a model-backed feature, also add deterministic fallback behavior or route it through existing services that already fallback.

## Decision 4: GraphRAG-lite First

Decision:

- Use GraphRAG-lite: relational node/edge tables plus graph-aware retrieval and lineage.
- Do not introduce full GraphRAG indexing/community summarization in the first phase.
- Do not introduce Neo4j yet.

Why:

- Full GraphRAG is powerful but heavy.
- The current priority is traceability across ideas, evidence, plans, experiments, tasks, and project delivery artifacts.
- SQLite node/edge tables are enough for first customer/pilot workflows.

Implication:

- Continue writing graph links through `ArtifactGraphService`.
- Add node/edge coverage for new durable artifacts.
- Keep edge names explicit and stable.
- Save full GraphRAG/Neo4j for later scale and global knowledge reasoning.

## Decision 5: Do Not Migrate DeerFlow Now

Decision:

- Do not migrate DeerFlow into the project now.
- Borrow useful concepts such as long-running tasks, tool harnesses, memory, and multi-agent planning later.

Why:

- DeerFlow is a larger long-horizon agent harness.
- Current project already has a domain-specific workflow shape.
- Migrating DeerFlow early would slow down the core product.

Implication:

- If a future feature needs explicit graph orchestration, evaluate LangGraph/DeerFlow then.
- Do not make DeerFlow a dependency for ordinary research workflow endpoints.

## Decision 6: MCP Is An Adapter Layer, Not The Core

Decision:

- Provide a stable tool manifest and MCP-ready spec.
- Provide a lightweight stdio MCP-to-HTTP bridge.
- Do not build core logic inside MCP.

Why:

- MCP is valuable for external clients and agents.
- The HTTP API should remain the single source of tool truth.
- Avoid maintaining a second route/tool registry.

Implication:

- New stable endpoints should be added to `/research/tools/manifest`.
- `/research/tools/mcp-spec` should derive from the manifest.
- MCP bridge should load the spec rather than hardcoding tools.
- Unknown clients should start read-only or allowlisted.

## Decision 7: Project Bundle And Release Loop Are The Customer-Facing Spine

Decision:

- Treat project bundle, release notes, feedback, closeout, acceptance packet, review session, review outcome, and outcome progress as the path toward real customer-facing value.

Why:

- A serious research assistant must not stop at generating ideas.
- Users need to show progress, get feedback, close actions, and preserve signoff evidence.
- Handoff artifacts make the system usable for advisors, collaborators, customers, and external agents.

Implication:

- Prioritize delivery-loop features over decorative UI.
- Persist key handoff states as `ResearchBrief` records.
- Include handoff records in project bundle metadata, Markdown artifacts, and manifest fields.

## Decision 8: Every Completed Round Gets Pushed

Decision:

- Each completed implementation round should be committed and pushed to GitHub.

Why:

- The user wants backup after each round.
- The remote/GitHub state should remain recoverable and usable from new machines.

Implication:

- Do not leave finished work only in a local mirror.
- Verify before pushing.
- Use concise commit messages.
- Do not commit secrets.

## Decision 9: Keep Existing Repo Patterns

Decision:

- Extend existing routes, schemas, services, tests, smoke script, Workbench, README, and docs in the same style.

Why:

- The codebase has grown a consistent artifact pattern.
- New capabilities should be traceable and testable in the same way as old ones.

Pattern for durable handoff artifact features:

1. Add Pydantic input/response schema in `backend/research/schemas.py`.
2. Add route handlers in `backend/research/routes.py`.
3. Store durable records in existing models when possible, often `ResearchBrief`.
4. Add graph links in `backend/research/services/artifact_graph_service.py`.
5. Add task generation in `backend/research/services/task_service.py` if the artifact should drive work.
6. Add tool manifest entries.
7. Add project bundle metadata/artifacts/manifest fields when relevant.
8. Add Workbench controls.
9. Add tests in `tests/test_app.py`.
10. Add smoke coverage in `scripts/smoke_api.py`.
11. Update `README.md` and design/requirements docs.

## Decision 10: Do Not Store Secrets In Docs

Decision:

- Never write real passwords, API keys, cookies, tokens, or private keys in repository files.

Why:

- The project will be pushed to GitHub.
- The user explicitly requested no secrets in handoff docs.

Implication:

- `.env.example` may contain empty placeholders.
- Handoff docs may mention variable names but not values.
- If SSH or API credentials are needed, ask the user to provide them through secure local configuration, not in Markdown.

## Rejected Or Deferred Options

### Full GraphRAG / Neo4j Immediately

Status: deferred.

Reason:

- Too heavy for the current phase.
- The immediate need is traceability and artifact graph context, which GraphRAG-lite handles.

### DeerFlow Migration

Status: deferred.

Reason:

- It would add a large agent harness before the domain workflow stabilizes.
- Current FastAPI workflow services are easier to verify.

### MCP As The Main Runtime

Status: rejected for core path, accepted as adapter.

Reason:

- MCP should expose tools; it should not own product state or route logic.

### Pure Frontend App First

Status: rejected.

Reason:

- The hard part is durable research state and workflow correctness.
- A frontend-only demo would recreate the original toy problem.

### Only Improve RAG Quality

Status: rejected.

Reason:

- The user wants research ideas, execution, and handoff, not just better retrieval answers.

## Attention Points

- The `backend/research/routes.py` file is large and central. Make tightly scoped edits.
- `tests/test_app.py` and `scripts/smoke_api.py` are long but important; update both for new capabilities.
- Preserve deterministic behavior in tests.
- Keep Workbench as a caller of API routes, not a second state machine.
- Do not accidentally commit generated DB files, uploaded papers, `.env`, or secrets.
- Remote root has two historical untracked docs; do not delete or fold them into commits unless the user explicitly asks.

