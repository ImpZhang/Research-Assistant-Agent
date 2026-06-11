# Project Context

This folder is a handoff pack for moving the Research Assistant Agent work from the old Windows Codex conversation to a fresh Codex session on Mac. The intent is that a new Codex can read these Markdown files and continue without relying on chat history.

## Project Name

Research Assistant Agent

## Core Theme

The project started as a rethink of a prior `super-mew` RAG project. The original project had a basic retrieval-augmented generation flow, but the user judged that "only connecting a RAG" was too toy-like for a serious project.

The upgraded target is a real research assistant that can help a researcher move from literature to meaningful research ideas, then from ideas to execution, evidence, review, and project-level delivery.

This is not meant to be a generic chatbot. It should become a workflow system that can:

- read papers and extract evidence;
- identify research gaps;
- generate and rank research ideas;
- check novelty/collision risk;
- draft proposals and reviewer critiques;
- build experiment plans;
- track experiment runs and analysis;
- maintain evidence ledgers and claim validation queues;
- manage project tasks and progress;
- produce advisor/customer-ready Markdown and zip handoff bundles;
- expose stable tools for future MCP/agent integration.

## Original Goal

The initial user goal was:

> Look at the existing remote `super-mew` project, decide how to upgrade it beyond a toy RAG, and design a new research assistant architecture.

Important early questions from the user:

- Should the project use Graph RAG?
- Should it use DeerFlow?
- Should it eventually connect MCP?
- What should the real architecture be?
- What requirements and technical design should be written before implementation?

The resulting direction was:

- Do not merely extend the old project.
- Create a new project under `/home/zhangwz/Research-Assistant-Agent`.
- Keep the architecture backend-first and workflow-oriented.
- Use GraphRAG-lite first, not full GraphRAG/Neo4j.
- Do not migrate DeerFlow at the beginning; borrow ideas only.
- Build a lightweight MCP-ready tool contract early, but do not make MCP the core workflow layer.
- Commit and push each completed implementation round to GitHub.

## Current Goal

The current product goal is:

> Turn Research Assistant Agent into a customer-facing research execution and handoff system, not just a literature-to-idea demo.

The active implementation trajectory is now in the "project delivery loop":

1. Literature to evidence.
2. Evidence to gap and idea.
3. Idea to proposal, review, experiment plan, and execution.
4. Idea/project progress to task board.
5. Project state to cockpit, advisor chat, and triage.
6. Project state to project bundle.
7. Project bundle to release note.
8. Release note to follow-up progress, feedback, closeout, acceptance packet, review session, review outcome, and review outcome progress.
9. Next planned step: persisted review outcome signoff evidence records.

The latest stable pushed round, before this handoff documentation round, was:

- Commit: `b3baf94 Add release review outcome progress`
- Stable capability added: project bundle release review outcome progress tracking.
- Verified on remote: ruff, targeted tests, full pytest, smoke workflow.

There may be local Windows draft edits for the next signoff-evidence feature. Treat those as work in progress unless a later commit exists on GitHub.

## Repositories And Paths

### GitHub

- Repository: `https://github.com/ImpZhang/Research-Assistant-Agent.git`
- Default branch used so far: `main`

### Authoritative Remote Linux Path

- Remote project directory: `/home/zhangwz/Research-Assistant-Agent`
- Remote home directory: `/home/zhangwz`
- Do not store SSH passwords or secrets in project files. Use the user's secure credential source or SSH keychain.

### Current Windows Local Path

- Workspace root: `D:\super-mew改进科研助手`
- Local project mirror: `D:\super-mew改进科研助手\Research-Assistant-Agent`
- This local mirror has not always been a Git worktree. Do not assume local `git status` works here.

### Suggested Mac Path

Use a clean Git clone on Mac:

```bash
mkdir -p ~/Projects
cd ~/Projects
git clone https://github.com/ImpZhang/Research-Assistant-Agent.git
cd Research-Assistant-Agent
```

Suggested Mac project root:

```text
~/Projects/Research-Assistant-Agent
```

If the user prefers a home-level location, this is also fine:

```text
~/Research-Assistant-Agent
```

When handoff docs mention the Windows path, map it to the Mac clone root.

## Technology Stack

Runtime and backend:

- Python 3.12+
- FastAPI
- SQLAlchemy
- Pydantic v2
- Uvicorn
- SQLite for current pilot persistence
- `python-multipart` for upload
- `pypdf` for PDF text extraction
- `requests` for external API calls and smoke checks

Workflow and model-facing libraries:

- LangChain / LangChain Core / LangChain OpenAI
- LangGraph dependency is present, but the core implementation currently remains service/workflow based rather than a full LangGraph conversion.
- OpenAI-compatible model adapter pattern with deterministic fallback when credentials are absent.

Development and testing:

- `uv`
- `pytest`
- FastAPI `TestClient`
- `ruff`
- End-to-end smoke workflow in `scripts/smoke_api.py`

Frontend:

- Static browser Workbench served by FastAPI at `/workbench`
- Files under `backend/static/workbench/`
- No full React/Vue frontend yet.

Deployment:

- `Dockerfile`
- `docker-compose.yml`
- `/health` and `/health/ready`
- Optional API key protection for `/research/*`
- Data volume expected at `/app/data` in container.

Graph / retrieval:

- Local hashed embedding index.
- Lexical/vector context retrieval.
- GraphRAG-lite node and edge persistence using relational tables.
- No Neo4j or full Microsoft GraphRAG indexing/community summarization yet.

MCP:

- Stable tool manifest endpoint: `/research/tools/manifest`
- HTTP MCP-ready bridge spec endpoint: `/research/tools/mcp-spec`
- Lightweight stdio MCP-to-HTTP bridge script: `scripts/mcp_http_bridge.py`
- This is a bridge/adapter layer, not the core business logic.

## Business And Product Background

The user wants a project strong enough to show as a serious research assistant, eventually customer-facing. "Customer" here can mean a real user, advisor, lab collaborator, or pilot stakeholder who needs clear project state and handoff artifacts.

The product should help answer questions such as:

- What have we learned from the papers?
- Which research ideas are promising?
- What evidence supports or weakens each idea?
- What experiments should be run next?
- What changed since the last project update?
- Is the current project ready to hand off or show to a customer/advisor?
- What still blocks acceptance/signoff?
- Can an external agent safely inspect or continue the project through stable tools?

## Papers, Tools, And Reference Ideas Mentioned

The architecture discussion referenced these concepts:

- RAG and research-paper grounded generation.
- GraphRAG and Microsoft GraphRAG-style knowledge graph/community retrieval.
- GraphRAG-lite as the selected first implementation.
- DeerFlow as an optional future long-horizon agent harness, not migrated now.
- MCP as a future external tool protocol; current implementation provides tool manifest and a lightweight bridge.
- Research workflow systems that turn evidence into ideas, tasks, experiments, and decision artifacts.

Important conclusion: the project should choose tools by task fit. GraphRAG, DeerFlow, and MCP are not goals by themselves.

