# Agent Replay Evaluation

This document defines the first local bad-case replay path for the Research Assistant Agent.

## Scope

The current replay path is deterministic and read-only:

- It reads saved `ReplayCase` rows from the local SQLite database.
- It optionally joins the source `AgentRun` and `ToolCallRecord` rows.
- It compares stored `expected_json` against stored or derived observed behavior.
- It can write JSON or Markdown reports.
- It does not call model providers, execute tools, or read secret files.

Live re-execution of Advisor, context search, or SOTA-review workflows is intentionally deferred until bounded tool selection and replay policies are stable.

## Command

```bash
python3 scripts/replay_agent_case.py --case-type bad_tool_selection --json
python3 scripts/replay_agent_case.py --case-id <replay_case_id> --write-markdown outputs/replay/agent-replay.md
python3 scripts/replay_agent_case.py --verdict needs_review --fail-on-regression
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
- `must_contain`: required text in observed data, source output, or tool summaries.
- `must_not_contain` / `forbidden_terms`: text that must be absent.
- Other simple key/value pairs: compared directly against observed or derived fields.

If `expected_json` is empty, the replay verdict is `needs_review`.

## Metrics

The script reports:

- `case_count`
- `passed`
- `failed`
- `needs_review`
- `pass_rate`

The API endpoint `GET /research/agent/metrics` additionally summarizes replay verdict distribution alongside agent-run and tool-call metrics.

These are engineering regression metrics. They do not certify scientific SOTA, model quality, or benchmark superiority.

## Safety Rules

- Do not store raw API keys, cookies, private keys, `.env` values, or private paper text in replay cases.
- Keep replay fixtures small and non-sensitive.
- Prefer ids, counts, summaries, and redacted snippets over full documents.
- Use `--fail-on-regression` in checks only when the fixture has deterministic expectations.

## Next Steps

- Add replay case creators for context-search misses, missing citations, and SOTA-readiness false positives.
- Add live replay executors after bounded Advisor tool selection exists.
- Add aggregate replay metrics to the local observability report.
