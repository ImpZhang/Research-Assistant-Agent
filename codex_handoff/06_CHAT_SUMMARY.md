# Chat Summary For Mac Codex

This is the highest-context summary of the old conversation. A new Codex should read this before continuing.

## User's Original Request

The user provided access to a remote server and said there was a `super-mew` RAG project in the remote directory. The user felt that only connecting a RAG was too elementary and too toy-like for a real project.

The user wanted to turn it into a genuine research assistant:

- not just answering questions from documents;
- capable of helping think of meaningful research ideas;
- useful enough to become a serious project;
- eventually customer-facing.

The user asked:

- Can you connect to the remote server?
- Look carefully at the remote directory.
- List what you would upgrade.
- Do we need Graph RAG?
- Do we need DeerFlow?
- Do we need MCP later?
- You decide based on the task scenario.
- Then clarify the whole architecture.
- Create Markdown requirement and technical design docs.
- Then create a new root project directory `/home/zhangwz/Research-Assistant-Agent`.
- Push every completed round to GitHub `ImpZhang/Research-Assistant-Agent.git`.
- Continue building without stopping.
- Always compare progress against the planned roadmap.

Security note for Mac Codex:

- The old chat contained remote login details. Do not write passwords into repository files.
- Use GitHub clone or user's secure SSH configuration instead.

## Early Analysis And Direction

The existing `super-mew` idea was treated as insufficient because it was basically RAG-centric.

The upgraded project direction became:

> A research workflow and execution assistant that turns literature evidence into research ideas, then into proposals, experiments, task boards, project state, and handoff artifacts.

The assistant recommended not starting with a huge all-in architecture. Instead:

- keep FastAPI and stable services;
- build deterministic local fallbacks;
- add GraphRAG-lite for lineage and traceability;
- expose a tool manifest early;
- add MCP bridge later/gradually;
- defer DeerFlow and full GraphRAG until needed;
- build toward customer-facing delivery and signoff.

## Documents Created Early

Two core docs were created/maintained:

- `docs/research_assistant_requirements.md`
- `docs/research_assistant_technical_design.md`

They contain:

- product goals;
- user scenarios;
- workflow phases;
- GraphRAG-lite reasoning;
- MCP strategy;
- DeerFlow decision;
- endpoint and artifact design;
- phase roadmap;
- ADR-style decisions.

Mac Codex should treat these docs as the detailed design baseline.

## Architecture Settled

The settled architecture is:

- FastAPI backend;
- SQLAlchemy + SQLite persistence;
- Pydantic schemas;
- service layer for research logic;
- deterministic fallback model behavior;
- optional OpenAI-compatible providers;
- static Workbench UI;
- `ResearchBrief` for many persisted Markdown/JSON handoff artifacts;
- `ResearchTask` for execution follow-up;
- GraphRAG-lite nodes/edges for lineage;
- project bundle zip export as a durable handoff;
- tool manifest and MCP-ready bridge spec as external tool contract.

The codebase should avoid:

- turning into a single chatbot;
- making MCP the core logic layer;
- adding DeerFlow before workflow boundaries stabilize;
- adding full GraphRAG/Neo4j before there is enough scale/use case;
- making tests depend on real LLM credentials.

## Implementation History By Major Theme

### Foundation

The new project was scaffolded under:

```text
/home/zhangwz/Research-Assistant-Agent
```

GitHub repository:

```text
https://github.com/ImpZhang/Research-Assistant-Agent.git
```

The project gained:

- FastAPI app;
- SQLite/SQLAlchemy database;
- `uv`-based Python setup;
- upload and parse paper routes;
- deterministic evidence/gap/idea services;
- Workbench frontend;
- tests and smoke workflow;
- Docker and compose;
- API key guard and health checks.

### Literature-To-Ideas Workflow

The main workflow became:

```text
paper upload
  -> evidence extraction
  -> paper card
  -> research gap mining
  -> idea generation
  -> novelty/collision screening
  -> reviewer simulation
  -> experiment planning
  -> Markdown dossier
  -> GraphRAG-lite context retrieval
```

Main entrypoints:

- `POST /research/workflows/literature-to-ideas`
- `POST /research/workflows/literature-to-ideas/async`
- `GET /research/jobs/{job_id}`
- `GET /research/jobs/{job_id}/artifacts`

### Idea-Level Research Artifacts

The system then grew beyond initial workflow output:

- related-work matrices;
- proposal drafts;
- proposal readiness reviews;
- proposal revisions;
- task backlog from revisions;
- experiment runs;
- experiment analyses;
- analysis follow-up tasks;
- decision memos;
- decision-memo tasks;
- assumption audits;
- evidence ledgers;
- evidence-ledger tasks;
- claim validation packets;
- claim validation queue;
- claim queue tasks;
- claim validation results;
- idea progress summaries;
- idea research packets;
- idea activity timeline;
- idea readiness score;
- idea quality gate;
- quality-gate tasks;
- readiness follow-up tasks;
- idea bundle export.

Important preserved idea:

- Every important artifact should be exportable or at least serializable.
- Every decision should leave a trace.
- Every recommended action should be able to become a task.

### Project-Level Workflow

The system expanded from single idea to project state:

