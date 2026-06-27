---
name: advisor-action-session
description: Turn a natural-language project question into a traced Advisor answer, follow-up tasks, task-board snapshot, and Markdown action report. Use when an agent needs a local execution session over project cockpit state, retrieved context, and task generation while preserving traceability.
---

# Advisor Action Session

## Purpose

Use the Advisor as a local project operator surface: answer one grounded question, generate follow-up work, snapshot the resulting task board, and preserve trace ids for audit/replay.

## Backing APIs And Tools

- `POST /research/advisor/chat`
- `POST /research/advisor/chat/tasks`
- `POST /research/advisor/action-session`
- `GET /research/agent/runs/{run_id}`
- `GET /research/agent/runs/{run_id}/tool-calls`
- Tool manifest names: `ask_project_advisor`, `create_tasks_from_project_advisor_chat`, `run_project_advisor_action_session`, `get_agent_run`, `list_agent_run_tool_calls`

## Workflow

1. Ask a concrete project question and pass `idea_id` or `paper_ids` when scope is known.
2. Keep `include_cockpit` and `include_context` enabled for grounded answers.
3. Inspect `agent_run_id` and tool-call records when debugging why the Advisor cited or recommended something.
4. Use `/advisor/chat/tasks` when the user only wants follow-up tasks.
5. Use `/advisor/action-session` when the user wants answer, tasks, snapshot, progress summary, and Markdown report in one operation.

## Safety Boundaries

- Current Advisor behavior uses a bounded read-first tool plan plus trace logging, not open-ended autonomous tool execution.
- Treat task creation as a side effect; use it only when the user wants work added to the task board.
- Do not hide weak evidence; surface cited gaps, risks, and missing actions.

## Failure Handling

- If tool calls fail, preserve the failed `AgentRun` and error metadata for replay.
- If context is empty, answer from cockpit state only and recommend a retrieval/evidence follow-up.
- If task creation is not desired, return the chat answer and recommended actions without calling task endpoints.

## Verification

- Run `bash scripts/check_workflow_job_controls.sh` after changing Advisor trace, job trace, or agent-run behavior.
- Run `bash scripts/check_research_planning_contracts.sh` after changing advisor briefs, planning, ranking, or action-session semantics.
