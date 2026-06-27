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
- Advisor chat automatically captures a `context_search_miss` replay case when an evidence-seeking question runs `search_research_context` but returns no evidence.
- `--live-executors` also supports `citation_audit`, `citation_mismatch`, and `missing_citation` replay cases.
- The citation-audit executor checks observed `cited_evidence_ids` against local `Evidence` rows, optional `paper_ids`, and optional required citation terms.
- `--live-executors` also supports `sota_readiness`, `sota_readiness_false_positive`, and `sota_signoff_audit` replay cases.
- The SOTA-readiness executor audits local `sota_signoff_record` briefs for signoff status, manual gate readiness, external-search completion, nearest-work count, benchmark-run count, benchmark evidence readiness, and blockers.
- SOTA signoff creation automatically captures a `sota_readiness_false_positive` replay case when `signoff_status=sota_confirmed` but the manual gate is not ready for a SOTA claim.
- It does not call model providers, but it can refresh local `research_embeddings` rows in the selected SQLite database.
- Full Advisor and SOTA-review workflow re-execution remain deferred until their replay policies are narrow enough to be deterministic and safe.

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
python3 scripts/replay_agent_case.py --case-type citation_audit --live-executors --record-run --json
python3 scripts/replay_agent_case.py --case-type sota_readiness_false_positive --live-executors --record-run --json
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
- `required_cited_evidence_ids`: cited evidence ids that must appear in observed citation data.
- `forbidden_cited_evidence_ids`: cited evidence ids that must not appear.
- `cited_evidence_ids`: evidence ids to audit when not supplied by `observed_json`.
- `required_citation_terms`: terms that must appear in each audited evidence record.
- `min_citation_count`, `max_missing_citation_count`, `max_wrong_paper_citation_count`, `max_citation_term_miss_count`: citation-audit thresholds.
- `idea_id`, `sota_signoff_id` or `signoff_id`: identify the SOTA signoff to audit. If no signoff id is supplied, the latest local signoff for `idea_id` is used.
- `sota_signoff_status` or `signoff_status`: expected signoff status, such as `sota_confirmed`.
- `require_ready_for_sota_claim`, `require_effective_external_search_completed`, `require_benchmark_evidence_ready`: boolean readiness gates.
- `min_nearest_work_count`, `min_benchmark_run_count`, `max_sota_blocker_count`: SOTA-readiness count thresholds.
- `required_sota_blockers`, `forbidden_sota_blockers`: expected blocker membership checks.
- Other simple key/value pairs: compared directly against observed or derived fields.

If `expected_json` is empty, the replay verdict is `needs_review`.

## Metrics

The script reports:

- `case_count`
- `passed`
- `failed`
- `needs_review`
- `pass_rate`

The API endpoint `GET /research/agent/metrics` additionally summarizes replay verdict distribution, replay case-type distribution, `agent_replay` run status distribution, failed replay-run count, and live replay executor usage alongside agent-run and tool-call metrics. Use `GET /research/agent/metrics/export/markdown` when a local handoff or interview demo needs a readable report.

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

- Add replay case creators for wrong citations and other evidence-link mistakes.
- Extend live replay executors beyond context search/citation/SOTA audit after bounded Advisor policies exist.
- Add automatic replay report scheduling only after local operator policy exists.
