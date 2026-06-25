# Admin Authorization Policy

This document defines the local authorization boundary for operator-only features. It is intentionally conservative because the current service has optional API-key protection but does not yet have user accounts, roles, or sessions.

## Current State

- `/research/*` can be protected with `API_KEY_AUTH_ENABLED=true` and a local deployment API key.
- The local API key proves that a caller is allowed to use the local API; it does not prove that the caller is an administrator.
- Workbench, scripts, and the MCP HTTP bridge may all use the same API key during a personal local deployment.
- Write-operation audit JSONL records may include sanitized metadata and short API-key fingerprint prefixes, never key values or payload text.

## Policy

Until a stronger identity model exists, the regular local API key is not admin authorization by itself. Operator-only features must require a separate admin gate.

Admin-only features include:

- Reading write-operation audit events or aggregate audit summaries.
- Exporting audit records outside the server data directory.
- Viewing API-key fingerprints across multiple clients.
- Managing retention, rotation, cleanup, or restore operations.
- Running database migrations or data repair commands.

## Future Admin Gate

Before adding an audit summary or export endpoint, the implementation should require all of the following:

- An explicit feature flag such as `AUDIT_ADMIN_EXPORT_ENABLED=true`, disabled by default.
- A separate admin credential or upstream reverse-proxy identity, not the normal local API key alone.
- Server-side checks that reject unauthenticated requests and reject ordinary API-key callers.
- No admin credential in query parameters, logs, Workbench local storage, project bundles, or handoff files.
- A non-secret admin actor label for audit correlation, such as a reverse-proxy username or configured operator label.
- Tests proving that unauthorized requests fail and that exported data contains no secrets or raw request bodies.

A first implementation may prefer a separate header such as `X-Research-Assistant-Admin-Key` only if the key value stays in operator-managed secret storage and never appears in documentation examples with real values. If the deployment already has an authenticated reverse proxy, prefer forwarding a verified operator identity instead of adding another shared secret.

## Implemented Summary Gate

The current implementation registers `GET /research/admin/write-audit/summary` only when `AUDIT_ADMIN_EXPORT_ENABLED=true`. The endpoint returns sanitized aggregate counts from `write-operations.jsonl`; it does not return raw events, actor labels, API-key fingerprints, request bodies, uploaded content, prompts, model responses, or credentials. Requests must include the separate admin key header configured by `AUDIT_ADMIN_KEY_HEADER_NAME`. If `/research/*` API-key protection is enabled, callers also need the normal local API key to pass the outer API guard.

Raw JSONL export is implemented only as a default-off, bounded admin endpoint at `GET /research/admin/write-audit/export`; retention and operator workflow expectations are documented in `docs/write_audit_retention_policy.md`.

## Audit Summary Rules

Audit summaries should expose aggregates before raw events:

- Counts by time window, operation, entity type, status, route template, and actor type.
- Recent request ids and sanitized failure categories only when useful for support.
- API-key fingerprint prefixes only when needed for correlation, never full hashes or key values.
- No request bodies, uploaded content, prompt text, model responses, `.env` values, cookies, private keys, provider credentials, or database connection strings.

Raw JSONL export should remain operator-only and disabled by default. If implemented, it should support bounded time windows and clear retention expectations.

## Workbench And MCP

- Workbench must not display audit summaries by default just because a browser has the local API key saved.
- MCP bridge must not expose audit export tools in read-only or generic allowlist setups unless the operator explicitly allows them and admin auth is active.
- Any future audit UI should show a clear operator mode state without revealing credentials.

## Acceptance Criteria For Future Code

- Default config exposes no audit summary/export route.
- Normal API key callers cannot read audit summaries or exports.
- Admin-gated calls require the explicit feature flag and admin identity check.
- Tests cover disabled, missing admin credential, wrong admin credential, normal API key only, and successful admin cases.
- Tests assert exported audit data never includes API keys, cookies, private keys, `.env` values, request bodies, uploaded file content, or provider credentials.
