# Agent Replay Evaluation

This document defines the first local bad-case replay path for the Research Assistant Agent.

## Scope

The default replay path is deterministic and log-based:

- It reads saved `ReplayCase` rows from the local SQLite database.
- It optionally joins the source `AgentRun` and `ToolCallRecord` rows.
- It compares stored `expected_json` against stored or derived observed behavior.
- It can write JSON or Markdown reports.
- It does not call model providers, execute tools, or read secret files.
- It only writes agent trace rows when `--record-run` is explicitly enabled.

Opt-in live replay is available for bounded local executors:

- `--live-executors` currently supports `context_search` and `context_search_miss` replay cases.
- The context-search executor re-runs `RetrievalService.search_context` with forced local hash embedding and disabled external rerank.
- It does not call model providers, but it can refresh local `research_embeddings` rows in the selected SQLite database.
- Advisor and SOTA-review workflow re-execution remain deferred until their replay policies are narrow enough to be deterministic and safe.

Opt-in trace recording is also available:

- `--record-run` persists the replay invocation as an `agent_replay` `AgentRun`.
- When live executors run, each executor is recorded as a `ToolCallRecord`, such as `replay.context_search`.
- Recorded replay runs store filter inputs, aggregate summary, per-case verdict rollups, latency, and redacted tool arguments/results.

## Command

```bash
python3 scripts/replay_agent_case.py --case-type bad_tool_selection --json
python3 scripts/replay_agent_case.py --case-id <replay_case_id> --write-markdown outputs/replay/agent-replay.md
python3 scripts/replay_agent_case.py --verdict needs_review --fail-on-regression
python3 scripts/replay_agent_case.py --case-type context_search_miss --live-executors --json
python3 scripts/replay_agent_case.py --case-type context_search_miss --live-executors --record-run --json
```

Focused verification:

```bash
bash scripts/check_agent_replay.sh
```

## Supported Expectations

`ReplayCase.expected_json` can contain:

- `tool` or `tool_name`: one required observed tool.
- `required_tool_names`: every listed tool must appear in source tool calls or observed data.
- `forbidden_tool_names`: none of these tools may appear.
- `status` or `run_status`: expected run/observed status.
- `live_status`: expected status from a live local executor, such as `completed`.
- `must_contain`: required text in observed data, source output, or tool summaries.
- `must_not_contain` / `forbidden_terms`: text that must be absent.
- `query`, `paper_ids`, `include_graph`, `graph_edge_types`, `limit`: parameters consumed by the live context-search executor.
- `required_chunk_ids`, `required_evidence_ids`, `required_gap_ids`, `required_idea_ids`: ids that must be returned by live context search.
- `min_chunk_count`, `min_evidence_count`, `min_gap_count`, `min_idea_count`: minimum result counts for live context search.
- Other simple key/value pairs: compared directly against observed or derived fields.

If `expected_json` is empty, the replay verdict is `needs_review`.

## Metrics

The script reports:

- `case_count`
- `passed`
- `failed`
- `needs_review`
- `pass_rate`

The API endpoint `GET /research/agent/metrics` additionally summarizes replay verdict distribution alongside agent-run and tool-call metrics. Use `GET /research/agent/metrics/export/markdown` when a local handoff or interview demo needs a readable report.

When `--record-run` is used, replay executions also contribute to `AgentRun` and `ToolCallRecord` observability. A replay run with any failed case is marked `failed`; a replay run with only pass or needs-review cases is marked `completed`.

These are engineering regression metrics. They do not certify scientific SOTA, model quality, or benchmark superiority.

## Safety Rules

- Do not store raw API keys, cookies, private keys, `.env` values, or private paper text in replay cases.
- Keep replay fixtures small and non-sensitive.
- Prefer ids, counts, summaries, and redacted snippets over full documents.
- Use `--fail-on-regression` in checks only when the fixture has deterministic expectations.
- Treat `--live-executors` as a local integration check: it should run against fixtures or safe local data and can update local embedding-cache rows.
- Use `--record-run` when the replay is part of an audit, release check, or regression investigation; leave it off for ad hoc dry runs.

## Next Steps

- Add replay case creators for missing citations and SOTA-readiness false positives.
- Extend live replay executors beyond context search after bounded Advisor/SOTA policies exist.
- Add aggregate replay metrics to the local observability report.
