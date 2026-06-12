# Database Migration Strategy

This document defines the migration approach for Research Assistant Agent before introducing migration tooling or changing production data.

## Current State

The application uses SQLAlchemy models in `backend/research/models.py` and initializes tables with `Base.metadata.create_all()` from `backend/research/db.py`. The default development database is SQLite at `./data/research/research_assistant.db`; the compose pilot path uses `/app/data/research/research_assistant.db`.

This approach is acceptable for early development because it can create missing tables without a migration step. It is not enough for customer-pilot upgrades once existing rows must be preserved across schema changes.

## First-Pilot Policy

Until migration tooling is added, production-facing schema changes should follow these rules:

- Prefer additive model changes that are backward-compatible with existing SQLite rows.
- Avoid renaming or deleting columns, tables, indexes, or JSON keys that existing services read.
- Back up `/app/data` before any deployment that changes SQLAlchemy models or database-related settings.
- Record the deployed commit and verification commands in `docs/progress_log.md` or release notes.
- Keep `init_db()` as table creation only; do not hide data migrations inside application startup.
- Do not run ad hoc SQL against the customer-pilot database without an operator-reviewed backup and rollback note.

## Migration Tooling Direction

Recommended future path: Alembic, introduced in a separate implementation slice after operator approval.

Expected shape:

- Add Alembic as a development dependency only when dependency sync is intentionally approved.
- Create `migrations/` with versioned migration files reviewed like application code.
- Configure Alembic to read `RESEARCH_DB_URL` and import `backend.research.models` metadata.
- Keep migration commands explicit, never implicit on FastAPI startup.
- Add a dry-run or current-head check to deployment verification before applying migrations.
- Document rollback expectations per migration. SQLite rollbacks may require restore-from-backup rather than reversible DDL.

## Pre-Migration Checklist

Before applying any migration to a pilot database:

- [ ] Confirm remote git state and deployed commit.
- [ ] Confirm the exact `RESEARCH_DB_URL` and data volume path.
- [ ] Create a cold backup using `docs/deployment.md` backup notes.
- [ ] Run migration checks against a restored copy or staging database when available.
- [ ] Review generated SQL or migration operations for destructive steps.
- [ ] Stop the service or enter a maintenance window if SQLite writes may occur.
- [ ] Apply the migration with operator approval.
- [ ] Verify `/health/ready`, authenticated `/research/status`, Workbench Pilot Launch, and representative read/write routes.
- [ ] Record migration id, deployed commit, backup id, verification results, and rollback note.

## SQLite Constraints

SQLite is suitable for the first internal pilot, but it affects migration design:

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
- Documentation for `alembic current`, `alembic history`, and `alembic upgrade head` in the remote-first runbook.
- Deployment docs that require backup before `upgrade head` on pilot data.
- No automatic migration execution during normal app startup.

## Open Questions

- When should the project switch from SQLite to Postgres for multi-user or higher-concurrency pilots?
- Should write-operation audit remain JSONL-only, move into a database table, or use both?
- Which migration verification command should be required in CI once Alembic is added?
- Who is the operator responsible for approving destructive or irreversible migrations?
