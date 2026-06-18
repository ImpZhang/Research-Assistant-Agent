# Write Operation Audit Design

This document defines the intended audit trail for state-changing operations before any persistence or middleware changes are introduced.

## Purpose

The audit trail should answer these operational questions for an internal customer pilot:

- Who or what client triggered a write operation?
- Which API route or MCP tool was used?
- Which domain object was created, updated, canceled, retried, or exported?
- Did the operation succeed or fail?
- Which deployment commit and policy were active when the write happened?

This is separate from research-domain artifacts such as assumption audits, evidence ledgers, task events, and GraphRAG-lite edges. Those explain research reasoning and artifact lineage; write-operation audit explains operational safety and accountability.

## Non-Goals

- Do not store raw request bodies, uploaded paper content, API keys, cookies, private keys, `.env` values, or provider credentials.
- Do not expose audit events to untrusted browser users by default.
- Do not replace task event history, artifact graph edges, or project bundle metadata.
- Do not add a database migration until the project has an agreed migration approach.

## Event Shape

A future `WriteAuditEvent` should capture sanitized metadata only:

- `id`: generated event id.
- `created_at`: server timestamp.
- `request_id`: per-request correlation id.
- `actor_type`: `workbench`, `mcp_bridge`, `script`, `api_client`, or `unknown`.
- `actor_label`: optional non-secret label such as client name or API-key fingerprint prefix.
- `method`: HTTP method.
- `path_template`: FastAPI route template when available, not raw query-heavy URLs.
- `tool_name`: MCP tool name when the write came through the bridge.
- `operation`: create, update, delete, cancel, retry, upload, export, or other write category.
- `entity_type`: paper, task, job, brief, bundle_release, review_outcome, signoff, etc.
- `entity_id`: created or affected id when safe to record.
- `status`: success or failure.
- `http_status`: response status code.
- `error_type`: sanitized exception class or validation category, not stack traces with secrets.
- `policy`: read-only, allowlist, denylist, or direct API mode when known.
- `duration_ms`: server-side latency.
- `commit_sha`: deployed git commit when available.
- `metadata`: small counts, booleans, and schema names; no raw text payloads.

## Capture Points

Recommended rollout order:

1. Add a request correlation id helper for `/research/*` routes.
2. Add a write-audit helper that accepts sanitized event fields and can write JSONL under the data directory.
3. Add FastAPI middleware or route dependency coverage for non-GET `/research/*` requests.
4. Let routes enrich `request.state.audit_context` with entity ids after successful writes.
5. Have the MCP bridge forward a non-secret client label and tool name when calling HTTP routes.
6. Have Workbench include a generated request id or client label without storing secrets.
7. Add an optional read-only admin/export path only after the policy in `docs/admin_authorization_policy.md` is implemented.

## Current Prototype

The first code prototype is disabled by default. Set `WRITE_AUDIT_ENABLED=true` and `WRITE_AUDIT_DIR=/app/data/audit` to append JSONL records for non-GET `/research/*` requests. The middleware records route templates, request ids, client labels, API-key fingerprint prefixes when a key is supplied, policy headers, operation/entity categories, status, HTTP code, duration, commit sha when provided, and query parameter names. It does not read request bodies or serialize payloads, and it never writes API-key values.

## Authorization Dependency

The read-only audit summary endpoint is implemented as `GET /research/admin/write-audit/summary`, and bounded raw JSONL export is implemented as `GET /research/admin/write-audit/export`; both are registered only when `AUDIT_ADMIN_EXPORT_ENABLED=true`. They require the separate admin key header configured by `AUDIT_ADMIN_KEY_HEADER_NAME`; the normal pilot API key is not sufficient admin authorization because Workbench, scripts, and the MCP bridge may share it during customer pilots. Raw export applies the field allowlist and metadata sensitive-key filter before returning JSONL, and it requires bounded query parameters such as `max_records`, `start_created_at`, and `end_created_at`.

## Storage Options

Recommended first implementation:

- Append JSONL to `/app/data/audit/write-operations.jsonl`.
- Rotate by size or date in a later hardening pass following `docs/write_audit_retention_policy.md`.
- Keep the file out of git and out of public project bundles.

Later implementation after migrations are settled:

- Add a database table for indexed search by timestamp, actor, operation, entity, status, and request id.
- Keep JSONL as a deployment fallback or disable it when DB audit is stable.

## Redaction Rules

- Store API-key fingerprints only, never key values.
- Store upload filenames only when already visible in the app; never store file bytes.
- Store request body hashes or schema names instead of body content.
- Store exception categories instead of full tracebacks.
- Treat provider prompts, model responses, cookies, and `.env` values as non-audit payloads.

## Minimal Acceptance Criteria

The first implementation should pass these checks:

- Creating a task writes one audit event with method, route, operation, entity id, status, and request id.
- Updating a task writes one audit event and does not duplicate task-domain events.
- Uploading a paper records an upload operation without storing file content.
- Canceling or retrying a job records the job id and operation.
- MCP bridge writes include tool name and read-only/allowlist policy when applicable.
- Failed validation records status and HTTP code without raw payloads.
- Tests assert that API keys and `.env` values are never serialized into audit records.

## Open Questions

- Should audit summaries enter project handoff bundles, or remain operator-only?
- Workbench can display the response request id after failed writes; the backend now returns the configured request-id header on all responses and the write audit reuses the same id.
- Should API-key fingerprints be derived in app config or inside auth middleware?