- project progress overview;
- project readiness overview;
- project quality gate overview;
- project onboarding readiness;
- project setup wizard;
- onboarding tasks;
- onboarding progress;
- pilot status report;
- persisted pilot report snapshots;
- pilot snapshot comparison;
- pilot snapshot tasks;
- pilot comparison tasks;
- project cockpit;
- cockpit tasks;
- advisor chat;
- advisor chat tasks;
- advisor action sessions;
- project triage brief;
- triage tasks;
- persisted triage snapshots;
- triage snapshot comparison;
- triage comparison tasks;
- opportunity radar;
- opportunity radar tasks;
- advisor briefs;
- research execution plans;
- plan tasks;
- plan progress.

The main product insight:

> Users need "what do I do next?" and "can I show this to someone?" more than another isolated generation output.

### Bundle And Customer Delivery Workflow

The project then moved into customer/advisor handoff:

- project bundle export;
- project bundle readiness;
- bundle readiness tasks;
- persisted bundle readiness snapshots;
- bundle readiness snapshot comparison;
- bundle readiness comparison tasks;
- release notes;
- release note tasks;
- release progress;
- release feedback;
- feedback tasks;
- release closeout;
- closeout tasks;
- release acceptance packet;
- persisted acceptance packet snapshots;
- acceptance snapshot comparison;
- acceptance comparison tasks;
- release review session;
- review session tasks;
- persisted review outcomes;
- review outcome tasks;
- review outcome progress.

The latest stable pushed capability is review outcome progress:

- it summarizes post-meeting follow-up execution for a review outcome;
- it reads `ResearchTask` rows with `owner_type=project_bundle_release_review_outcome`;
- it returns task summary, blocked/open/done counts, completion ratio, blocked tasks, next tasks, and Markdown;
- it enters the project bundle as JSON and latest Markdown;
- it appears in manifest fields.

## Current Product State In Plain Language

The project is already much more than RAG.

It can:

- ingest papers;
- generate and evaluate research ideas;
- manage evidence and claims;
- create proposals and experiments;
- turn recommendations into tasks;
- summarize project state;
- prepare project handoff bundles;
- manage customer/advisor release review artifacts;
- expose many stable API tools.

It is not yet a polished customer SaaS.

It still lacks:

- real user/team auth;
- full production database/migrations;
- background worker durability;
- polished full frontend;
- full observability;
- external integrations;
- full GraphRAG/DeerFlow;
- mature managed MCP server.

## Current Incomplete Thread

Immediately before this handoff request, the next implementation round had started:

> project bundle release review outcome signoff evidence records.

The reason:

- The system can record a review outcome.
- It can generate tasks from the outcome.
- It can report progress on those tasks.
- But it still needs a durable signoff evidence artifact that says whether the outcome was signed off, deferred, or declined, by whom, with what conditions and evidence.

Draft design:

- Create signoff records under a release review outcome.
- Persist as `ResearchBrief` scope `project_bundle_release_review_outcome_signoff`.
- Include:
  - `signoff_decision`;
  - `signoff_confirmed`;
  - `approver`;
  - `signoff_notes`;
  - `accepted_artifacts`;
  - `conditions`;
  - `evidence_links`;
  - progress snapshot fields from outcome progress.
- Link graph:
  - outcome -> signoff via `project_bundle_release_review_outcome_has_signoff`.
- Export Markdown.
- Include in project bundle metadata/artifacts/manifest.
- Add Workbench buttons.
- Add tests and smoke.

Known local Windows draft files may already contain partial signoff edits:

- `backend/research/schemas.py`
- `backend/research/routes.py`
- `backend/research/services/artifact_graph_service.py`

But the safe assumption for Mac is:

- GitHub stable may not include these edits.
- Recreate/finish the feature from the TODO if not present.

## User Preferences And Working Style

The user repeatedly asked to:

- keep going without stopping;
- make decisions based on task fit;
- compare against the planned architecture;
- push completed rounds to GitHub;
- report current stage and customer-readiness honestly;
- distinguish developer view and user view;
- avoid relying on old chat history after migration.

Style preference:

- The user is comfortable with ambitious implementation.
- The user wants real product value, not just demos.
- The user trusts the assistant to choose suitable architecture, but expects rationale.
- The assistant should not ask for decisions that can be made from context.

## What Mac Codex Should Do First

1. Read all files in `codex_handoff/`.
2. Clone or update GitHub repo on Mac.
3. Run baseline verification.
4. Check whether signoff feature exists in the current branch.
5. If absent, implement `Project bundle release review outcome signoff evidence records`.
6. Update tests, smoke, README, requirements, technical design.
7. Commit and push.

## Important Safety Notes

- Do not include real passwords, API keys, tokens, cookies, or private keys in docs or commits.
- Do not commit `.env`.
- Do not rely on old Windows local mirror as authoritative.
- Do not delete remote untracked root docs unless the user explicitly asks.
- Do not replace GraphRAG-lite with full GraphRAG unless a new phase calls for it.
- Do not migrate DeerFlow just because it was discussed.
- Do not make MCP a second tool registry.

## One-Sentence Continuation Brief

Continue building Research Assistant Agent as a backend-first, artifact-driven research execution and handoff system; the next best feature is durable release review outcome signoff evidence, implemented through existing schemas/routes/ResearchBrief/GraphRAG-lite/project-bundle/Workbench/tests/smoke/docs patterns, then pushed to GitHub.

