# Agent Engineering Strengthening Plan

This document turns the current agent-interview gap analysis into an implementation roadmap for the personal local Research Assistant Agent target.

The goal is not to replace the stable backend workflow. The goal is to add the missing agent-engineering layer around it: traceable tool calling, reusable skills, replayable bad cases, and one isolated LangGraph workflow where graph semantics actually help.

## Current Baseline

The project is already beyond a basic RAG chatbot:

- Hybrid retrieval covers source chunks, evidence, research gaps, and ideas.
- SQLite persists papers, chunks, embeddings, evidence, gaps, ideas, jobs, tasks, reviews, experiments, graph nodes, and graph edges.
- GraphRAG-lite records lineage through `ResearchNode` and `ResearchEdge`.
- The initial agent trace foundation persists `AgentRun`, `ToolCallRecord`, and `ReplayCase` rows with secret redaction and read-only trace inspection tools.
- Advisor chat now creates an `advisor_chat` run and records its cockpit/context read calls as `ToolCallRecord` rows without changing the existing response contract.
- The Workbench, HTTP API, local scripts, and optional stdio MCP-to-HTTP bridge expose the system locally.
- Focused checks cover context-search metrics, graph behavior, tool bridge contracts, workflow primitives, backup manifests, and local readiness.

The project is not yet a full autonomous agent runtime:

- The production workflow is service-layer orchestration; the LangGraph path is an isolated opt-in Advisor deep-review example, not the default runtime.
- The MCP surface is a lightweight bridge over FastAPI, not a full MCP SDK server with resources and prompts.
- Advisor responses now use a bounded deterministic read-tool plan over approved tools; they are not yet an LLM-ranked tool-calling loop.
- Replay and LangGraph flows do not yet write trace records automatically.
- The project-local skill registry now covers core workflows under `skills/*/SKILL.md` and is validated by `scripts/check_project_skills.sh`.

This is an intentional boundary. The current stable workflow should stay intact while the new agent layer is added incrementally.

## Non-Goals

- Do not rewrite `WorkflowService` into LangGraph just to claim LangGraph usage.
- Do not make MCP the required runtime for local users.
- Do not require Milvus, Qdrant, pgvector, Redis, or a message queue for the default clone-to-run path.
- Do not introduce multi-agent handoff before Planner, Verifier, Reporter, or Tool Executor responsibilities are clearly separated.
- Do not log secrets, raw `.env` values, API keys, cookies, private keys, or full private paper content in trace or replay artifacts.

## P0 Agent Engineering Roadmap

### 1. Agent Run And Tool Call Trace

Add durable trace tables before changing agent behavior.

Initial status: the tables, service, create/read API, secret redaction, read-only tool-manifest entries, Advisor chat trace wiring, and failed Advisor read-tool replay capture are implemented. The next step is extending replay workflow run creation and adding richer live replay executors for retrieval/citation/SOTA cases.

Proposed artifacts:

- `AgentRun`: one row per advisor/tool-calling/replay/LangGraph run.
- `ToolCallRecord`: one row per selected tool call.
- `ReplayCase`: saved inputs, expected behavior, observed behavior, and replay metadata.

Suggested fields:

- `AgentRun`: `id`, `run_type`, `status`, `question`, `input_json`, `output_json`, `error`, `started_at`, `finished_at`, `created_by`, `model_name`, `latency_ms`, `token_usage_json`, `metadata_json`.
- `ToolCallRecord`: `id`, `agent_run_id`, `tool_name`, `tool_arguments_json`, `tool_result_summary`, `status`, `error`, `latency_ms`, `side_effect`, `created_at`.
- `ReplayCase`: `id`, `source_agent_run_id`, `case_type`, `query`, `expected_json`, `observed_json`, `verdict`, `notes`, `created_at`.

Acceptance criteria:

- Advisor chat can create an `AgentRun`; replay flows still need first-class run creation.
- Every Advisor read-tool invocation records arguments, result summary, status, latency, and error state.
- Failed Advisor read tools automatically create `advisor_tool_failure` replay cases with expected/observed tool state.
- Trace records never store secrets or raw provider credentials.
- Tests prove failed tool calls are captured without breaking the whole request.

Interview framing:

> I added a first-class trace layer so every agent run and tool call is auditable, replayable, and measurable. This lets us debug why a tool was selected, where failures happened, and whether changes improved completion rate or retrieval quality.

### 2. Advisor Tool-Calling Agent

