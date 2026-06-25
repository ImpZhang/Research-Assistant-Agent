# Development Process

This is the standard workflow for future Research Assistant Agent development.

## 1. Orient

Before changing files:

```bash
git status --short
git branch --show-current
git --no-pager log --oneline -5
```

Then read:

- `AGENTS.md`
- `docs/documentation_index.md`
- The design, operations, or evaluation document that matches the task

If the task touches local runtime behavior, source the local environment:

```bash
source scripts/env.sh
```

Do not read real `.env` values, private keys, cookies, or credential caches.

## 2. Classify The Change

Use the smallest accurate category:

| Category | Examples | Required Docs |
| --- | --- | --- |
| Documentation-only | Runbooks, process docs, design notes | The changed doc plus `docs/progress_log.md` if nontrivial |
| Backend behavior | Routes, schemas, services, adapters | `README.md`, requirements/design docs, focused tests |
| Workflow/product loop | Literature-to-ideas, tasks, cockpit, bundles | Requirements/design docs, progress log, smoke or focused suites |
| Runtime/deployment | Env vars, health checks, Docker, local scripts | `docs/deployment.md`, `docs/local_isolation.md`, preflight checks |
| Data/schema | SQLAlchemy models, stored artifacts, migrations | `docs/database_migration_strategy.md`, migration notes |
| Audit/security | API keys, admin gate, audit logs, sensitive export | audit/admin policy docs and redaction tests |
| Evaluation/SOTA | Product-effect, representative papers, benchmark boundaries | matching evaluation docs and manual-review notes |

## 3. Edit In Small Rounds

- Prefer small, reviewable changes.
- Keep unrelated refactors out of the round.
- Preserve existing public API shapes unless the task explicitly changes them.
- Keep all local dependencies, caches, generated outputs, models, logs, and data under the project root.
- Add comments only where they clarify non-obvious logic.

## 4. Verification Ladder

Choose the lowest sufficient verification first, then broaden when risk increases.

### Documentation-only

```bash
git diff --check
bash -n scripts/*.sh
```

### Local setup or scripts

```bash
source scripts/env.sh
bash -n scripts/env.sh scripts/setup-local.sh scripts/run-local.sh scripts/clean.sh scripts/deep-clean.sh scripts/docker-clean.sh
bash scripts/check_pilot_operational_preflight.sh
```

### Backend route or service changes

```bash
source scripts/env.sh
ruff check <changed-python-files>
ruff format --check <changed-python-files>
pytest -q <focused-tests>
```

### Workflow/product changes

Run the relevant focused script from `scripts/check_*.sh`. Common choices:

```bash
bash scripts/check_research_workflow_primitives.sh
bash scripts/check_research_proposal_contracts.sh
bash scripts/check_project_delivery_loop.sh
bash scripts/check_tool_bridge_contracts.sh
bash scripts/check_graph_rag_lite.sh
bash scripts/check_context_search_evaluations.sh
```

### Broad local preflight

```bash
bash scripts/check_remote_safe_suite.sh
```

`check_remote_safe_suite.sh` is a historical script name. In the current local-only workflow, treat it as a local focused suite; it should not imply SSH or remote-server work.

The full `pytest -q` suite can write persistent local test data and has at least one stateful assertion that is not a good standalone local deployment gate. Prefer the focused scripts and the local focused suite unless the task specifically requires full pytest investigation.

## 5. Local Runtime Check

For manual local verification:

```bash
./scripts/run-local.sh
```

Then open:

```text
http://127.0.0.1:8000/workbench
```

Check:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/health/ready
```

Keep the server in the foreground unless the operator explicitly asks for a persistent background process.

## 6. Cleanup

After tests that write local data:

```bash
rm -rf data/research data/papers data/audit .pytest_cache .ruff_cache
mkdir -p data models outputs logs .docker
```

For a full rebuildable-artifact cleanup:

```bash
./scripts/clean.sh
```

For data/model removal, use the confirmation-gated command:

```bash
./scripts/deep-clean.sh
```

Do not delete source, docs, lockfiles, user-authored notebooks, or real data unless the operator explicitly approves it.

## 7. Handoff And Commit

Before ending a development round:

```bash
git status --short
git diff --check
```

Record:

- What changed
- What was verified
- What was not verified
- Any remaining risk

For nontrivial work, add a dated entry to `docs/progress_log.md`.

Commit only after successful verification and operator approval when the change should be pushed upstream.
