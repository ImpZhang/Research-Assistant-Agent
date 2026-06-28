# Migration Baseline

This directory is an Alembic-style migration staging area for the local Research Assistant Agent.

The project does not yet run Alembic or automatic migrations. The committed baseline manifest records the current SQLAlchemy metadata fingerprint so future schema changes can detect drift before a real migration tool is introduced.

Use:

```bash
.venv/bin/python scripts/check_migration_baseline.py --json
```

This check imports the SQLAlchemy models and compares the current metadata fingerprint with `migrations/baseline_schema.json`. It does not connect to the local database, read `.env` secrets, run migrations, or modify data.
