# Durable Workflow Queue Design

This document records the current local queue contract and the migration plan for long-running research workflows. The default API server still uses the lightweight in-process background path, while personal local deployments can opt into a separate SQLite worker by setting `WORKFLOW_BACKGROUND_TASKS_ENABLED=false` and running `scripts/run_workflow_worker.py`. This document still does not introduce Redis, Celery, RQ, Dramatiq, Temporal, deployment services, or migration-backed queue columns.

## Current State

The current async literature-to-ideas path is intentionally simple:

- `POST /research/workflows/literature-to-ideas/async` creates a `jobs` row with `status=pending`.
- FastAPI `BackgroundTasks` calls `run_literature_to_ideas_job_background(job.id)` inside the API process.
- `WORKFLOW_BACKGROUND_TASKS_ENABLED=false` disables that in-process background call and leaves the job as `pending` for a local worker.
- `scripts/run_workflow_worker.py` claims pending `literature_to_ideas_workflow` jobs from SQLite, marks them `running`, writes lease metadata under `Job.output_json.lease`, and then runs the same `WorkflowService.run_literature_to_ideas_job` path.
- `WorkflowService.run_literature_to_ideas_job` reloads the job, marks it `running`, updates progress/output JSON after workflow stages, and marks it `completed`, `failed`, or `canceled`.
- `WorkflowService` refreshes lease heartbeat metadata during stage updates when a worker lease exists.
- `JobRead` exposes `stage` and `stage_message` derived from `Job.output_json` so clients can display current workflow phase without parsing every artifact id.
- Clients poll `GET /research/jobs/{job_id}` and hydrate artifacts through `GET /research/jobs/{job_id}/artifacts`.
- Retry creates a new `pending` job and uses either the in-process background path or the external local worker path, depending on `WORKFLOW_BACKGROUND_TASKS_ENABLED`.
- `scripts/evaluate_real_papers.py` defaults to `--workflow-mode async-poll`, which queues a local `jobs` row through `WorkflowService`, starts a short-lived worker process, polls `GET /research/jobs/{job_id}`, saves poll history in the report, and hydrates artifacts through `GET /research/jobs/{job_id}/artifacts`.
- The real-paper evaluator can terminate its own timed-out worker process and recover partial artifacts from the job row. This is an evaluation-runner safety mechanism, not a durable server queue.

This is acceptable for the first local pilot because it avoids extra infrastructure and still gives operators a separate worker command for long jobs. It is not a full durable queue because stale-lease reclaim, retry backoff, and resumable stage checkpoints are still deliberately deferred.

## Problem

FastAPI `BackgroundTasks` is tied to the API worker process. It does not provide durable scheduling or recovery if the process restarts after a job is accepted. It also does not provide a worker queue, lease ownership, heartbeat visibility, retry backoff, or multi-worker concurrency control.

The project needs a documented path before changing runtime behavior because queue implementation touches deployment topology, database migrations, readiness checks, logs, and operator runbooks.

## Non-Goals For The Current Round

- Do not add Redis, RQ, Celery, Dramatiq, Temporal, or worker dependencies yet.
- Do not change `docker-compose.yml` or production process management yet.
- Do not add schema columns until migration tooling and backup policy are approved.
- Do not change the current API response shapes.
- Do not run service restarts, migrations, queue workers, or dependency installs from this design step.

## Queue Options

### FastAPI BackgroundTasks plus Jobs Table

Best for:

- Single-user or small internal pilot.
- Short to medium jobs where losing an in-flight background task can be handled manually.
- Keeping deployment simple.

Limits:

- No recovery after API process restart.
- Independent worker process only when `WORKFLOW_BACKGROUND_TASKS_ENABLED=false`.
- Lease and heartbeat metadata are stored in `Job.output_json`, not migration-backed columns.
- Hard to scale beyond one API process safely.

### DB-Backed Worker Lease

Best for:

- A minimal next step that keeps dependencies small.
- SQLite or PostgreSQL deployments that prefer not to add Redis yet.
- Explicit job leasing with a separate worker command.

Limits:

- Requires schema migration for lease fields.
- SQLite concurrency must be tested carefully.
- Backoff and scheduling logic must be implemented by the project.

### RQ With Redis

Best for:

- Simple Python job queues.
- Clear separation between API and worker process.
- Basic retries and operational visibility with low complexity.

Limits:

- Adds Redis to deployment.
- Requires operator policy for Redis persistence and backup scope.
- Workflow progress still lives in the project database, so Redis should not become the only source of job truth.

### Celery Or Dramatiq

Best for:

- Larger deployments with multiple task types, routing, scheduled jobs, and mature worker management.

Limits:

- More configuration and operational complexity than the project needs for the first pilot.
- Requires stronger deployment/runbook coverage.

### Temporal

Best for:

- Resumable workflow state, long-running DAGs, and rich visibility.

Limits:

- Too heavy until workflow durability becomes the product center.

## Recommended Direction

