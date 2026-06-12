# Durable Workflow Queue Design

This document records the migration plan for long-running research workflows. It is design-only: it does not add dependencies, workers, migrations, Redis, Celery, RQ, Dramatiq, Temporal, deployment services, or runtime behavior.

## Current State

The current async literature-to-ideas path is intentionally simple:

- `POST /research/workflows/literature-to-ideas/async` creates a `jobs` row with `status=pending`.
- FastAPI `BackgroundTasks` calls `run_literature_to_ideas_job_background(job.id)` inside the API process.
- `WorkflowService.run_literature_to_ideas_job` reloads the job, marks it `running`, updates progress/output JSON after workflow stages, and marks it `completed`, `failed`, or `canceled`.
- Clients poll `GET /research/jobs/{job_id}` and hydrate artifacts through `GET /research/jobs/{job_id}/artifacts`.
- Retry creates a new `pending` job and currently reuses the same in-process background execution path.

This is acceptable for the first pilot because it avoids a second process and extra infrastructure. It is not a durable queue.

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
- No independent worker process.
- No durable lease or heartbeat.
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

Do not migrate immediately. Keep the current in-process path until one of these triggers is true:

- Multiple pilot users run long workflows concurrently.
- Operators need jobs to survive API restarts without manual reruns.
- Retry/backoff policy becomes required for external API failures.
- Queue wait time and worker health must be visible in readiness checks.
- A deployment owner confirms Redis or an equivalent queue backend is acceptable.

When a trigger is met, prefer one of two first migrations:

- DB-backed worker lease if the deployment must avoid Redis and the workload stays small.
- RQ/Redis if the operator accepts a Redis service and wants a standard Python queue quickly.

Celery, Dramatiq, and Temporal should remain later options.

## API Compatibility Requirements

Any queue migration must preserve these user-facing contracts:

- `POST /research/workflows/literature-to-ideas/async` returns a `JobRead` immediately.
- `GET /research/jobs/{job_id}` remains the polling endpoint for Workbench, scripts, and MCP clients.
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

Future durable execution likely needs migration-backed fields like:

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

A future worker process should:

- Claim only jobs with supported `job_type` values.
- Use database transactions or queue acknowledgement semantics to avoid duplicate execution.
- Record heartbeat updates during long workflow stages.
- Check cancellation before and after each stage.
- Treat `Job.output_json` as append-only stage progress until final completion.
- Never store raw secrets, prompts with secret values, request bodies, or API keys in job metadata.
- Log request/job ids, not sensitive payloads.

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
