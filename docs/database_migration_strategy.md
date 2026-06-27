# Database Migration Strategy

This document defines the migration approach for Research Assistant Agent before introducing migration tooling or changing existing local deployment data.

## Current State

The application uses SQLAlchemy models in `backend/research/models.py` and initializes tables with `Base.metadata.create_all()` from `backend/research/db.py`. The default local database is SQLite at `./data/research/research_assistant.db`; the optional compose path uses `/app/data/research/research_assistant.db`.

This approach is acceptable for early development because it can create missing tables without a migration step. It is not enough for local upgrade paths once existing rows must be preserved across schema changes.

## Local Upgrade Policy

Until migration tooling is added, schema changes that affect existing local data should follow these rules:

- Prefer additive model changes that are backward-compatible with existing SQLite rows.
- Avoid renaming or deleting columns, tables, indexes, or JSON keys that existing services read.
- Back up `/app/data` before any deployment that changes SQLAlchemy models or database-related settings.
- Record the deployed commit and verification commands in `docs/progress_log.md` or release notes.
- Keep `init_db()` as table creation only; do not hide data migrations inside application startup.
- Do not run ad hoc SQL against a user's local database without an operator-reviewed backup and rollback note.

## Migration Tooling Direction

Recommended future path: Alembic, introduced in a separate implementation slice after operator approval.

Expected shape:

- Add Alembic as a development dependency only when dependency sync is intentionally approved.
- Create `migrations/` with versioned migration files reviewed like application code.
- Configure Alembic to read `RESEARCH_DB_URL` and import `backend.research.models` metadata.
- Keep migration commands explicit, never implicit on FastAPI startup.
- Add a dry-run or current-head check to deployment verification before applying migrations.
- Document rollback expectations per migration. SQLite rollbacks may require restore-from-backup rather than reversible DDL.

## Project Scoping Migration Candidate

User/project scoping should follow `docs/user_project_scoping_design.md`: create default user/project rows, backfill project-scoped tables, add `project_id` indexes, then enforce route-level isolation before tightening nullability. This should happen only after migration tooling and auth identity are explicit.

## Recent Additive Tables

The agent trace foundation adds `agent_runs`, `tool_call_records`, and `replay_cases` as additive tables. Fresh local checkouts receive these tables through `Base.metadata.create_all()`. Existing local databases need operator-aware upgrade handling until Alembic is introduced: back up the local data directory, start the app so missing tables are created, then verify `/health/ready` and `/research/agent/runs`.

## Pre-Migration Checklist

Before applying any migration to an existing local database:

- [ ] Confirm local git state and deployed commit.
- [ ] Confirm the exact `RESEARCH_DB_URL` and data volume path.
- [ ] Create a cold backup using `docs/deployment.md` backup notes.
- [ ] Run migration checks against a restored copy or staging database when available.
- [ ] Review generated SQL or migration operations for destructive steps.
- [ ] Stop the service or enter a maintenance window if SQLite writes may occur.
- [ ] Apply the migration with operator approval.
- [ ] Verify `/health/ready`, authenticated `/research/status`, the Workbench launch panel, and representative read/write routes.
- [ ] Record migration id, deployed commit, backup id, verification results, and rollback note.

## SQLite Constraints

SQLite is suitable for the personal local-agent target, but it affects migration design:

- Many schema changes require table rebuilds rather than simple `ALTER TABLE` operations.
- Concurrent writes should be avoided during migrations.
- Restore-from-backup is often the safest rollback path.
- Large uploaded files should remain in `/app/data/papers`, not inside database rows.
- JSON columns make additive metadata changes easier, but schema expectations still need tests.

## Acceptance Criteria For Introducing Alembic

A future migration-tooling implementation should include:

- Alembic configuration committed without secrets.
- A baseline migration matching current SQLAlchemy models.
- Tests or checks that detect metadata drift between models and migrations.
- Documentation for `alembic current`, `alembic history`, and `alembic upgrade head` in the local runbook.
- Deployment docs that require backup before `upgrade head` on existing local data.
- No automatic migration execution during normal app startup.

## Open Questions

- When would SQLite stop being enough for personal local-agent usage?
- Should write-operation audit remain JSONL-only, move into a database table, or use both?
- Which migration verification command should be required in CI once Alembic is added?
- Who is the operator responsible for approving destructive or irreversible migrations?