Convert Advisor into the first real tool-calling agent surface while preserving existing advisor response contracts.

Initial status: Advisor chat now uses a bounded read-first plan over `get_project_cockpit`, `search_research_context`, `get_idea_progress`, `get_idea_lineage`, and `list_research_tasks`. Tool calls are trace-recorded, failed read tools produce replay cases, selected/skipped tools are returned in `source_summaries.tool_plan`, and model-ranked selection remains a future extension.

Initial tool set:

- `search_research_context`
- `get_project_progress`
- `list_research_tasks`
- `get_idea_progress`
- `get_idea_lineage`
- `create_advisor_chat_tasks` only behind explicit write-policy checks

Implementation shape:

- Keep the existing deterministic advisor composer as fallback.
- Add a tool selection step that reads the tool manifest, validates arguments through schema, calls approved tools, summarizes observations, and records each call.
- Start with bounded tool plans, such as `max_tool_calls=3`, rather than open-ended autonomous loops.
- Treat write tools as side-effecting and require explicit policy checks before calling them.

Acceptance criteria:

- Advisor can answer project questions by selecting read tools.
- Tool calls appear in `ToolCallRecord`.
- Unknown tools, invalid parameters, timeouts, and empty results produce traceable fallback behavior. Failed read tools now persist failed `ToolCallRecord` rows and `advisor_tool_failure` replay cases.
- The old advisor route remains compatible for Workbench and MCP bridge clients.

Interview framing:

> I did not expose arbitrary tool execution. Advisor has a bounded tool-calling loop with schema validation, side-effect policy, trace logging, and deterministic fallback.

### 3. Project-Local Skills

Add a skill documentation layer over stable tools and workflows. This is not a runtime dependency at first; it is an operator and agent instruction layer.

Initial status: the first project-local registry is implemented with six skills and a focused validation script.

Proposed tree:

```text
skills/
  paper-ingestion/SKILL.md
  hybrid-context-search/SKILL.md
  literature-to-ideas/SKILL.md
  sota-review/SKILL.md
  benchmark-evaluation/SKILL.md
  advisor-action-session/SKILL.md
```

Each `SKILL.md` should include:

- Purpose and when to use it.
- Inputs and outputs.
- Backing API routes/tools.
- Safety rules and side-effect boundaries.
- Failure handling.
- Verification commands.
- Example invocation or workflow.

Acceptance criteria:

- Core skills map to actual APIs or scripts.
- Skills distinguish read-only, side-effecting, and human-confirmation workflows.
- The documentation index links to the skill registry.
- A focused docs check verifies required skill files exist once the registry is introduced.

Interview framing:

> I separated tool availability from skill instructions. Tools define callable APIs; skills define when and how an agent should use those APIs safely.

### 4. Bad Case Replay

Add replay support on top of trace data.

Initial status: the deterministic replay path is implemented and documented.

Completed artifacts:

- `scripts/replay_agent_case.py`
- `docs/agent_replay_eval.md`
- `scripts/check_agent_replay.sh`
- API endpoints for listing and replaying saved cases can come later.

Replay case types:

- context-search miss
- wrong evidence citation
- bad tool selection
- advisor answer missing required action
- SOTA readiness false positive
- benchmark evidence incomplete

Metrics:

- replay pass rate
- tool call success rate
- context hit@k / MRR
- graph edge hit/noise rate
- evidence citation correctness
- average tool calls
- latency

Acceptance criteria:

- A saved case can be replayed locally without reading secrets.
- Replay output compares expected versus observed behavior.
- Replay fixtures are small and non-sensitive.
- A focused check script covers at least the deterministic replay path.

Interview framing:

> I treated bad cases as first-class data. Failures can be saved, replayed, and evaluated, so improvements are measured rather than judged by ad hoc demos.

### 5. Isolated LangGraph Example Workflow

Add one new LangGraph workflow without replacing the existing production workflow.

Recommended first workflow:

```text
/research/agent/advisor-deep-review
```

Initial status: `/research/agent/advisor-deep-review` is implemented as an opt-in LangGraph workflow with `load_state`, `retrieve_context`, `verify_evidence`, and `compose_answer` nodes. It writes an `advisor_deep_review` agent run and read-tool call records, then returns an Advisor-compatible answer plus verification flags.

Candidate LangGraph nodes:

```text
load_state
retrieve_context
select_tools
verify_evidence
compose_answer
create_followup_tasks_optional
save_trace
```

State should include:

