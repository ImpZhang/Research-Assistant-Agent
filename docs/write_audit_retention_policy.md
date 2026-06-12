# Write Audit Retention Policy

This document defines the first-pilot retention and operator workflow for write-operation audit records. It exists before raw audit export code so export behavior has an explicit safety contract.

## Scope

- Current audit storage: `/app/data/audit/write-operations.jsonl` or `WRITE_AUDIT_DIR/write-operations.jsonl`.
- Current public surface: no unauthenticated or normal-user raw audit export endpoint.
- Current operator surface: default-off admin summary at `GET /research/admin/write-audit/summary` and bounded raw JSONL export at `GET /research/admin/write-audit/export`.
- Audit records are sanitized metadata only; they must never include request bodies, uploaded paper content, API keys, cookies, private keys, `.env` values, provider credentials, prompts, model responses, or database connection strings.

## First-Pilot Retention Target

Use conservative local retention until the deployment target and compliance expectations are fixed:

- Keep the active JSONL file on the service data volume, outside git and outside public handoff bundles.
- Review audit volume growth weekly during the pilot.
- Rotate by date or size before the active JSONL file becomes operationally large; a future code/script slice should make the threshold explicit.
- Prefer retaining 30 days of audit metadata for first-pilot support unless the operator sets a stricter customer policy.
- Keep long-term audit archives only in operator-managed storage with the same secret-handling rules as production backups.

This policy does not require deleting existing audit data automatically. Automated cleanup should wait for an approved backup/restore and retention workflow.

## Operator Export Workflow

Raw JSONL export is implemented as a bounded, default-off admin endpoint. Operator use should still require:

- Explicit operator approval for the export purpose, time window, destination, and recipient.
- `AUDIT_ADMIN_EXPORT_ENABLED=true` and a separate admin authorization gate as defined in `docs/admin_authorization_policy.md`.
- A bounded time window or `max_records` limit; no unbounded full-file downloads by default.
- Export into an operator-only directory, not into the repo, project bundle, Workbench local storage, or public handoff package.
- A sanitized summary review before raw JSONL leaves the server.
- A progress-log or release-note entry containing the exported time window and destination class, not the exported contents.

Do not put raw audit exports in git, issue trackers, chat transcripts, model prompts, or customer-visible artifacts unless a separate operator-approved redaction pass has completed.

## Future Implementation Gates

The implemented endpoint and any future raw export script should satisfy these checks:

- Disabled by default behind an explicit feature flag.
- Requires admin auth in addition to any normal pilot API key guard.
- Supports bounded start/end time filters or a maximum record count.
- Streams or writes JSONL without loading an unbounded file into memory.
- Refuses export when the target path is inside the repository or another known public artifact directory.
- Includes tests for disabled, unauthorized, bounded export, invalid bounds, and secret redaction invariants.
- Keeps aggregate summary endpoints separate from raw export endpoints.

## Rotation And Cleanup Notes

- Rotation should be additive first: write a new file and preserve old files until backup has been confirmed.
- Cleanup should never run against a live service volume without a backup or explicit operator approval.
- If database-backed audit storage is introduced later, keep JSONL retention behavior documented as either a fallback or disabled path.
