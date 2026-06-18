# User And Project Scoping Design

This document defines the target user/project scoping model before database schema changes are introduced. The current pilot uses a shared API key and project-level domain objects, so scoping must be designed before migrations or route filters are added.

## Current State

- There is no first-class `users`, `projects`, or `project_memberships` table.
- Many records have `created_by` labels, but these are free-form strings and are not authorization identities.
- Some artifact tables use `scope` values such as `pilot_report`, `bundle_readiness`, or release-specific scopes; these are artifact categories, not project isolation boundaries.
- Task-like records use `owner_type` and `owner_id` for domain linkage, not user ownership.
- API-key auth proves access to the pilot deployment, not membership in a specific project.
- Existing data should be treated as belonging to one implicit default project until an approved migration assigns explicit project ids.

## Goals

- Add a stable project boundary for papers, evidence, ideas, tasks, briefs, workflows, bundles, reviews, and generated artifacts.
- Preserve backward compatibility for existing pilot data by assigning a default project during migration.
- Keep user identity separate from free-form `created_by` labels.
- Let Workbench, scripts, and MCP clients select or forward the active project without exposing secrets.
- Ensure write-operation audit records can include non-secret project context.
- Avoid accidental cross-project reads in list, detail, bundle export, and search endpoints.

## Non-Goals

- Do not implement full enterprise multi-tenancy in the first slice.
- Do not add billing, organizations, SSO, or complex role hierarchies yet.
- Do not infer real user identity from the shared pilot API key alone.
- Do not run automatic migrations at startup.

## Proposed Data Model

Add these tables after migration tooling and operator approval exist:

- `research_users`: internal id, external subject or operator label, display name, email hash or contact label, status, created/updated timestamps.
- `research_projects`: id, slug, name, description, status, created_by_user_id, default profile id, created/updated timestamps.
- `research_project_memberships`: project_id, user_id, role, status, created/updated timestamps.

Add nullable-then-required `project_id` to project-scoped domain tables in a staged migration. Candidate table groups:

- Core literature: `papers`, `paper_sections`, `chunks`, `evidences`, `paper_cards`, `research_gaps`.
- Idea loop: `ideas`, reviews, novelty checks, feedback, decision memos, assumption audits, evidence ledgers, related-work matrices, proposal artifacts, experiment artifacts.
- Delivery and operations: `research_tasks`, task events, task-board snapshots, research briefs, plans, jobs, portfolio snapshots, project triage snapshots, bundle/release artifacts represented in brief or metadata rows.
- GraphRAG-lite: `research_nodes` and `research_edges` should carry project_id or only connect nodes within one project.

Keep `created_by` as a human-readable label for exports, but add separate identity fields such as `created_by_user_id` only after auth identity is explicit.

## Request Scope Contract

A future implementation should resolve request scope in this order:

1. Admin routes may explicitly request cross-project views only when admin authorization is active.
2. Authenticated project clients provide `X-Research-Assistant-Project` or a route/query project id.
3. Workbench stores the selected project id locally and sends it on `/research/*` calls.
4. MCP bridge forwards the active project id as a non-secret header or request argument.
5. If no project is provided during the compatibility phase, use the default project and mark the response as compatibility scoped.

Project ids are not secrets, but they should not grant authorization by themselves.

## API Behavior

- List endpoints must filter by the resolved project unless an admin cross-project mode is explicitly enabled.
- Detail endpoints must return 404 or 403 when a record belongs to another project.
- Create endpoints must attach the resolved project id to all newly created records and derived artifacts.
- Bundle exports must include only one project unless an admin export mode explicitly requests more.
- Search and GraphRAG-lite retrieval must not mix nodes, chunks, or evidence across projects.
- Write-audit events should include sanitized project metadata such as `project_id` or `project_slug`, never user secrets.

## Migration Strategy

Follow `docs/database_migration_strategy.md`:

1. Add migration tooling only after operator approval and dependency sync approval.
2. Create default user/project rows.
3. Backfill existing project-scoped tables with the default project id.
4. Add indexes on `project_id` for list/search hot paths.
5. Add route filters and tests while fields are still nullable for compatibility.
6. Tighten nullability only after backfill and compatibility tests pass.

No scoping migration should run implicitly at app startup.

## Workbench And MCP

- Workbench should show a project selector only after project list/detail routes exist.
- The selected project should be stored as a non-secret preference, separate from the API key.
- MCP tools should accept or forward project id in a consistent way, and read-only mode must remain project-scoped.
- Tool manifests should document whether each tool is project-scoped or admin-only.


## Implemented Compatibility Scope Contract

The current pilot exposes `GET /research/project/scope` as a read-only compatibility contract before schema migrations exist. It reports:

- Active project id: `default`.
- Project header name: `X-Research-Assistant-Project`.
- Compatibility mode: `true`.
- Isolation status: `default_project_only`.
- Project ids are not secrets and do not grant authorization by themselves.

If a client sends a non-default project id, the response records it as `requested_project_id` and warns that isolation is not available until project-id migrations and route filters are implemented. The endpoint does not create users or projects, does not migrate data, and does not imply cross-project isolation.

## Acceptance Criteria For Future Code

- Existing data is readable through the default project after migration.
- Creating papers, ideas, tasks, workflows, and bundles attaches project id consistently.
- Listing and detail routes cannot leak records from another project.
- Search, GraphRAG-lite, and bundle exports are project-scoped.
- Write-audit records include sanitized project context for writes.
- Tests cover default-project compatibility, cross-project isolation, Workbench project forwarding, MCP project forwarding, and admin-only cross-project behavior.