- user question
- selected paper ids / idea id
- retrieved chunks/evidence/gaps/ideas
- graph context
- tool observations
- verification flags
- final answer
- generated task ids
- agent run id

Acceptance criteria:

- The LangGraph workflow is opt-in and isolated.
- Existing `WorkflowService` and advisor routes keep working.
- Outputs persist through existing SQLAlchemy models and trace tables.
- Tests prove the graph can run locally with deterministic providers.

Interview framing:

> I kept the stable service workflow and introduced LangGraph only where DAG semantics were useful: explicit state, tool nodes, verification, optional human/write steps, and trace persistence.

## P1 Agent Quality Improvements

### Case Memory

Turn successful reports, human confirmations, review decisions, and replay outcomes into searchable memory.

Recommended initial scope:

- Persist high-value case summaries as structured artifacts.
- Embed summaries into `ResearchEmbedding` with `owner_type="case_memory"`.
- Retrieve case memories during advisor and SOTA review flows.

### Guardrails

Strengthen the local safety model:

- Prompt-injection note for untrusted PDF content.
- Read/write tool separation in tool-calling agent.
- Max tool-call count and timeout.
- Side-effect confirmation policy.
- Secret redaction in trace payloads.
- Explicit blocked-tool behavior.

### RAG Enhancements

Current dense retrieval is SQLite-backed exact cosine retrieval. Next retrieval improvements should be measured before adoption:

- BM25 or sparse lexical retrieval.
- RRF fusion across lexical and dense rankings.
- Query rewrite for underspecified advisor questions.
- HyDE only if deterministic fixtures show recall gains.
- Parent/child chunk expansion for citation context.
- Context compression for long tool observations.

### MCP Maturity

Keep MCP optional, but improve the bridge:

- Add resources for read-only project status, docs, and reports.
- Add prompt templates for common workflows.
- Keep read-only mode as the safe default for new clients.
- Do not add a second tool registry separate from `/research/tools/manifest`.

### Observability Metrics

Add aggregate metrics after trace tables exist:

Initial status: `/research/agent/metrics` summarizes run status/type counts, tool-call success rate, replay verdict distribution, average latency, tool usage, and recent failures.

- agent run count by status
- tool success/failure rate
- average tool calls per run
- average latency
- fallback rate
- replay pass rate
- retrieval metric trend
- write-tool invocation count

## P2 Deferred Enhancements

- Multi-agent handoff after role boundaries are clear.
- Full GraphRAG after corpus scale or global community-summary needs justify it.
- Milvus/Qdrant/pgvector after vector count or latency makes SQLite exact scan insufficient.
- SSE/WebSocket streaming after the Workbench UX needs stage-by-stage updates.
- LangSmith, Langfuse, OpenTelemetry, Prometheus, or Grafana after local trace metrics are stable.

## Personal Local Deployment Strengthening

The personal local target should remain simple: clone, configure `.env`, run locally, back up safely, and cleanly remove artifacts.

### High-Priority Local Improvements

- Improve `.env.example` with required, recommended, and optional model-provider variables.
- Enhance `scripts/check_local_doctor.sh` with disk-space, SQLite, Workbench, model-provider, MCP bridge, backup-manifest, and benchmark readiness summaries.
- Add a local restore rehearsal script after backup scope is stable.
- Add SQLite maintenance helpers for size reporting, WAL health, row counts, and optional vacuum guidance.
- Keep `clean.sh`, `deep-clean.sh`, and `docker-clean.sh` clearly separated from user data deletion.
- Add a shortest-path demo runbook for first-time local users.
- Keep offline/deterministic fallback behavior so users can run smoke checks without model keys.

### Local Deployment Interview Framing

> I optimized for personal local deployment rather than SaaS operations. The default path avoids external vector/database services, stores artifacts under the project root, keeps `.env` untracked, provides doctor and backup checks, and can run deterministic smoke tests without model credentials.

## Recommended Implementation Order

1. Completed: add `AgentRun`, `ToolCallRecord`, and `ReplayCase` models plus read APIs.
2. Completed: add Advisor trace creation without changing answer behavior.
3. Completed: add bounded read-only Advisor tool calling.
4. Completed: add project-local skill docs for the core workflows.
5. Completed: add replay script and deterministic replay fixtures.
6. Completed: add one isolated LangGraph advisor deep-review workflow.
7. Expand case memory, guardrails, and aggregate observability metrics.

This order keeps the current product usable while making each new agent capability observable and testable.