Do not migrate the API server to Redis/Celery immediately. Keep the current in-process path plus the optional SQLite worker until one of these triggers is true:

- Multiple pilot users run long workflows concurrently.
- Operators need jobs to survive API restarts without manual reruns.
- Retry/backoff policy becomes required for external API failures.
- Queue wait time and worker health must be visible in readiness checks.
- A deployment owner confirms Redis or an equivalent queue backend is acceptable.

When a trigger is met, prefer one of two first migrations:

- Migration-backed DB worker lease if the deployment must avoid Redis and the workload stays small.
- RQ/Redis if the operator accepts a Redis service and wants a standard Python queue quickly.

Celery, Dramatiq, and Temporal should remain later options.

## API Compatibility Requirements

Any queue migration must preserve these user-facing contracts:

- `POST /research/workflows/literature-to-ideas/async` returns a `JobRead` immediately.
- `GET /research/jobs/{job_id}` remains the polling endpoint for Workbench, scripts, and MCP clients.
- `JobRead.stage` and `JobRead.stage_message` remain backward-compatible optional strings for stage display.
- `GET /research/jobs/{job_id}/artifacts` remains the hydration endpoint for workflow outputs.
- `POST /research/jobs/{job_id}/cancel` continues to work for pending and running jobs.
- `POST /research/jobs/{job_id}/retry` creates a new job linked to the source job.
- `Job.output_json` remains the durable artifact manifest for paper, card, gap, idea, novelty, review, experiment plan, and Markdown export ids.

## Future Job State Model

The current table has:

- `id`
- `job_type`
- `status`
- `input_json`
- `output_json`
- `error`
- `progress`
- `started_at`
- `finished_at`

The current worker stores lease metadata in `Job.output_json.lease` to avoid a migration. Future durable execution likely needs migration-backed fields like:

- `queued_at`
- `lease_owner`
- `leased_at`
- `lease_expires_at`
- `heartbeat_at`
- `attempts`
- `max_attempts`
- `next_run_at`
- `last_error_type`
- `cancel_requested_at`
- `idempotency_key`
- `priority`

These fields must not be added until the migration path and backup/restore workflow are approved.

## State Transitions

Target state transitions should stay explicit:

```text
pending -> leased -> running -> completed
pending -> leased -> running -> failed
pending -> canceled
leased -> canceled
running -> cancel_requested -> canceled
failed -> retry_created -> pending(new job)
running -> failed -> pending(new retry job)
```

The public `status` values can remain compatible by either exposing `leased` as `pending` during the first migration or by adding a documented `leased` status after clients are prepared.

## Worker Contract

The current local worker:

- Claim only jobs with supported `job_type` values.
- Uses a conditional SQLite update from `pending` to `running` to avoid duplicate claims in the common local case.
- Records heartbeat updates during workflow stages through `Job.output_json.lease.heartbeat_at`.
- Check cancellation before and after each stage.
- Treat `Job.output_json` as append-only stage progress until final completion.
- Never store raw secrets, prompts with secret values, request bodies, or API keys in job metadata.
- Log request/job ids, not sensitive payloads.

Future migration-backed workers should add explicit stale-lease reclaim, retry backoff, and idempotency checks before supporting multi-worker concurrency.

## Deployment And Operations

Before implementation, the operator must confirm:

- Queue backend choice.
- Worker process supervisor: compose service, systemd unit, or another runner.
- Redis persistence policy if Redis is used.
- Database backup and restore procedure for job state.
- Log location and rotation policy.
- Health/readiness semantics for queue and workers.
- How to stop workers gracefully during deployment.

Commands that start workers, run migrations, add services, or restart deployments require explicit human confirmation.

## Testing Requirements

The first implementation should include tests for:

- Queueing returns `pending` immediately.
- Worker claims a job and marks it `running`.
- Progress and artifact ids are persisted after each workflow stage.
- Failed jobs keep sanitized errors and can be retried.
- Canceled jobs stop before the next stage.
- Duplicate worker claims do not produce duplicate artifacts.
- Readiness reports queue/worker state without blocking unrelated checks unless configured.
- Existing smoke workflow and Workbench job polling remain compatible.

## Acceptance Criteria

A durable queue migration is ready for pilot use only when:

- The API still passes the existing workflow and smoke tests.
- A worker can be started and stopped through documented operator commands.
- Jobs accepted before API restart are either executed by a worker or visibly recoverable.
- Retry and cancellation behavior is covered by tests.
- Readiness/logging gives operators enough information to diagnose stuck jobs.
- Documentation names all state-changing commands that require human confirmation.

## Open Questions

- Should the first durable step be DB-backed leasing or RQ/Redis?
- Is Redis acceptable in the first pilot deployment?
- Should queue worker health block `/health/ready` or appear as a warning while the feature is disabled?
- What is the desired maximum runtime for a literature-to-ideas job?
- Should workflow stages become resumable checkpoints or remain full-job retries for the next phase?
