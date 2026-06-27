---
name: literature-to-ideas
description: Run the core local research workflow from an ingested paper to evidence, gaps, ideas, novelty checks, reviews, experiment plans, and dossier artifacts. Use when an agent needs to transform literature into traceable research directions or verify the main workflow path.
---

# Literature To Ideas

## Purpose

Drive the main product workflow from a paper id to research artifacts that can be reviewed, searched, bundled, and turned into execution tasks.

## Backing APIs And Tools

- `POST /research/workflows/literature-to-ideas`
- `POST /research/workflows/literature-to-ideas/async`
- `GET /research/jobs/{job_id}`
- `GET /research/jobs/{job_id}/artifacts`
- Tool manifest names: `run_literature_to_ideas_workflow`, `queue_literature_to_ideas_workflow`

## Workflow

1. Start from an already ingested `paper_id`; use `paper-ingestion` first if only a file path is available.
2. Run the synchronous workflow for smoke checks and small local demos.
3. Use the async job endpoint for longer runs or frontend-driven execution.
4. Inspect job status, output ids, and hydrated artifacts before presenting results.
5. Treat generated ideas as candidates; route them through context search, novelty screening, SOTA review, and benchmark readiness before strong claims.

## Safety Boundaries

- Do not call this a multi-agent runtime; it is service-layer orchestration with job trace.
- Do not claim novelty, publishability, or SOTA from generated ideas without review evidence.
- Keep generated outputs inside the project root.

## Failure Handling

- If a job fails, inspect `GET /research/jobs/{job_id}` and `GET /research/jobs/{job_id}/artifacts` before rerunning.
- Use cancel/retry controls only for explicit job-management tasks.
- Preserve partial artifacts when they are useful for replay or debugging.

## Verification

- Run `bash scripts/check_workflow_job_controls.sh` after changing job trace, async workflow, agent trace, or cancel/retry controls.
- Run `bash scripts/check_research_workflow_primitives.sh` after changing card, gap, idea, novelty, review, or experiment-plan generation.
