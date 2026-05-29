from collections import Counter

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from backend.research.config import settings
from backend.research.db import get_session
from backend.research.models import (
    Chunk,
    Evidence,
    ExperimentAnalysis,
    ExperimentPlan,
    ExperimentRun,
    Idea,
    IdeaDecisionMemo,
    IdeaFeedback,
    IdeaPortfolioSnapshot,
    Job,
    NoveltyCheck,
    Paper,
    PaperCard,
    PaperSection,
    ProposalDraft,
    ProposalReview,
    ProposalRevision,
    RelatedWorkMatrix,
    ResearchBrief,
    ResearchEdge,
    ResearchGap,
    ResearchNode,
    Review,
    ResearchTask,
    ResearchTaskEvent,
    TaskBoardSnapshot,
)
from backend.research.schemas import (
    ContextSearchRequest,
    ContextSearchResponse,
    EmbeddingRebuildRequest,
    EmbeddingRebuildResponse,
    EvidenceRead,
    ExperimentAnalysisCreate,
    ExperimentAnalysisRead,
    ExperimentPlanRead,
    ExperimentRunCreate,
    ExperimentRunRead,
    ExperimentRunUpdate,
    GapMiningRequest,
    GapMiningResponse,
    IdeaFeedbackCreate,
    IdeaFeedbackRead,
    IdeaGenerationRequest,
    IdeaGenerationResponse,
    IdeaDecisionMemoCreate,
    IdeaDecisionMemoRead,
    IdeaLineageResponse,
    IdeaProgressResponse,
    IdeaPortfolioComparisonRequest,
    IdeaPortfolioComparisonResponse,
    IdeaPortfolioExportRequest,
    IdeaPortfolioSnapshotCreate,
    IdeaPortfolioSnapshotDetail,
    IdeaPortfolioSnapshotRead,
    IdeaRankingRequest,
    IdeaRankingResponse,
    IdeaRefinementRequest,
    IdeaRefinementResponse,
    IdeaRead,
    IdeaScore,
    JobArtifactsResponse,
    JobRead,
    LiteratureSearchRequest,
    LiteratureSearchResponse,
    LiteratureToIdeasWorkflowRequest,
    LiteratureToIdeasWorkflowResponse,
    NoveltyCheckRead,
    PaperCreate,
    PaperCardPayload,
    PaperCardRead,
    PaperDetail,
    PaperRead,
    PaperUploadResponse,
    ProposalDraftCreate,
    ProposalDraftRead,
    ProposalRevisionCreate,
    ProposalRevisionRead,
    ProposalReviewCreate,
    ProposalReviewRead,
    ProjectStatus,
    RankedIdeaRead,
    RelatedWorkMatrixCreate,
    RelatedWorkMatrixRead,
    ResearchBriefCreate,
    ResearchBriefDetail,
    ResearchBriefRead,
    ResearchEdgeRead,
    ResearchGapRead,
    ResearchNodeRead,
    ResearchOverviewResponse,
    ResearchTaskGenerateRequest,
    ResearchTaskGenerationResponse,
    ResearchTaskEventCreate,
    ResearchTaskEventRead,
    ResearchTaskRead,
    ResearchTaskUpdate,
    ReviewRead,
    ScoredEvidenceRead,
    ScoredIdeaRead,
    ScoredResearchGapRead,
    TaskBoardSnapshotCreate,
    TaskBoardSnapshotDetail,
    TaskBoardSnapshotRead,
    ToolManifestItem,
    ToolManifestResponse,
)
from backend.research.services.brief_service import ResearchBriefService
from backend.research.services.document_ingestion import DocumentIngestionService
from backend.research.services.decision_memo_service import IdeaDecisionMemoService
from backend.research.services.embedding_service import EmbeddingService
from backend.research.services.experiment_analysis_service import ExperimentAnalysisService
from backend.research.services.experiment_run_service import ExperimentRunService
from backend.research.services.experiment_service import ExperimentService
from backend.research.services.export_service import ExportService
from backend.research.services.gap_service import GapService
from backend.research.services.graph_service import GraphService
from backend.research.services.idea_feedback_service import IdeaFeedbackService
from backend.research.services.idea_ranking_service import IdeaRankingService
from backend.research.services.idea_refinement_service import IdeaRefinementService
from backend.research.services.idea_service import IdeaService
from backend.research.services.literature_search_service import LiteratureSearchService
from backend.research.services.novelty_service import NoveltyService
from backend.research.services.paper_card_service import PaperCardService
from backend.research.services.paper_service import PaperService
from backend.research.services.portfolio_service import (
    PortfolioService,
    render_portfolio_agenda_markdown,
    render_idea_portfolio_markdown,
    render_snapshot_markdown,
)
from backend.research.services.proposal_service import ProposalDraftService
from backend.research.services.proposal_review_service import ProposalReviewService
from backend.research.services.proposal_revision_service import ProposalRevisionService
from backend.research.services.related_work_service import RelatedWorkService
from backend.research.services.retrieval_service import RetrievalService
from backend.research.services.review_service import ReviewService
from backend.research.services.structured_extraction_service import StructuredExtractionService
from backend.research.services.structured_idea_service import StructuredIdeaService
from backend.research.services.task_service import ResearchTaskService
from backend.research.services.task_board_service import TaskBoardService
from backend.research.services.workflow_service import (
    WorkflowService,
    run_literature_to_ideas_job_background,
)


router = APIRouter(prefix="/research", tags=["research"])


@router.get("/status", response_model=ProjectStatus)
def status() -> ProjectStatus:
    return ProjectStatus(
        service=settings.app_name,
        phase="phase_0_foundation",
        graph_rag_lite_enabled=settings.graph_rag_lite_enabled,
        mcp_enabled=settings.mcp_enabled,
        implemented_capabilities=[
            "fastapi_app",
            "sqlalchemy_models",
            "paper_registry_api",
            "document_ingestion_api",
            "evidence_extraction",
            "paper_card_extraction",
            "structured_extraction_adapter",
            "research_gap_mining",
            "idea_generation",
            "structured_idea_generation_adapter",
            "idea_refinement_loop",
            "idea_ranking_portfolio",
            "idea_progress_summary",
            "idea_decision_memos",
            "project_progress_overview",
            "advisor_research_briefs",
            "tool_manifest",
            "human_idea_feedback",
            "portfolio_markdown_export",
            "persisted_portfolio_snapshots",
            "portfolio_snapshot_comparison",
            "portfolio_execution_agenda",
            "persisted_related_work_matrix",
            "proposal_draft_generation",
            "proposal_readiness_review",
            "proposal_revision_loop",
            "research_task_backlog",
            "task_board_snapshots",
            "local_novelty_collision_check",
            "literature_backed_novelty_screening",
            "reviewer_simulation",
            "experiment_planning",
            "experiment_run_tracking",
            "experiment_result_analysis",
            "experiment_analysis_task_generation",
            "literature_to_ideas_workflow",
            "async_literature_to_ideas_workflow",
            "workflow_job_trace",
            "workflow_job_artifact_snapshot",
            "workflow_job_cancel_retry_controls",
            "literature_search_adapter",
            "local_embedding_index",
            "embedding_backed_context_retrieval",
            "lexical_context_retrieval",
            "graph_rag_lite_schema",
            "graph_rag_lite_workflow_links",
            "graph_rag_lite_context_retrieval",
            "markdown_exports",
            "requirements_and_technical_docs",
        ],
        next_capabilities=[
            "external_embedding_provider",
            "learned_reranking",
            "external_novelty_search",
            "mcp_tool_bridge",
        ],
    )


@router.get("/tools/manifest", response_model=ToolManifestResponse)
def tool_manifest() -> ToolManifestResponse:
    tools = [
        ToolManifestItem(
            name="upload_paper",
            description="Upload and ingest a paper into sections, chunks, and evidence records.",
            method="POST",
            path="/research/papers/upload",
            input_model="multipart/form-data",
            output_model="PaperUploadResponse",
            side_effect=True,
        ),
        ToolManifestItem(
            name="search_research_context",
            description="Search evidence, gaps, ideas, and GraphRAG-lite neighborhoods.",
            method="POST",
            path="/research/search/context",
            input_model="ContextSearchRequest",
            output_model="ContextSearchResponse",
        ),
        ToolManifestItem(
            name="search_literature",
            description="Search local literature and optional external providers.",
            method="POST",
            path="/research/literature/search",
            input_model="LiteratureSearchRequest",
            output_model="LiteratureSearchResponse",
        ),
        ToolManifestItem(
            name="run_literature_to_ideas_workflow",
            description="Run the full literature-to-ideas workflow for an ingested paper.",
            method="POST",
            path="/research/workflows/literature-to-ideas",
            input_model="LiteratureToIdeasWorkflowRequest",
            output_model="LiteratureToIdeasWorkflowResponse",
            side_effect=True,
        ),
        ToolManifestItem(
            name="queue_literature_to_ideas_workflow",
            description="Queue the literature-to-ideas workflow as a background job.",
            method="POST",
            path="/research/workflows/literature-to-ideas/async",
            input_model="LiteratureToIdeasWorkflowRequest",
            output_model="JobRead",
            side_effect=True,
        ),
        ToolManifestItem(
            name="cancel_job",
            description="Cancel a pending or running research workflow job.",
            method="POST",
            path="/research/jobs/{job_id}/cancel",
            output_model="JobRead",
            side_effect=True,
        ),
        ToolManifestItem(
            name="retry_job",
            description="Create and queue a retry for a failed or canceled research workflow job.",
            method="POST",
            path="/research/jobs/{job_id}/retry",
            output_model="JobRead",
            side_effect=True,
        ),
        ToolManifestItem(
            name="get_idea_lineage",
            description="Load proposal, experiment, task, and graph lineage for one idea.",
            method="GET",
            path="/research/ideas/{idea_id}/lineage",
            output_model="IdeaLineageResponse",
        ),
        ToolManifestItem(
            name="get_idea_progress",
            description="Load progress summary and recommended next step for one idea.",
            method="GET",
            path="/research/ideas/{idea_id}/progress",
            output_model="IdeaProgressResponse",
        ),
        ToolManifestItem(
            name="create_idea_decision_memo",
            description="Persist a traceable pursue/revise/park/reject memo for one idea.",
            method="POST",
            path="/research/ideas/{idea_id}/decision-memo",
            input_model="IdeaDecisionMemoCreate",
            output_model="IdeaDecisionMemoRead",
            side_effect=True,
        ),
        ToolManifestItem(
            name="get_project_progress_overview",
            description="Load project-level progress, open tasks, blockers, and recommended actions.",
            method="GET",
            path="/research/progress/overview",
            output_model="ResearchOverviewResponse",
        ),
        ToolManifestItem(
            name="create_advisor_brief",
            description="Create a persisted Markdown research brief for advisor or group review.",
            method="POST",
            path="/research/briefs",
            input_model="ResearchBriefCreate",
            output_model="ResearchBriefDetail",
            side_effect=True,
        ),
        ToolManifestItem(
            name="create_experiment_run",
            description="Record an experiment run for a planned experiment.",
            method="POST",
            path="/research/experiment-plans/{plan_id}/runs",
            input_model="ExperimentRunCreate",
            output_model="ExperimentRunRead",
            side_effect=True,
        ),
        ToolManifestItem(
            name="analyze_experiment_run",
            description="Analyze a recorded experiment run and produce next actions.",
            method="POST",
            path="/research/experiment-runs/{run_id}/analysis",
            input_model="ExperimentAnalysisCreate",
            output_model="ExperimentAnalysisRead",
            side_effect=True,
        ),
        ToolManifestItem(
            name="create_tasks_from_experiment_analysis",
            description="Turn experiment-analysis next actions into research tasks.",
            method="POST",
            path="/research/experiment-analyses/{analysis_id}/tasks",
            input_model="ResearchTaskGenerateRequest",
            output_model="ResearchTaskGenerationResponse",
            side_effect=True,
        ),
    ]
    return ToolManifestResponse(
        service=settings.app_name,
        mcp_enabled=settings.mcp_enabled,
        tools=tools,
        message=f"Loaded {len(tools)} tool definitions for future MCP/tool bridge use.",
    )


@router.get("/progress/overview", response_model=ResearchOverviewResponse)
def get_research_progress_overview(
    idea_limit: int = 50,
    task_limit: int = 300,
    session: Session = Depends(get_session),
) -> ResearchOverviewResponse:
    idea_limit = max(1, min(idea_limit, 200))
    task_limit = max(1, min(task_limit, 1000))
    ideas = session.query(Idea).order_by(Idea.updated_at.desc()).limit(idea_limit).all()
    tasks = (
        session.query(ResearchTask).order_by(ResearchTask.created_at.desc()).limit(task_limit).all()
    )
    analyses = (
        session.query(ExperimentAnalysis)
        .order_by(ExperimentAnalysis.created_at.desc())
        .limit(30)
        .all()
    )
    status_counts = dict(Counter(idea.status for idea in ideas))
    task_summary = _overview_task_summary(tasks)
    recent_experiment_analyses = [
        {
            "id": analysis.id,
            "idea_id": analysis.idea_id,
            "experiment_run_id": analysis.experiment_run_id,
            "decision": analysis.decision,
            "confidence": analysis.confidence,
        }
        for analysis in analyses[:10]
    ]
    blocked_tasks = [
        {
            "id": task.id,
            "idea_id": task.idea_id,
            "title": task.title,
            "priority": task.priority,
            "owner_type": task.owner_type,
        }
        for task in tasks
        if task.status == "blocked"
    ][:20]
    recommended_actions = _overview_recommendations(
        idea_count=len(ideas),
        task_summary=task_summary,
        blocked_tasks=blocked_tasks,
        recent_experiment_analyses=recent_experiment_analyses,
    )
    markdown_export = _render_research_overview_markdown(
        idea_count=len(ideas),
        status_counts=status_counts,
        task_summary=task_summary,
        recent_experiment_analyses=recent_experiment_analyses,
        blocked_tasks=blocked_tasks,
        recommended_actions=recommended_actions,
    )
    return ResearchOverviewResponse(
        idea_count=len(ideas),
        status_counts=status_counts,
        task_summary=task_summary,
        recent_experiment_analyses=recent_experiment_analyses,
        blocked_tasks=blocked_tasks,
        recommended_actions=recommended_actions,
        markdown_export=markdown_export,
        message=(
            f"Loaded project progress overview for {len(ideas)} ideas and "
            f"{len(tasks)} recent tasks."
        ),
    )


def _overview_task_summary(tasks: list[ResearchTask]) -> dict:
    by_status = Counter(task.status for task in tasks)
    by_priority = Counter(task.priority for task in tasks)
    open_tasks = [task for task in tasks if task.status in {"todo", "doing", "blocked"}]
    top_open_tasks = sorted(open_tasks, key=_progress_task_order)[:10]
    return {
        "total_recent_tasks": len(tasks),
        "open_task_count": len(open_tasks),
        "by_status": dict(by_status),
        "by_priority": dict(by_priority),
        "top_open_tasks": [
            {
                "id": task.id,
                "idea_id": task.idea_id,
                "title": task.title,
                "priority": task.priority,
                "status": task.status,
                "owner_type": task.owner_type,
            }
            for task in top_open_tasks
        ],
    }


def _overview_recommendations(
    *,
    idea_count: int,
    task_summary: dict,
    blocked_tasks: list[dict],
    recent_experiment_analyses: list[dict],
) -> list[str]:
    if idea_count == 0:
        return ["Ingest papers and run the literature-to-ideas workflow."]
    if blocked_tasks:
        return ["Resolve blocked research tasks before expanding the portfolio."]
    if not recent_experiment_analyses:
        return ["Record and analyze experiment runs for the strongest shortlisted ideas."]
    top_open_tasks = task_summary.get("top_open_tasks") or []
    if top_open_tasks:
        first = top_open_tasks[0]
        return [
            f"Work the highest-priority task: {first['title']}",
            "Refresh the idea progress summary after completing or blocking that task.",
        ]
    return [
        "Create a new portfolio snapshot or ingest new literature to refresh the research queue."
    ]


def _render_research_overview_markdown(
    *,
    idea_count: int,
    status_counts: dict[str, int],
    task_summary: dict,
    recent_experiment_analyses: list[dict],
    blocked_tasks: list[dict],
    recommended_actions: list[str],
) -> str:
    lines = [
        "# Research Progress Overview",
        "",
        f"- Idea Count: {idea_count}",
        f"- Status Counts: {status_counts}",
        f"- Open Tasks: {task_summary.get('open_task_count', 0)}",
        "",
        "## Top Open Tasks",
        "",
    ]
    top_open_tasks = task_summary.get("top_open_tasks") or []
    if top_open_tasks:
        for task in top_open_tasks:
            lines.append(
                f"- `{task['id']}` `{task['priority']}` `{task['status']}` {task['title']}"
            )
    else:
        lines.append("- No open tasks.")
    lines.extend(["", "## Recent Experiment Analyses", ""])
    if recent_experiment_analyses:
        for analysis in recent_experiment_analyses:
            lines.append(
                f"- `{analysis['id']}` `{analysis['decision']}` "
                f"confidence={analysis['confidence']:.2f}"
            )
    else:
        lines.append("- No experiment analyses yet.")
    lines.extend(["", "## Blocked Tasks", ""])
    if blocked_tasks:
        for task in blocked_tasks:
            lines.append(f"- `{task['id']}` `{task['priority']}` {task['title']}")
    else:
        lines.append("- No blocked tasks.")
    lines.extend(["", "## Recommended Actions", ""])
    lines.extend(f"- {action}" for action in recommended_actions)
    return "\n".join(lines).strip() + "\n"


def _serialize_research_brief(
    brief: ResearchBrief,
    *,
    include_markdown: bool = False,
) -> ResearchBriefRead | ResearchBriefDetail:
    payload = {
        "id": brief.id,
        "title": brief.title,
        "scope": brief.scope,
        "idea_ids": brief.idea_ids_json or [],
        "summary": brief.summary_json or {},
        "markdown_export_chars": len(brief.markdown_export or ""),
        "created_by": brief.created_by,
        "created_at": brief.created_at,
        "updated_at": brief.updated_at,
    }
    if include_markdown:
        return ResearchBriefDetail(
            **payload,
            markdown_export=brief.markdown_export or "",
        )
    return ResearchBriefRead(**payload)


@router.post("/briefs", response_model=ResearchBriefDetail)
def create_research_brief(
    payload: ResearchBriefCreate,
    session: Session = Depends(get_session),
) -> ResearchBriefDetail:
    try:
        brief = ResearchBriefService(session).create_brief(
            title=payload.title,
            scope=payload.scope,
            idea_ids=payload.idea_ids,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize_research_brief(brief, include_markdown=True)


@router.get("/briefs", response_model=list[ResearchBriefRead])
def list_research_briefs(
    limit: int = 50,
    session: Session = Depends(get_session),
) -> list[ResearchBriefRead]:
    briefs = ResearchBriefService(session).list_briefs(limit)
    return [_serialize_research_brief(brief) for brief in briefs]


@router.get("/briefs/{brief_id}", response_model=ResearchBriefDetail)
def get_research_brief(
    brief_id: str,
    session: Session = Depends(get_session),
) -> ResearchBriefDetail:
    brief = ResearchBriefService(session).get_brief(brief_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="Research brief not found")
    return _serialize_research_brief(brief, include_markdown=True)


@router.get(
    "/briefs/{brief_id}/export/markdown",
    response_class=PlainTextResponse,
)
def export_research_brief_markdown(
    brief_id: str,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    brief = ResearchBriefService(session).get_brief(brief_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="Research brief not found")
    return PlainTextResponse(brief.markdown_export or "", media_type="text/markdown")


def _serialize_job(job: Job) -> JobRead:
    return JobRead(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        progress=job.progress,
        input=job.input_json or {},
        output=job.output_json or {},
        error=job.error,
    )


def _serialize_paper(paper: Paper) -> PaperRead:
    return PaperRead(
        id=paper.id,
        title=paper.title,
        authors=paper.authors_json or [],
        year=paper.year,
        venue=paper.venue,
        filename=paper.filename,
        domain=paper.domain,
        task=paper.task,
        status=paper.status,
        created_at=paper.created_at,
        updated_at=paper.updated_at,
    )


def _load_ordered_by_ids(session: Session, model, ids: list[str]) -> list:
    if not ids:
        return []
    records = session.query(model).filter(model.id.in_(ids)).all()
    by_id = {record.id: record for record in records}
    return [by_id[record_id] for record_id in ids if record_id in by_id]


def _render_idea_bundle_markdown(session: Session, ideas: list[Idea]) -> str:
    if not ideas:
        return ""

    export_service = ExportService(session)
    sections = [export_service.render_idea_markdown(idea.id).strip() for idea in ideas]
    return "\n---\n\n".join(section for section in sections if section) + "\n"


@router.get("/jobs", response_model=list[JobRead])
def list_jobs(limit: int = 50, session: Session = Depends(get_session)) -> list[JobRead]:
    limit = max(1, min(limit, 200))
    jobs = session.query(Job).order_by(Job.created_at.desc()).limit(limit).all()
    return [_serialize_job(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job(job_id: str, session: Session = Depends(get_session)) -> JobRead:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _serialize_job(job)


@router.post("/jobs/{job_id}/cancel", response_model=JobRead)
def cancel_job(job_id: str, session: Session = Depends(get_session)) -> JobRead:
    try:
        job = WorkflowService(session).cancel_job(job_id)
    except ValueError as exc:
        status_code = 404 if str(exc) == "Job not found" else 409
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return _serialize_job(job)


@router.post("/jobs/{job_id}/retry", response_model=JobRead)
def retry_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> JobRead:
    try:
        job = WorkflowService(session).retry_job(job_id)
    except ValueError as exc:
        status_code = 404 if str(exc) == "Job not found" else 409
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    if job.job_type == "literature_to_ideas_workflow":
        background_tasks.add_task(run_literature_to_ideas_job_background, job.id)
    return _serialize_job(job)


@router.get("/jobs/{job_id}/artifacts", response_model=JobArtifactsResponse)
def get_job_artifacts(
    job_id: str,
    session: Session = Depends(get_session),
) -> JobArtifactsResponse:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    output = job.output_json or {}
    input_payload = job.input_json or {}
    paper_id = output.get("paper_id") or input_payload.get("paper_id") or ""
    paper = session.get(Paper, paper_id) if paper_id else None
    card = session.get(PaperCard, output.get("card_id")) if output.get("card_id") else None
    gaps = _load_ordered_by_ids(session, ResearchGap, output.get("gap_ids") or [])
    ideas = _load_ordered_by_ids(session, Idea, output.get("idea_ids") or [])
    novelty_checks = _load_ordered_by_ids(
        session,
        NoveltyCheck,
        output.get("novelty_check_ids") or [],
    )
    reviews = _load_ordered_by_ids(session, Review, output.get("review_ids") or [])
    experiment_plans = _load_ordered_by_ids(
        session,
        ExperimentPlan,
        output.get("experiment_plan_ids") or [],
    )
    markdown_export = _render_idea_bundle_markdown(session, ideas)

    return JobArtifactsResponse(
        job=_serialize_job(job),
        paper=_serialize_paper(paper) if paper else None,
        card=_serialize_card(card) if card else None,
        gaps=[_serialize_gap(gap) for gap in gaps],
        ideas=[_serialize_idea(idea) for idea in ideas],
        novelty_checks=[_serialize_novelty_check(check) for check in novelty_checks],
        reviews=[_serialize_review(review) for review in reviews],
        experiment_plans=[_serialize_experiment_plan(plan) for plan in experiment_plans],
        markdown_export=markdown_export,
        message=(
            f"Loaded artifact snapshot for job {job.id}: "
            f"{len(gaps)} gaps, {len(ideas)} ideas, "
            f"{len(novelty_checks)} novelty checks, {len(reviews)} reviews, "
            f"{len(experiment_plans)} experiment plans."
        ),
    )


@router.post("/literature/search", response_model=LiteratureSearchResponse)
def search_literature(
    payload: LiteratureSearchRequest,
    session: Session = Depends(get_session),
) -> LiteratureSearchResponse:
    try:
        return LiteratureSearchService(session).search(
            query=payload.query,
            limit=payload.limit,
            include_external=payload.include_external,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/embeddings/rebuild", response_model=EmbeddingRebuildResponse)
def rebuild_embeddings(
    payload: EmbeddingRebuildRequest,
    session: Session = Depends(get_session),
) -> EmbeddingRebuildResponse:
    stats = EmbeddingService(session).rebuild_index(
        owner_types=payload.owner_types,
        paper_ids=payload.paper_ids,
        limit=payload.limit,
    )
    return EmbeddingRebuildResponse(
        model=stats.model,
        dimension=stats.dimension,
        indexed_count=stats.indexed_count,
        evidence_count=stats.evidence_count,
        gap_count=stats.gap_count,
        idea_count=stats.idea_count,
        message=f"Indexed {stats.indexed_count} research objects for vector retrieval.",
    )


@router.get("/papers", response_model=list[PaperRead])
def list_papers(session: Session = Depends(get_session)) -> list[PaperRead]:
    papers = PaperService(session).list_papers()
    return [_serialize_paper(paper) for paper in papers]


@router.get("/papers/{paper_id}", response_model=PaperDetail)
def get_paper(paper_id: str, session: Session = Depends(get_session)) -> PaperDetail:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    return PaperDetail(
        **_serialize_paper(paper).model_dump(),
        section_count=session.query(PaperSection).filter(PaperSection.paper_id == paper_id).count(),
        chunk_count=session.query(Chunk).filter(Chunk.paper_id == paper_id).count(),
        evidence_count=session.query(Evidence).filter(Evidence.paper_id == paper_id).count(),
    )


@router.post("/papers", response_model=PaperRead)
def create_paper(payload: PaperCreate, session: Session = Depends(get_session)) -> PaperRead:
    paper = PaperService(session).create_paper(payload)
    return _serialize_paper(paper)


@router.post("/papers/upload", response_model=PaperUploadResponse)
async def upload_paper(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> PaperUploadResponse:
    try:
        result = await DocumentIngestionService(session).ingest_upload(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    paper = result.paper
    return PaperUploadResponse(
        paper=_serialize_paper(paper),
        section_count=result.section_count,
        chunk_count=result.chunk_count,
        evidence_count=result.evidence_count,
        message=f"Ingested {paper.filename} into the research knowledge base.",
    )


@router.get("/papers/{paper_id}/evidence", response_model=list[EvidenceRead])
def list_paper_evidence(
    paper_id: str,
    session: Session = Depends(get_session),
) -> list[EvidenceRead]:
    if session.get(Paper, paper_id) is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    return (
        session.query(Evidence)
        .filter(Evidence.paper_id == paper_id)
        .order_by(Evidence.created_at.asc())
        .all()
    )


def _serialize_evidence(evidence: Evidence) -> EvidenceRead:
    return EvidenceRead(
        id=evidence.id,
        paper_id=evidence.paper_id,
        evidence_type=evidence.evidence_type,
        text=evidence.text,
        summary=evidence.summary,
        supports=evidence.supports,
        confidence=evidence.confidence,
        page_number=evidence.page_number,
    )


def _serialize_card(card) -> PaperCardRead:
    return PaperCardRead(
        id=card.id,
        paper_id=card.paper_id,
        payload=PaperCardPayload(
            problem=card.problem_json.get("items", []) if card.problem_json else [],
            motivation=card.motivation_json.get("items", []) if card.motivation_json else [],
            contributions=card.contributions_json.get("items", [])
            if card.contributions_json
            else [],
            method=card.method_json.get("items", []) if card.method_json else [],
            datasets=card.datasets_json.get("items", []) if card.datasets_json else [],
            metrics=card.metrics_json.get("items", []) if card.metrics_json else [],
            baselines=card.baselines_json.get("items", []) if card.baselines_json else [],
            results=card.results_json.get("items", []) if card.results_json else [],
            limitations=card.limitations_json.get("items", []) if card.limitations_json else [],
            future_work=card.future_work_json.get("items", []) if card.future_work_json else [],
            keywords=card.keywords_json.get("items", []) if card.keywords_json else [],
            open_questions=card.open_questions_json.get("items", [])
            if card.open_questions_json
            else [],
        ),
        extraction_model=card.extraction_model,
        extraction_status=card.extraction_status,
        created_at=card.created_at,
        updated_at=card.updated_at,
    )


@router.get("/papers/{paper_id}/card", response_model=PaperCardRead)
def get_paper_card(paper_id: str, session: Session = Depends(get_session)) -> PaperCardRead:
    if session.get(Paper, paper_id) is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    card = PaperCardService(session).get_card(paper_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Paper card not found")
    return _serialize_card(card)


@router.post("/papers/{paper_id}/card/extract", response_model=PaperCardRead)
def extract_paper_card(paper_id: str, session: Session = Depends(get_session)) -> PaperCardRead:
    try:
        card = PaperCardService(session).extract_heuristic_card(paper_id)
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return _serialize_card(card)


@router.post("/papers/{paper_id}/card/extract-structured", response_model=PaperCardRead)
def extract_paper_card_structured(
    paper_id: str,
    session: Session = Depends(get_session),
) -> PaperCardRead:
    try:
        card = StructuredExtractionService(session).extract_paper_card(paper_id)
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return _serialize_card(card)


@router.get(
    "/papers/{paper_id}/card/export/markdown",
    response_class=PlainTextResponse,
)
def export_paper_card_markdown(
    paper_id: str,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    try:
        markdown = ExportService(session).render_paper_card_markdown(paper_id)
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return PlainTextResponse(markdown, media_type="text/markdown")


def _serialize_gap(gap) -> ResearchGapRead:
    return ResearchGapRead(
        id=gap.id,
        title=gap.title,
        description=gap.description,
        gap_type=gap.gap_type,
        source_paper_ids=gap.source_paper_ids_json or [],
        evidence_ids=gap.evidence_ids_json or [],
        why_important=gap.why_important,
        why_unsolved=gap.why_unsolved,
        possible_approaches=gap.possible_approaches_json or [],
        feasibility_score=gap.feasibility_score,
        novelty_score=gap.novelty_score,
        risk_level=gap.risk_level,
        status=gap.status,
        created_at=gap.created_at,
        updated_at=gap.updated_at,
    )


@router.post("/gaps/mine", response_model=GapMiningResponse)
def mine_gaps(
    payload: GapMiningRequest,
    session: Session = Depends(get_session),
) -> GapMiningResponse:
    gaps = GapService(session).mine_gaps(payload.paper_ids, payload.max_gaps)
    return GapMiningResponse(
        gaps=[_serialize_gap(gap) for gap in gaps],
        message=f"Generated {len(gaps)} research gaps from available evidence.",
    )


@router.get("/gaps", response_model=list[ResearchGapRead])
def list_gaps(session: Session = Depends(get_session)) -> list[ResearchGapRead]:
    return [_serialize_gap(gap) for gap in GapService(session).list_gaps()]


@router.get("/gaps/{gap_id}", response_model=ResearchGapRead)
def get_gap(gap_id: str, session: Session = Depends(get_session)) -> ResearchGapRead:
    gap = GapService(session).get_gap(gap_id)
    if gap is None:
        raise HTTPException(status_code=404, detail="Research gap not found")
    return _serialize_gap(gap)


def _serialize_idea(idea) -> IdeaRead:
    return IdeaRead(
        id=idea.id,
        title=idea.title,
        research_question=idea.research_question,
        core_hypothesis=idea.core_hypothesis,
        motivation=idea.motivation,
        related_gap_ids=idea.related_gap_ids_json or [],
        related_paper_ids=idea.related_paper_ids_json or [],
        evidence_ids=idea.evidence_ids_json or [],
        method_sketch=idea.method_sketch,
        expected_contribution=idea.expected_contribution,
        novelty_argument=idea.novelty_argument,
        datasets=idea.datasets_json or [],
        baselines=idea.baselines_json or [],
        metrics=idea.metrics_json or [],
        risks=idea.risks_json or [],
        resource_requirements=idea.resource_requirements,
        target_venues=idea.target_venues_json or [],
        score=IdeaScore(**(idea.score_json or {})),
        status=idea.status,
        version=idea.version,
        parent_idea_id=idea.parent_idea_id,
        created_at=idea.created_at,
        updated_at=idea.updated_at,
    )


def _serialize_feedback(feedback: IdeaFeedback) -> IdeaFeedbackRead:
    return IdeaFeedbackRead(
        id=feedback.id,
        idea_id=feedback.idea_id,
        decision=feedback.decision,
        rating=feedback.rating,
        comment=feedback.comment,
        tags=feedback.tags_json or [],
        created_by=feedback.created_by,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
    )


def _serialize_portfolio_snapshot(
    snapshot: IdeaPortfolioSnapshot,
    *,
    include_markdown: bool = False,
) -> IdeaPortfolioSnapshotRead | IdeaPortfolioSnapshotDetail:
    payload = {
        "id": snapshot.id,
        "title": snapshot.title,
        "description": snapshot.description,
        "ranking_request": snapshot.ranking_request_json or {},
        "idea_ids": snapshot.idea_ids_json or [],
        "ranked_items": snapshot.ranked_items_json or [],
        "markdown_export_chars": len(snapshot.markdown_export or ""),
        "created_by": snapshot.created_by,
        "created_at": snapshot.created_at,
        "updated_at": snapshot.updated_at,
    }
    if include_markdown:
        return IdeaPortfolioSnapshotDetail(
            **payload,
            markdown_export=snapshot.markdown_export or "",
        )
    return IdeaPortfolioSnapshotRead(**payload)


def _serialize_related_work_matrix(matrix: RelatedWorkMatrix) -> RelatedWorkMatrixRead:
    return RelatedWorkMatrixRead(
        id=matrix.id,
        idea_id=matrix.idea_id,
        status=matrix.status,
        query=matrix.query,
        items=matrix.items_json or [],
        differentiators=matrix.differentiators_json or [],
        missing_searches=matrix.missing_searches_json or [],
        checked_sources=matrix.checked_sources_json or [],
        summary=matrix.summary,
        markdown_export=matrix.markdown_export or "",
        created_by=matrix.created_by,
        created_at=matrix.created_at,
        updated_at=matrix.updated_at,
    )


def _serialize_proposal_draft(draft: ProposalDraft) -> ProposalDraftRead:
    return ProposalDraftRead(
        id=draft.id,
        idea_id=draft.idea_id,
        status=draft.status,
        title=draft.title,
        abstract=draft.abstract,
        problem_statement=draft.problem_statement,
        novelty_statement=draft.novelty_statement,
        related_work_summary=draft.related_work_summary,
        method_summary=draft.method_summary,
        experiment_summary=draft.experiment_summary,
        risk_mitigation=draft.risk_mitigation,
        milestone_plan=draft.milestone_plan_json or [],
        evidence_ids=draft.evidence_ids_json or [],
        related_work_matrix_id=draft.related_work_matrix_id,
        experiment_plan_id=draft.experiment_plan_id,
        markdown_export=draft.markdown_export or "",
        created_by=draft.created_by,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )


def _serialize_proposal_review(review: ProposalReview) -> ProposalReviewRead:
    return ProposalReviewRead(
        id=review.id,
        proposal_draft_id=review.proposal_draft_id,
        idea_id=review.idea_id,
        reviewer_type=review.reviewer_type,
        decision=review.decision,
        readiness_score=review.readiness_score,
        strengths=review.strengths_json or [],
        concerns=review.concerns_json or [],
        required_revisions=review.required_revisions_json or [],
        missing_evidence=review.missing_evidence_json or [],
        summary=review.summary,
        markdown_export=review.markdown_export or "",
        created_by=review.created_by,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def _serialize_proposal_revision(revision: ProposalRevision) -> ProposalRevisionRead:
    return ProposalRevisionRead(
        id=revision.id,
        proposal_draft_id=revision.proposal_draft_id,
        proposal_review_id=revision.proposal_review_id,
        idea_id=revision.idea_id,
        status=revision.status,
        revision_summary=revision.revision_summary,
        applied_revisions=revision.applied_revisions_json or [],
        missing_evidence_actions=revision.missing_evidence_actions_json or [],
        revised_sections=revision.revised_sections_json or {},
        markdown_export=revision.markdown_export or "",
        created_by=revision.created_by,
        created_at=revision.created_at,
        updated_at=revision.updated_at,
    )


def _serialize_idea_decision_memo(memo: IdeaDecisionMemo) -> IdeaDecisionMemoRead:
    return IdeaDecisionMemoRead(
        id=memo.id,
        idea_id=memo.idea_id,
        decision=memo.decision,
        rationale=memo.rationale_json or [],
        evidence_ids=memo.evidence_ids_json or [],
        risk_register=memo.risk_register_json or [],
        next_commitments=memo.next_commitments_json or [],
        source_artifacts=memo.source_artifacts_json or {},
        markdown_export=memo.markdown_export or "",
        created_by=memo.created_by,
        created_at=memo.created_at,
        updated_at=memo.updated_at,
    )


def _serialize_research_task(task: ResearchTask) -> ResearchTaskRead:
    return ResearchTaskRead(
        id=task.id,
        idea_id=task.idea_id,
        owner_type=task.owner_type,
        owner_id=task.owner_id,
        source_type=task.source_type,
        source_id=task.source_id,
        title=task.title,
        description=task.description,
        priority=task.priority,
        status=task.status,
        due_phase=task.due_phase,
        metadata=task.metadata_json or {},
        created_by=task.created_by,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _serialize_research_task_event(event: ResearchTaskEvent) -> ResearchTaskEventRead:
    return ResearchTaskEventRead(
        id=event.id,
        task_id=event.task_id,
        idea_id=event.idea_id,
        event_type=event.event_type,
        status_from=event.status_from,
        status_to=event.status_to,
        priority_from=event.priority_from,
        priority_to=event.priority_to,
        note=event.note,
        metadata=event.metadata_json or {},
        created_by=event.created_by,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def _serialize_task_board_snapshot(
    snapshot: TaskBoardSnapshot,
    *,
    include_markdown: bool = False,
) -> TaskBoardSnapshotRead | TaskBoardSnapshotDetail:
    payload = {
        "id": snapshot.id,
        "title": snapshot.title,
        "idea_id": snapshot.idea_id,
        "owner_type": snapshot.owner_type,
        "status_filter": snapshot.status_filter_json or [],
        "task_ids": snapshot.task_ids_json or [],
        "summary": snapshot.summary_json or {},
        "markdown_export_chars": len(snapshot.markdown_export or ""),
        "created_by": snapshot.created_by,
        "created_at": snapshot.created_at,
        "updated_at": snapshot.updated_at,
    }
    if include_markdown:
        return TaskBoardSnapshotDetail(
            **payload,
            markdown_export=snapshot.markdown_export or "",
        )
    return TaskBoardSnapshotRead(**payload)


@router.post("/ideas/generate", response_model=IdeaGenerationResponse)
def generate_ideas(
    payload: IdeaGenerationRequest,
    session: Session = Depends(get_session),
) -> IdeaGenerationResponse:
    ideas = StructuredIdeaService(session).generate_from_gaps(
        payload.gap_ids,
        payload.max_ideas_per_gap,
    )
    return IdeaGenerationResponse(
        ideas=[_serialize_idea(idea) for idea in ideas],
        message=f"Generated {len(ideas)} research ideas from selected gaps with structured adapter.",
    )


@router.post("/gaps/{gap_id}/ideas", response_model=IdeaGenerationResponse)
def generate_ideas_for_gap(
    gap_id: str,
    session: Session = Depends(get_session),
) -> IdeaGenerationResponse:
    if GapService(session).get_gap(gap_id) is None:
        raise HTTPException(status_code=404, detail="Research gap not found")
    ideas = StructuredIdeaService(session).generate_from_gaps([gap_id], 2)
    return IdeaGenerationResponse(
        ideas=[_serialize_idea(idea) for idea in ideas],
        message=f"Generated {len(ideas)} research ideas from gap {gap_id} with structured adapter.",
    )


@router.get("/ideas", response_model=list[IdeaRead])
def list_ideas(session: Session = Depends(get_session)) -> list[IdeaRead]:
    return [_serialize_idea(idea) for idea in IdeaService(session).list_ideas()]


@router.post("/ideas/rank", response_model=IdeaRankingResponse)
def rank_ideas(
    payload: IdeaRankingRequest,
    session: Session = Depends(get_session),
) -> IdeaRankingResponse:
    ranked = IdeaRankingService(session).rank_ideas(
        idea_ids=payload.idea_ids,
        gap_ids=payload.gap_ids,
        paper_ids=payload.paper_ids,
        limit=payload.limit,
        weights=payload.weights,
        include_refined=payload.include_refined,
        deduplicate_lineage=payload.deduplicate_lineage,
    )
    return IdeaRankingResponse(
        ranked_ideas=[
            RankedIdeaRead(
                rank=item.rank,
                idea=_serialize_idea(item.idea),
                weighted_score=item.weighted_score,
                score_breakdown=item.score_breakdown,
                rationale=item.rationale,
            )
            for item in ranked
        ],
        message=f"Ranked {len(ranked)} ideas for research portfolio review.",
    )


@router.post(
    "/ideas/rank/export/markdown",
    response_class=PlainTextResponse,
)
def export_ranked_ideas_markdown(
    payload: IdeaPortfolioExportRequest,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    ranked = IdeaRankingService(session).rank_ideas(
        idea_ids=payload.idea_ids,
        gap_ids=payload.gap_ids,
        paper_ids=payload.paper_ids,
        limit=payload.limit,
        weights=payload.weights,
        include_refined=payload.include_refined,
        deduplicate_lineage=payload.deduplicate_lineage,
    )
    markdown = render_idea_portfolio_markdown(payload.title, ranked)
    return PlainTextResponse(markdown, media_type="text/markdown")


@router.post("/ideas/portfolios", response_model=IdeaPortfolioSnapshotDetail)
def create_idea_portfolio_snapshot(
    payload: IdeaPortfolioSnapshotCreate,
    session: Session = Depends(get_session),
) -> IdeaPortfolioSnapshotDetail:
    snapshot = PortfolioService(session).create_snapshot(
        title=payload.title,
        description=payload.description,
        created_by=payload.created_by,
        idea_ids=payload.idea_ids,
        gap_ids=payload.gap_ids,
        paper_ids=payload.paper_ids,
        limit=payload.limit,
        weights=payload.weights,
        include_refined=payload.include_refined,
        deduplicate_lineage=payload.deduplicate_lineage,
    )
    return _serialize_portfolio_snapshot(snapshot, include_markdown=True)


@router.get("/ideas/portfolios", response_model=list[IdeaPortfolioSnapshotRead])
def list_idea_portfolio_snapshots(
    limit: int = 50,
    session: Session = Depends(get_session),
) -> list[IdeaPortfolioSnapshotRead]:
    snapshots = PortfolioService(session).list_snapshots(limit)
    return [_serialize_portfolio_snapshot(snapshot) for snapshot in snapshots]


@router.post("/ideas/portfolios/compare", response_model=IdeaPortfolioComparisonResponse)
def compare_idea_portfolio_snapshots(
    payload: IdeaPortfolioComparisonRequest,
    session: Session = Depends(get_session),
) -> IdeaPortfolioComparisonResponse:
    try:
        comparison = PortfolioService(session).compare_snapshots(
            payload.baseline_snapshot_id,
            payload.candidate_snapshot_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return IdeaPortfolioComparisonResponse(**comparison)


@router.post(
    "/ideas/portfolios/compare/export/markdown",
    response_class=PlainTextResponse,
)
def export_idea_portfolio_comparison_markdown(
    payload: IdeaPortfolioComparisonRequest,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    try:
        comparison = PortfolioService(session).compare_snapshots(
            payload.baseline_snapshot_id,
            payload.candidate_snapshot_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PlainTextResponse(comparison["markdown_export"], media_type="text/markdown")


@router.get("/ideas/portfolios/{snapshot_id}", response_model=IdeaPortfolioSnapshotDetail)
def get_idea_portfolio_snapshot(
    snapshot_id: str,
    session: Session = Depends(get_session),
) -> IdeaPortfolioSnapshotDetail:
    snapshot = PortfolioService(session).get_snapshot(snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Idea portfolio snapshot not found")
    return _serialize_portfolio_snapshot(snapshot, include_markdown=True)


@router.get(
    "/ideas/portfolios/{snapshot_id}/export/markdown",
    response_class=PlainTextResponse,
)
def export_idea_portfolio_snapshot_markdown(
    snapshot_id: str,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    snapshot = PortfolioService(session).get_snapshot(snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Idea portfolio snapshot not found")
    return PlainTextResponse(render_snapshot_markdown(snapshot), media_type="text/markdown")


@router.get(
    "/ideas/portfolios/{snapshot_id}/agenda/markdown",
    response_class=PlainTextResponse,
)
def export_idea_portfolio_agenda_markdown(
    snapshot_id: str,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    snapshot = PortfolioService(session).get_snapshot(snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Idea portfolio snapshot not found")
    return PlainTextResponse(render_portfolio_agenda_markdown(snapshot), media_type="text/markdown")


@router.get("/ideas/{idea_id}", response_model=IdeaRead)
def get_idea(idea_id: str, session: Session = Depends(get_session)) -> IdeaRead:
    idea = IdeaService(session).get_idea(idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")
    return _serialize_idea(idea)


@router.get("/ideas/{idea_id}/lineage", response_model=IdeaLineageResponse)
def get_idea_lineage(
    idea_id: str,
    session: Session = Depends(get_session),
) -> IdeaLineageResponse:
    idea = IdeaService(session).get_idea(idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")

    matrices = (
        session.query(RelatedWorkMatrix)
        .filter(RelatedWorkMatrix.idea_id == idea_id)
        .order_by(RelatedWorkMatrix.created_at.desc())
        .limit(20)
        .all()
    )
    drafts = (
        session.query(ProposalDraft)
        .filter(ProposalDraft.idea_id == idea_id)
        .order_by(ProposalDraft.created_at.desc())
        .limit(20)
        .all()
    )
    reviews = (
        session.query(ProposalReview)
        .filter(ProposalReview.idea_id == idea_id)
        .order_by(ProposalReview.created_at.desc())
        .limit(50)
        .all()
    )
    revisions = (
        session.query(ProposalRevision)
        .filter(ProposalRevision.idea_id == idea_id)
        .order_by(ProposalRevision.created_at.desc())
        .limit(50)
        .all()
    )
    experiment_runs = (
        session.query(ExperimentRun)
        .filter(ExperimentRun.idea_id == idea_id)
        .order_by(ExperimentRun.created_at.desc())
        .limit(50)
        .all()
    )
    experiment_analyses = (
        session.query(ExperimentAnalysis)
        .filter(ExperimentAnalysis.idea_id == idea_id)
        .order_by(ExperimentAnalysis.created_at.desc())
        .limit(50)
        .all()
    )
    decision_memos = (
        session.query(IdeaDecisionMemo)
        .filter(IdeaDecisionMemo.idea_id == idea_id)
        .order_by(IdeaDecisionMemo.created_at.desc())
        .limit(20)
        .all()
    )
    tasks = (
        session.query(ResearchTask)
        .filter(ResearchTask.idea_id == idea_id)
        .order_by(ResearchTask.created_at.desc())
        .limit(100)
        .all()
    )
    snapshots = (
        session.query(TaskBoardSnapshot)
        .filter(TaskBoardSnapshot.idea_id == idea_id)
        .order_by(TaskBoardSnapshot.created_at.desc())
        .limit(20)
        .all()
    )
    graph_edge_summary = _graph_edge_summary(
        session,
        [
            idea_id,
            *[matrix.id for matrix in matrices],
            *[draft.id for draft in drafts],
            *[review.id for review in reviews],
            *[revision.id for revision in revisions],
            *[run.experiment_plan_id for run in experiment_runs],
            *[run.id for run in experiment_runs],
            *[analysis.id for analysis in experiment_analyses],
            *[memo.id for memo in decision_memos],
            *[task.id for task in tasks],
            *[snapshot.id for snapshot in snapshots],
        ],
    )
    markdown_export = _render_idea_lineage_markdown(
        idea=idea,
        matrices=matrices,
        drafts=drafts,
        reviews=reviews,
        revisions=revisions,
        experiment_runs=experiment_runs,
        experiment_analyses=experiment_analyses,
        decision_memos=decision_memos,
        tasks=tasks,
        snapshots=snapshots,
        graph_edge_summary=graph_edge_summary,
    )
    return IdeaLineageResponse(
        idea=_serialize_idea(idea),
        related_work_matrices=[_serialize_related_work_matrix(matrix) for matrix in matrices],
        proposal_drafts=[_serialize_proposal_draft(draft) for draft in drafts],
        proposal_reviews=[_serialize_proposal_review(review) for review in reviews],
        proposal_revisions=[_serialize_proposal_revision(revision) for revision in revisions],
        experiment_runs=[_serialize_experiment_run(run) for run in experiment_runs],
        experiment_analyses=[
            _serialize_experiment_analysis(analysis) for analysis in experiment_analyses
        ],
        decision_memos=[_serialize_idea_decision_memo(memo) for memo in decision_memos],
        research_tasks=[_serialize_research_task(task) for task in tasks],
        task_board_snapshots=[_serialize_task_board_snapshot(snapshot) for snapshot in snapshots],
        graph_edge_summary=graph_edge_summary,
        markdown_export=markdown_export,
        message=(
            f"Loaded lineage for idea {idea.id}: {len(drafts)} drafts, "
            f"{len(reviews)} reviews, {len(revisions)} revisions, "
            f"{len(experiment_runs)} experiment runs, "
            f"{len(experiment_analyses)} analyses, "
            f"{len(decision_memos)} decision memos, {len(tasks)} tasks."
        ),
    )


@router.get("/ideas/{idea_id}/progress", response_model=IdeaProgressResponse)
def get_idea_progress(
    idea_id: str,
    session: Session = Depends(get_session),
) -> IdeaProgressResponse:
    idea = IdeaService(session).get_idea(idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")

    matrices = _latest_for_idea(session, RelatedWorkMatrix, idea_id, 20)
    drafts = _latest_for_idea(session, ProposalDraft, idea_id, 20)
    reviews = _latest_for_idea(session, ProposalReview, idea_id, 50)
    revisions = _latest_for_idea(session, ProposalRevision, idea_id, 50)
    experiment_runs = _latest_for_idea(session, ExperimentRun, idea_id, 50)
    experiment_analyses = _latest_for_idea(session, ExperimentAnalysis, idea_id, 50)
    decision_memos = _latest_for_idea(session, IdeaDecisionMemo, idea_id, 20)
    tasks = _latest_for_idea(session, ResearchTask, idea_id, 200)
    snapshots = _latest_for_idea(session, TaskBoardSnapshot, idea_id, 20)

    latest_analysis = experiment_analyses[0] if experiment_analyses else None
    analysis_tasks = [
        task
        for task in tasks
        if latest_analysis
        and task.owner_type == "experiment_analysis"
        and task.owner_id == latest_analysis.id
    ]
    artifact_counts = {
        "related_work_matrices": len(matrices),
        "proposal_drafts": len(drafts),
        "proposal_reviews": len(reviews),
        "proposal_revisions": len(revisions),
        "experiment_runs": len(experiment_runs),
        "experiment_analyses": len(experiment_analyses),
        "decision_memos": len(decision_memos),
        "research_tasks": len(tasks),
        "open_tasks": len([task for task in tasks if task.status in {"todo", "doing", "blocked"}]),
        "blocked_tasks": len([task for task in tasks if task.status == "blocked"]),
        "analysis_follow_up_tasks": len(analysis_tasks),
        "task_board_snapshots": len(snapshots),
    }
    latest_artifacts = _progress_latest_artifacts(
        matrices,
        drafts,
        reviews,
        revisions,
        experiment_runs,
        experiment_analyses,
        decision_memos,
        snapshots,
    )
    task_summary = _progress_task_summary(tasks)
    experiment_summary = _progress_experiment_summary(experiment_runs, experiment_analyses)
    blockers = _progress_blockers(tasks, latest_analysis)
    recommended_next_step = _progress_recommendation(
        artifact_counts=artifact_counts,
        latest_artifacts=latest_artifacts,
        task_summary=task_summary,
        blockers=blockers,
    )
    markdown_export = _render_idea_progress_markdown(
        idea=idea,
        artifact_counts=artifact_counts,
        latest_artifacts=latest_artifacts,
        task_summary=task_summary,
        experiment_summary=experiment_summary,
        blockers=blockers,
        recommended_next_step=recommended_next_step,
    )
    return IdeaProgressResponse(
        idea=_serialize_idea(idea),
        artifact_counts=artifact_counts,
        latest_artifacts=latest_artifacts,
        task_summary=task_summary,
        experiment_summary=experiment_summary,
        blockers=blockers,
        recommended_next_step=recommended_next_step,
        markdown_export=markdown_export,
        message=f"Loaded progress summary for idea {idea.id}.",
    )


def _latest_for_idea(session: Session, model, idea_id: str, limit: int) -> list:
    return (
        session.query(model)
        .filter(model.idea_id == idea_id)
        .order_by(model.created_at.desc())
        .limit(limit)
        .all()
    )


def _progress_latest_artifacts(
    matrices: list[RelatedWorkMatrix],
    drafts: list[ProposalDraft],
    reviews: list[ProposalReview],
    revisions: list[ProposalRevision],
    experiment_runs: list[ExperimentRun],
    experiment_analyses: list[ExperimentAnalysis],
    decision_memos: list[IdeaDecisionMemo],
    snapshots: list[TaskBoardSnapshot],
) -> dict[str, dict | None]:
    latest_run = experiment_runs[0] if experiment_runs else None
    latest_analysis = experiment_analyses[0] if experiment_analyses else None
    latest_memo = decision_memos[0] if decision_memos else None
    return {
        "related_work_matrix": {"id": matrices[0].id, "status": matrices[0].status}
        if matrices
        else None,
        "proposal_draft": {"id": drafts[0].id, "status": drafts[0].status} if drafts else None,
        "proposal_review": {
            "id": reviews[0].id,
            "decision": reviews[0].decision,
            "readiness_score": reviews[0].readiness_score,
        }
        if reviews
        else None,
        "proposal_revision": {"id": revisions[0].id, "status": revisions[0].status}
        if revisions
        else None,
        "experiment_run": {"id": latest_run.id, "status": latest_run.status}
        if latest_run
        else None,
        "experiment_analysis": {
            "id": latest_analysis.id,
            "decision": latest_analysis.decision,
            "confidence": latest_analysis.confidence,
        }
        if latest_analysis
        else None,
        "decision_memo": {"id": latest_memo.id, "decision": latest_memo.decision}
        if latest_memo
        else None,
        "task_board_snapshot": {"id": snapshots[0].id, "title": snapshots[0].title}
        if snapshots
        else None,
    }


def _progress_task_summary(tasks: list[ResearchTask]) -> dict:
    by_status = Counter(task.status for task in tasks)
    by_priority = Counter(task.priority for task in tasks)
    next_tasks = sorted(
        [task for task in tasks if task.status in {"todo", "doing", "blocked"}],
        key=_progress_task_order,
    )[:8]
    return {
        "by_status": dict(by_status),
        "by_priority": dict(by_priority),
        "next_tasks": [
            {
                "id": task.id,
                "title": task.title,
                "priority": task.priority,
                "status": task.status,
                "owner_type": task.owner_type,
            }
            for task in next_tasks
        ],
    }


def _progress_task_order(task: ResearchTask) -> tuple[int, int, str]:
    priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    status_rank = {"blocked": 0, "doing": 1, "todo": 2, "done": 3, "archived": 4}
    return (
        priority_rank.get(task.priority, 9),
        status_rank.get(task.status, 9),
        task.created_at.isoformat(),
    )


def _progress_experiment_summary(
    experiment_runs: list[ExperimentRun],
    experiment_analyses: list[ExperimentAnalysis],
) -> dict:
    latest_run = experiment_runs[0] if experiment_runs else None
    latest_analysis = experiment_analyses[0] if experiment_analyses else None
    return {
        "latest_run_status": latest_run.status if latest_run else "",
        "latest_run_id": latest_run.id if latest_run else "",
        "latest_analysis_decision": latest_analysis.decision if latest_analysis else "",
        "latest_analysis_confidence": latest_analysis.confidence if latest_analysis else 0.0,
        "latest_analysis_next_actions": latest_analysis.next_actions_json
        if latest_analysis
        else [],
        "latest_analysis_concerns": latest_analysis.concerns_json if latest_analysis else [],
    }


def _progress_blockers(
    tasks: list[ResearchTask],
    latest_analysis: ExperimentAnalysis | None,
) -> list[dict[str, str]]:
    blockers = [
        {
            "type": "task",
            "id": task.id,
            "title": task.title,
            "reason": task.description,
        }
        for task in tasks
        if task.status == "blocked"
    ]
    if latest_analysis:
        blockers.extend(
            {
                "type": "analysis_concern",
                "id": latest_analysis.id,
                "title": latest_analysis.decision,
                "reason": concern,
            }
            for concern in latest_analysis.concerns_json or []
        )
    return blockers[:20]


def _progress_recommendation(
    *,
    artifact_counts: dict[str, int],
    latest_artifacts: dict[str, dict | None],
    task_summary: dict,
    blockers: list[dict[str, str]],
) -> str:
    if artifact_counts["related_work_matrices"] == 0:
        return "Build a related-work matrix before investing more execution effort."
    if artifact_counts["proposal_drafts"] == 0:
        return "Draft a proposal to make the idea reviewable."
    if artifact_counts["proposal_reviews"] == 0:
        return "Run a proposal readiness review."
    if artifact_counts["proposal_revisions"] == 0:
        return "Create a proposal revision from the latest review."
    if artifact_counts["research_tasks"] == 0:
        return "Generate a task backlog from the latest proposal revision."
    if artifact_counts["experiment_runs"] == 0:
        return "Record the first experiment run for the latest experiment plan."
    if artifact_counts["experiment_analyses"] == 0:
        return "Analyze the latest experiment run to decide the next research move."
    if (
        latest_artifacts.get("experiment_analysis")
        and artifact_counts["analysis_follow_up_tasks"] == 0
    ):
        return "Create follow-up tasks from the latest experiment analysis."
    if artifact_counts["experiment_analyses"] and artifact_counts["decision_memos"] == 0:
        return "Create a decision memo to record whether this idea should be pursued, revised, parked, or rejected."
    if blockers:
        return "Resolve blockers or analysis concerns before expanding the scope."
    next_tasks = task_summary.get("next_tasks") or []
    if next_tasks:
        return f"Work the highest-priority open task: {next_tasks[0]['title']}"
    return "Archive this iteration or ingest new literature to refresh the portfolio."


def _render_idea_progress_markdown(
    *,
    idea: Idea,
    artifact_counts: dict[str, int],
    latest_artifacts: dict[str, dict | None],
    task_summary: dict,
    experiment_summary: dict,
    blockers: list[dict[str, str]],
    recommended_next_step: str,
) -> str:
    lines = [
        f"# Idea Progress: {idea.title}",
        "",
        f"- Idea ID: `{idea.id}`",
        f"- Status: {idea.status}",
        "",
        "## Artifact Counts",
        "",
    ]
    lines.extend([f"- {key}: {value}" for key, value in artifact_counts.items()])
    lines.extend(["", "## Latest Artifacts", ""])
    for key, value in latest_artifacts.items():
        lines.append(f"- {key}: {value if value else 'none'}")
    lines.extend(["", "## Task Summary", ""])
    lines.append(f"- By Status: {task_summary.get('by_status', {})}")
    lines.append(f"- By Priority: {task_summary.get('by_priority', {})}")
    lines.extend(["", "## Next Tasks", ""])
    next_tasks = task_summary.get("next_tasks") or []
    if next_tasks:
        for task in next_tasks:
            lines.append(
                f"- `{task['id']}` `{task['priority']}` `{task['status']}` {task['title']}"
            )
    else:
        lines.append("- No open tasks.")
    lines.extend(["", "## Experiment Summary", ""])
    for key, value in experiment_summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Blockers And Concerns", ""])
    if blockers:
        for blocker in blockers:
            lines.append(
                f"- `{blocker['type']}` `{blocker['id']}` {blocker['title']}: {blocker['reason']}"
            )
    else:
        lines.append("- No blockers or analysis concerns.")
    lines.extend(["", "## Recommended Next Step", "", recommended_next_step])
    return "\n".join(lines).strip() + "\n"


@router.post("/ideas/{idea_id}/decision-memo", response_model=IdeaDecisionMemoRead)
def create_idea_decision_memo(
    idea_id: str,
    payload: IdeaDecisionMemoCreate,
    session: Session = Depends(get_session),
) -> IdeaDecisionMemoRead:
    try:
        memo = IdeaDecisionMemoService(session).create_memo(
            idea_id,
            decision=payload.decision,
            rationale=payload.rationale,
            evidence_ids=payload.evidence_ids,
            risks=payload.risks,
            next_commitments=payload.next_commitments,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize_idea_decision_memo(memo)


@router.get("/ideas/{idea_id}/decision-memos", response_model=list[IdeaDecisionMemoRead])
def list_idea_decision_memos(
    idea_id: str,
    limit: int = 20,
    session: Session = Depends(get_session),
) -> list[IdeaDecisionMemoRead]:
    try:
        memos = IdeaDecisionMemoService(session).list_for_idea(idea_id, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_serialize_idea_decision_memo(memo) for memo in memos]


@router.get("/ideas/{idea_id}/decision-memos/{memo_id}", response_model=IdeaDecisionMemoRead)
def get_idea_decision_memo(
    idea_id: str,
    memo_id: str,
    session: Session = Depends(get_session),
) -> IdeaDecisionMemoRead:
    memo = IdeaDecisionMemoService(session).get_memo(idea_id, memo_id)
    if memo is None:
        raise HTTPException(status_code=404, detail="Idea decision memo not found")
    return _serialize_idea_decision_memo(memo)


@router.get(
    "/ideas/{idea_id}/decision-memos/{memo_id}/export/markdown",
    response_class=PlainTextResponse,
)
def export_idea_decision_memo_markdown(
    idea_id: str,
    memo_id: str,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    memo = IdeaDecisionMemoService(session).get_memo(idea_id, memo_id)
    if memo is None:
        raise HTTPException(status_code=404, detail="Idea decision memo not found")
    return PlainTextResponse(memo.markdown_export or "", media_type="text/markdown")


def _graph_edge_summary(session: Session, canonical_keys: list[str]) -> dict[str, int]:
    if not canonical_keys:
        return {}
    nodes = (
        session.query(ResearchNode)
        .filter(ResearchNode.canonical_key.in_(canonical_keys))
        .limit(500)
        .all()
    )
    node_ids = {node.id for node in nodes}
    if not node_ids:
        return {}
    edge_types = [
        "idea_has_proposal_draft",
        "proposal_review_reviews_draft",
        "proposal_revision_updates_draft",
        "proposal_revision_addresses_review",
        "proposal_revision_creates_task",
        "task_board_snapshot_tracks_task",
        "idea_has_experiment_plan",
        "experiment_plan_has_run",
        "idea_has_experiment_run",
        "task_records_experiment_run",
        "experiment_run_has_analysis",
        "idea_has_experiment_analysis",
        "task_records_experiment_analysis",
        "experiment_analysis_creates_task",
        "idea_has_decision_memo",
    ]
    edges = (
        session.query(ResearchEdge)
        .filter(ResearchEdge.edge_type.in_(edge_types))
        .order_by(ResearchEdge.created_at.desc())
        .limit(2000)
        .all()
    )
    summary: dict[str, int] = {}
    for edge in edges:
        if edge.source_node_id in node_ids or edge.target_node_id in node_ids:
            summary[edge.edge_type] = summary.get(edge.edge_type, 0) + 1
    return summary


def _render_idea_lineage_markdown(
    *,
    idea: Idea,
    matrices: list[RelatedWorkMatrix],
    drafts: list[ProposalDraft],
    reviews: list[ProposalReview],
    revisions: list[ProposalRevision],
    experiment_runs: list[ExperimentRun],
    experiment_analyses: list[ExperimentAnalysis],
    decision_memos: list[IdeaDecisionMemo],
    tasks: list[ResearchTask],
    snapshots: list[TaskBoardSnapshot],
    graph_edge_summary: dict[str, int],
) -> str:
    lines = [
        f"# Idea Lineage: {idea.title}",
        "",
        f"- Idea ID: `{idea.id}`",
        f"- Related Work Matrices: {len(matrices)}",
        f"- Proposal Drafts: {len(drafts)}",
        f"- Proposal Reviews: {len(reviews)}",
        f"- Proposal Revisions: {len(revisions)}",
        f"- Experiment Runs: {len(experiment_runs)}",
        f"- Experiment Analyses: {len(experiment_analyses)}",
        f"- Decision Memos: {len(decision_memos)}",
        f"- Research Tasks: {len(tasks)}",
        f"- Task Board Snapshots: {len(snapshots)}",
        "",
        "## Graph Edge Summary",
        "",
    ]
    if graph_edge_summary:
        lines.extend(
            [f"- `{edge_type}`: {count}" for edge_type, count in graph_edge_summary.items()]
        )
    else:
        lines.append("- No proposal artifact graph edges found.")

    lines.extend(["", "## Latest Proposal Artifacts", ""])
    for draft in drafts[:3]:
        lines.append(f"- Draft `{draft.id}`: {draft.title}")
    for review in reviews[:3]:
        lines.append(f"- Review `{review.id}`: {review.decision} score={review.readiness_score}")
    for revision in revisions[:3]:
        lines.append(f"- Revision `{revision.id}`: {revision.status}")

    lines.extend(["", "## Experiment Runs", ""])
    if experiment_runs:
        for run in experiment_runs[:5]:
            lines.append(f"- `{run.id}` `{run.status}` {run.title}")
    else:
        lines.append("- No experiment runs recorded yet.")

    lines.extend(["", "## Experiment Analyses", ""])
    if experiment_analyses:
        for analysis in experiment_analyses[:5]:
            lines.append(
                f"- `{analysis.id}` `{analysis.decision}` confidence={analysis.confidence:.2f}"
            )
    else:
        lines.append("- No experiment analyses recorded yet.")

    lines.extend(["", "## Decision Memos", ""])
    if decision_memos:
        for memo in decision_memos[:5]:
            lines.append(f"- `{memo.id}` `{memo.decision}` by {memo.created_by}")
    else:
        lines.append("- No decision memos recorded yet.")

    lines.extend(["", "## Next Tasks", ""])
    next_tasks = [task for task in tasks if task.status in {"todo", "doing", "blocked"}][:10]
    if next_tasks:
        for task in next_tasks:
            lines.append(f"- `{task.id}` `{task.priority}` `{task.status}` {task.title}")
    else:
        lines.append("- No open tasks found.")
    return "\n".join(lines).strip() + "\n"


@router.post("/ideas/{idea_id}/related-work-matrix", response_model=RelatedWorkMatrixRead)
def create_related_work_matrix(
    idea_id: str,
    payload: RelatedWorkMatrixCreate,
    session: Session = Depends(get_session),
) -> RelatedWorkMatrixRead:
    try:
        matrix = RelatedWorkService(session).create_matrix(
            idea_id,
            include_external=payload.include_external,
            limit=payload.limit,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return _serialize_related_work_matrix(matrix)


@router.get("/ideas/{idea_id}/related-work-matrices", response_model=list[RelatedWorkMatrixRead])
def list_related_work_matrices(
    idea_id: str,
    limit: int = 20,
    session: Session = Depends(get_session),
) -> list[RelatedWorkMatrixRead]:
    try:
        matrices = RelatedWorkService(session).list_for_idea(idea_id, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_serialize_related_work_matrix(matrix) for matrix in matrices]


@router.get(
    "/ideas/{idea_id}/related-work-matrices/{matrix_id}",
    response_model=RelatedWorkMatrixRead,
)
def get_related_work_matrix(
    idea_id: str,
    matrix_id: str,
    session: Session = Depends(get_session),
) -> RelatedWorkMatrixRead:
    matrix = RelatedWorkService(session).get_matrix(idea_id, matrix_id)
    if matrix is None:
        raise HTTPException(status_code=404, detail="Related work matrix not found")
    return _serialize_related_work_matrix(matrix)


@router.get(
    "/ideas/{idea_id}/related-work-matrices/{matrix_id}/export/markdown",
    response_class=PlainTextResponse,
)
def export_related_work_matrix_markdown(
    idea_id: str,
    matrix_id: str,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    matrix = RelatedWorkService(session).get_matrix(idea_id, matrix_id)
    if matrix is None:
        raise HTTPException(status_code=404, detail="Related work matrix not found")
    return PlainTextResponse(matrix.markdown_export or "", media_type="text/markdown")


@router.post("/ideas/{idea_id}/proposal-draft", response_model=ProposalDraftRead)
def create_proposal_draft(
    idea_id: str,
    payload: ProposalDraftCreate,
    session: Session = Depends(get_session),
) -> ProposalDraftRead:
    try:
        draft = ProposalDraftService(session).create_draft(
            idea_id,
            related_work_matrix_id=payload.related_work_matrix_id,
            experiment_plan_id=payload.experiment_plan_id,
            include_latest_related_work=payload.include_latest_related_work,
            include_latest_experiment_plan=payload.include_latest_experiment_plan,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return _serialize_proposal_draft(draft)


@router.get("/ideas/{idea_id}/proposal-drafts", response_model=list[ProposalDraftRead])
def list_proposal_drafts(
    idea_id: str,
    limit: int = 20,
    session: Session = Depends(get_session),
) -> list[ProposalDraftRead]:
    try:
        drafts = ProposalDraftService(session).list_for_idea(idea_id, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_serialize_proposal_draft(draft) for draft in drafts]


@router.get("/ideas/{idea_id}/proposal-drafts/{draft_id}", response_model=ProposalDraftRead)
def get_proposal_draft(
    idea_id: str,
    draft_id: str,
    session: Session = Depends(get_session),
) -> ProposalDraftRead:
    draft = ProposalDraftService(session).get_draft(idea_id, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Proposal draft not found")
    return _serialize_proposal_draft(draft)


@router.get(
    "/ideas/{idea_id}/proposal-drafts/{draft_id}/export/markdown",
    response_class=PlainTextResponse,
)
def export_proposal_draft_markdown(
    idea_id: str,
    draft_id: str,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    draft = ProposalDraftService(session).get_draft(idea_id, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Proposal draft not found")
    return PlainTextResponse(draft.markdown_export or "", media_type="text/markdown")


@router.post(
    "/ideas/{idea_id}/proposal-drafts/{draft_id}/review",
    response_model=ProposalReviewRead,
)
def create_proposal_review(
    idea_id: str,
    draft_id: str,
    payload: ProposalReviewCreate,
    session: Session = Depends(get_session),
) -> ProposalReviewRead:
    draft = ProposalDraftService(session).get_draft(idea_id, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Proposal draft not found")
    try:
        review = ProposalReviewService(session).create_review(
            draft.id,
            reviewer_type=payload.reviewer_type,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize_proposal_review(review)


@router.get(
    "/ideas/{idea_id}/proposal-drafts/{draft_id}/reviews",
    response_model=list[ProposalReviewRead],
)
def list_proposal_reviews(
    idea_id: str,
    draft_id: str,
    limit: int = 20,
    session: Session = Depends(get_session),
) -> list[ProposalReviewRead]:
    if ProposalDraftService(session).get_draft(idea_id, draft_id) is None:
        raise HTTPException(status_code=404, detail="Proposal draft not found")
    try:
        reviews = ProposalReviewService(session).list_for_draft(draft_id, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_serialize_proposal_review(review) for review in reviews]


@router.get(
    "/ideas/{idea_id}/proposal-drafts/{draft_id}/reviews/{review_id}",
    response_model=ProposalReviewRead,
)
def get_proposal_review(
    idea_id: str,
    draft_id: str,
    review_id: str,
    session: Session = Depends(get_session),
) -> ProposalReviewRead:
    if ProposalDraftService(session).get_draft(idea_id, draft_id) is None:
        raise HTTPException(status_code=404, detail="Proposal draft not found")
    review = ProposalReviewService(session).get_review(draft_id, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Proposal review not found")
    return _serialize_proposal_review(review)


@router.get(
    "/ideas/{idea_id}/proposal-drafts/{draft_id}/reviews/{review_id}/export/markdown",
    response_class=PlainTextResponse,
)
def export_proposal_review_markdown(
    idea_id: str,
    draft_id: str,
    review_id: str,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    if ProposalDraftService(session).get_draft(idea_id, draft_id) is None:
        raise HTTPException(status_code=404, detail="Proposal draft not found")
    review = ProposalReviewService(session).get_review(draft_id, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Proposal review not found")
    return PlainTextResponse(review.markdown_export or "", media_type="text/markdown")


@router.post(
    "/ideas/{idea_id}/proposal-drafts/{draft_id}/revise",
    response_model=ProposalRevisionRead,
)
def create_proposal_revision(
    idea_id: str,
    draft_id: str,
    payload: ProposalRevisionCreate,
    session: Session = Depends(get_session),
) -> ProposalRevisionRead:
    draft = ProposalDraftService(session).get_draft(idea_id, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Proposal draft not found")
    try:
        revision = ProposalRevisionService(session).create_revision(
            draft.id,
            proposal_review_id=payload.proposal_review_id,
            include_latest_review=payload.include_latest_review,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return _serialize_proposal_revision(revision)


@router.get(
    "/ideas/{idea_id}/proposal-drafts/{draft_id}/revisions",
    response_model=list[ProposalRevisionRead],
)
def list_proposal_revisions(
    idea_id: str,
    draft_id: str,
    limit: int = 20,
    session: Session = Depends(get_session),
) -> list[ProposalRevisionRead]:
    if ProposalDraftService(session).get_draft(idea_id, draft_id) is None:
        raise HTTPException(status_code=404, detail="Proposal draft not found")
    try:
        revisions = ProposalRevisionService(session).list_for_draft(draft_id, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_serialize_proposal_revision(revision) for revision in revisions]


@router.get(
    "/ideas/{idea_id}/proposal-drafts/{draft_id}/revisions/{revision_id}",
    response_model=ProposalRevisionRead,
)
def get_proposal_revision(
    idea_id: str,
    draft_id: str,
    revision_id: str,
    session: Session = Depends(get_session),
) -> ProposalRevisionRead:
    if ProposalDraftService(session).get_draft(idea_id, draft_id) is None:
        raise HTTPException(status_code=404, detail="Proposal draft not found")
    revision = ProposalRevisionService(session).get_revision(draft_id, revision_id)
    if revision is None:
        raise HTTPException(status_code=404, detail="Proposal revision not found")
    return _serialize_proposal_revision(revision)


@router.get(
    "/ideas/{idea_id}/proposal-drafts/{draft_id}/revisions/{revision_id}/export/markdown",
    response_class=PlainTextResponse,
)
def export_proposal_revision_markdown(
    idea_id: str,
    draft_id: str,
    revision_id: str,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    if ProposalDraftService(session).get_draft(idea_id, draft_id) is None:
        raise HTTPException(status_code=404, detail="Proposal draft not found")
    revision = ProposalRevisionService(session).get_revision(draft_id, revision_id)
    if revision is None:
        raise HTTPException(status_code=404, detail="Proposal revision not found")
    return PlainTextResponse(revision.markdown_export or "", media_type="text/markdown")


@router.post(
    "/ideas/{idea_id}/proposal-drafts/{draft_id}/revisions/{revision_id}/tasks",
    response_model=ResearchTaskGenerationResponse,
)
def create_tasks_from_proposal_revision(
    idea_id: str,
    draft_id: str,
    revision_id: str,
    payload: ResearchTaskGenerateRequest,
    session: Session = Depends(get_session),
) -> ResearchTaskGenerationResponse:
    if ProposalDraftService(session).get_draft(idea_id, draft_id) is None:
        raise HTTPException(status_code=404, detail="Proposal draft not found")
    revision = ProposalRevisionService(session).get_revision(draft_id, revision_id)
    if revision is None:
        raise HTTPException(status_code=404, detail="Proposal revision not found")
    tasks = ResearchTaskService(session).create_from_proposal_revision(
        revision.id,
        created_by=payload.created_by,
    )
    return ResearchTaskGenerationResponse(
        tasks=[_serialize_research_task(task) for task in tasks],
        message=f"Created {len(tasks)} research tasks from proposal revision {revision.id}.",
    )


@router.get("/tasks", response_model=list[ResearchTaskRead])
def list_research_tasks(
    idea_id: str | None = None,
    owner_type: str | None = None,
    status: str | None = None,
    limit: int = 100,
    session: Session = Depends(get_session),
) -> list[ResearchTaskRead]:
    tasks = ResearchTaskService(session).list_tasks(
        idea_id=idea_id,
        owner_type=owner_type,
        status=status,
        limit=limit,
    )
    return [_serialize_research_task(task) for task in tasks]


@router.post("/tasks/snapshots", response_model=TaskBoardSnapshotDetail)
def create_task_board_snapshot(
    payload: TaskBoardSnapshotCreate,
    session: Session = Depends(get_session),
) -> TaskBoardSnapshotDetail:
    snapshot = TaskBoardService(session).create_snapshot(
        title=payload.title,
        idea_id=payload.idea_id,
        owner_type=payload.owner_type,
        statuses=payload.statuses,
        created_by=payload.created_by,
    )
    return _serialize_task_board_snapshot(snapshot, include_markdown=True)


@router.get("/tasks/snapshots", response_model=list[TaskBoardSnapshotRead])
def list_task_board_snapshots(
    limit: int = 50,
    session: Session = Depends(get_session),
) -> list[TaskBoardSnapshotRead]:
    snapshots = TaskBoardService(session).list_snapshots(limit)
    return [_serialize_task_board_snapshot(snapshot) for snapshot in snapshots]


@router.get("/tasks/snapshots/{snapshot_id}", response_model=TaskBoardSnapshotDetail)
def get_task_board_snapshot(
    snapshot_id: str,
    session: Session = Depends(get_session),
) -> TaskBoardSnapshotDetail:
    snapshot = TaskBoardService(session).get_snapshot(snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Task board snapshot not found")
    return _serialize_task_board_snapshot(snapshot, include_markdown=True)


@router.get(
    "/tasks/snapshots/{snapshot_id}/export/markdown",
    response_class=PlainTextResponse,
)
def export_task_board_snapshot_markdown(
    snapshot_id: str,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    snapshot = TaskBoardService(session).get_snapshot(snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Task board snapshot not found")
    return PlainTextResponse(snapshot.markdown_export or "", media_type="text/markdown")


@router.get("/tasks/{task_id}", response_model=ResearchTaskRead)
def get_research_task(
    task_id: str,
    session: Session = Depends(get_session),
) -> ResearchTaskRead:
    task = ResearchTaskService(session).get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")
    return _serialize_research_task(task)


@router.post("/tasks/{task_id}/events", response_model=ResearchTaskEventRead)
def create_research_task_event(
    task_id: str,
    payload: ResearchTaskEventCreate,
    session: Session = Depends(get_session),
) -> ResearchTaskEventRead:
    try:
        event = ResearchTaskService(session).create_event(
            task_id,
            event_type=payload.event_type,
            note=payload.note,
            metadata=payload.metadata,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize_research_task_event(event)


@router.get("/tasks/{task_id}/events", response_model=list[ResearchTaskEventRead])
def list_research_task_events(
    task_id: str,
    limit: int = 50,
    session: Session = Depends(get_session),
) -> list[ResearchTaskEventRead]:
    try:
        events = ResearchTaskService(session).list_events(task_id, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_serialize_research_task_event(event) for event in events]


@router.patch("/tasks/{task_id}", response_model=ResearchTaskRead)
def update_research_task(
    task_id: str,
    payload: ResearchTaskUpdate,
    session: Session = Depends(get_session),
) -> ResearchTaskRead:
    try:
        task = ResearchTaskService(session).update_task(
            task_id,
            status=payload.status,
            priority=payload.priority,
            description=payload.description,
            note=payload.note,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize_research_task(task)


@router.post("/ideas/{idea_id}/feedback", response_model=IdeaFeedbackRead)
def create_idea_feedback(
    idea_id: str,
    payload: IdeaFeedbackCreate,
    session: Session = Depends(get_session),
) -> IdeaFeedbackRead:
    try:
        feedback = IdeaFeedbackService(session).create_feedback(
            idea_id,
            decision=payload.decision,
            rating=payload.rating,
            comment=payload.comment,
            tags=payload.tags,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize_feedback(feedback)


@router.get("/ideas/{idea_id}/feedback", response_model=list[IdeaFeedbackRead])
def list_idea_feedback(
    idea_id: str,
    session: Session = Depends(get_session),
) -> list[IdeaFeedbackRead]:
    try:
        feedback_items = IdeaFeedbackService(session).list_feedback_for_idea(idea_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_serialize_feedback(feedback) for feedback in feedback_items]


@router.post("/ideas/{idea_id}/refine", response_model=IdeaRefinementResponse)
def refine_idea(
    idea_id: str,
    payload: IdeaRefinementRequest,
    session: Session = Depends(get_session),
) -> IdeaRefinementResponse:
    try:
        result = IdeaRefinementService(session).refine_idea(
            idea_id,
            focus=payload.focus,
            preserve_evidence=payload.preserve_evidence,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return IdeaRefinementResponse(
        source_idea=_serialize_idea(result.source_idea),
        refined_idea=_serialize_idea(result.refined_idea),
        applied_actions=result.applied_actions,
        message=(
            f"Created refined idea version {result.refined_idea.version} "
            f"from source idea {result.source_idea.id}."
        ),
    )


def _serialize_novelty_check(check) -> NoveltyCheckRead:
    return NoveltyCheckRead(
        id=check.id,
        idea_id=check.idea_id,
        status=check.status,
        risk_level=check.risk_level,
        summary=check.summary,
        local_overlap_score=check.local_overlap_score,
        external_overlap_score=check.external_overlap_score,
        collision_signals=check.collision_signals_json or [],
        missing_searches=check.missing_searches_json or [],
        recommended_actions=check.recommended_actions_json or [],
        checked_sources=check.checked_sources_json or [],
        created_at=check.created_at,
        updated_at=check.updated_at,
    )


@router.post("/ideas/{idea_id}/novelty-check", response_model=NoveltyCheckRead)
def create_idea_novelty_check(
    idea_id: str,
    include_external: bool = True,
    session: Session = Depends(get_session),
) -> NoveltyCheckRead:
    try:
        check = NoveltyService(session).create_check(
            idea_id,
            include_external_literature=include_external,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize_novelty_check(check)


@router.get("/ideas/{idea_id}/novelty-checks", response_model=list[NoveltyCheckRead])
def list_idea_novelty_checks(
    idea_id: str,
    session: Session = Depends(get_session),
) -> list[NoveltyCheckRead]:
    if IdeaService(session).get_idea(idea_id) is None:
        raise HTTPException(status_code=404, detail="Idea not found")
    return [
        _serialize_novelty_check(check)
        for check in NoveltyService(session).list_checks_for_idea(idea_id)
    ]


@router.get(
    "/ideas/{idea_id}/export/markdown",
    response_class=PlainTextResponse,
)
def export_idea_markdown(
    idea_id: str,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    try:
        markdown = ExportService(session).render_idea_markdown(idea_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PlainTextResponse(markdown, media_type="text/markdown")


def _serialize_review(review) -> ReviewRead:
    return ReviewRead(
        id=review.id,
        idea_id=review.idea_id,
        reviewer_type=review.reviewer_type,
        summary=review.summary,
        major_concerns=review.major_concerns_json or [],
        minor_concerns=review.minor_concerns_json or [],
        required_experiments=review.required_experiments_json or [],
        decision=review.decision,
        action_items=review.action_items_json or [],
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


@router.post("/ideas/{idea_id}/review", response_model=ReviewRead)
def review_idea(idea_id: str, session: Session = Depends(get_session)) -> ReviewRead:
    try:
        review = ReviewService(session).create_review(idea_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize_review(review)


@router.get("/ideas/{idea_id}/reviews", response_model=list[ReviewRead])
def list_idea_reviews(idea_id: str, session: Session = Depends(get_session)) -> list[ReviewRead]:
    if IdeaService(session).get_idea(idea_id) is None:
        raise HTTPException(status_code=404, detail="Idea not found")
    return [
        _serialize_review(review)
        for review in ReviewService(session).list_reviews_for_idea(idea_id)
    ]


def _serialize_experiment_plan(plan) -> ExperimentPlanRead:
    return ExperimentPlanRead(
        id=plan.id,
        idea_id=plan.idea_id,
        objective=plan.objective,
        hypothesis=plan.hypothesis,
        datasets=plan.datasets_json or [],
        baselines=plan.baselines_json or [],
        metrics=plan.metrics_json or [],
        main_experiment=plan.main_experiment_json or {},
        ablation_studies=plan.ablation_studies_json or [],
        robustness_tests=plan.robustness_tests_json or [],
        expected_tables=plan.expected_tables_json or [],
        failure_modes=plan.failure_modes_json or [],
        fallback_plan=plan.fallback_plan,
        compute_requirements=plan.compute_requirements,
        timeline=plan.timeline_json or {},
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


def _serialize_experiment_run(run: ExperimentRun) -> ExperimentRunRead:
    return ExperimentRunRead(
        id=run.id,
        experiment_plan_id=run.experiment_plan_id,
        idea_id=run.idea_id,
        task_id=run.task_id,
        title=run.title,
        status=run.status,
        objective_snapshot=run.objective_snapshot,
        hypothesis_snapshot=run.hypothesis_snapshot,
        dataset_snapshot=run.dataset_snapshot,
        baseline_snapshot=run.baseline_snapshot_json or [],
        parameters=run.parameters_json or {},
        metric_results=run.metric_results_json or {},
        artifact_links=run.artifact_links_json or [],
        conclusion=run.conclusion,
        notes=run.notes,
        markdown_export=run.markdown_export or "",
        created_by=run.created_by,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _serialize_experiment_analysis(analysis: ExperimentAnalysis) -> ExperimentAnalysisRead:
    return ExperimentAnalysisRead(
        id=analysis.id,
        experiment_run_id=analysis.experiment_run_id,
        experiment_plan_id=analysis.experiment_plan_id,
        idea_id=analysis.idea_id,
        task_id=analysis.task_id,
        decision=analysis.decision,
        confidence=analysis.confidence,
        metric_interpretation=analysis.metric_interpretation_json or {},
        key_findings=analysis.key_findings_json or [],
        concerns=analysis.concerns_json or [],
        next_actions=analysis.next_actions_json or [],
        markdown_export=analysis.markdown_export or "",
        created_by=analysis.created_by,
        created_at=analysis.created_at,
        updated_at=analysis.updated_at,
    )


@router.post("/ideas/{idea_id}/experiment-plan", response_model=ExperimentPlanRead)
def create_experiment_plan(
    idea_id: str,
    session: Session = Depends(get_session),
) -> ExperimentPlanRead:
    try:
        plan = ExperimentService(session).create_plan(idea_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize_experiment_plan(plan)


@router.get("/ideas/{idea_id}/experiment-plans", response_model=list[ExperimentPlanRead])
def list_experiment_plans(
    idea_id: str,
    session: Session = Depends(get_session),
) -> list[ExperimentPlanRead]:
    if IdeaService(session).get_idea(idea_id) is None:
        raise HTTPException(status_code=404, detail="Idea not found")
    return [
        _serialize_experiment_plan(plan)
        for plan in ExperimentService(session).list_plans_for_idea(idea_id)
    ]


@router.post("/experiment-plans/{plan_id}/runs", response_model=ExperimentRunRead)
def create_experiment_run(
    plan_id: str,
    payload: ExperimentRunCreate,
    session: Session = Depends(get_session),
) -> ExperimentRunRead:
    try:
        run = ExperimentRunService(session).create_run(
            plan_id,
            title=payload.title,
            task_id=payload.task_id,
            status=payload.status,
            dataset_snapshot=payload.dataset_snapshot,
            parameters=payload.parameters,
            metric_results=payload.metric_results,
            artifact_links=payload.artifact_links,
            conclusion=payload.conclusion,
            notes=payload.notes,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return _serialize_experiment_run(run)


@router.get("/experiment-plans/{plan_id}/runs", response_model=list[ExperimentRunRead])
def list_experiment_runs_for_plan(
    plan_id: str,
    limit: int = 50,
    session: Session = Depends(get_session),
) -> list[ExperimentRunRead]:
    try:
        runs = ExperimentRunService(session).list_for_plan(plan_id, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_serialize_experiment_run(run) for run in runs]


@router.get("/ideas/{idea_id}/experiment-runs", response_model=list[ExperimentRunRead])
def list_experiment_runs_for_idea(
    idea_id: str,
    limit: int = 50,
    session: Session = Depends(get_session),
) -> list[ExperimentRunRead]:
    try:
        runs = ExperimentRunService(session).list_for_idea(idea_id, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_serialize_experiment_run(run) for run in runs]


@router.get("/experiment-runs/{run_id}", response_model=ExperimentRunRead)
def get_experiment_run(
    run_id: str,
    session: Session = Depends(get_session),
) -> ExperimentRunRead:
    run = ExperimentRunService(session).get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Experiment run not found")
    return _serialize_experiment_run(run)


@router.patch("/experiment-runs/{run_id}", response_model=ExperimentRunRead)
def update_experiment_run(
    run_id: str,
    payload: ExperimentRunUpdate,
    session: Session = Depends(get_session),
) -> ExperimentRunRead:
    try:
        run = ExperimentRunService(session).update_run(
            run_id,
            status=payload.status,
            dataset_snapshot=payload.dataset_snapshot,
            parameters=payload.parameters,
            metric_results=payload.metric_results,
            artifact_links=payload.artifact_links,
            conclusion=payload.conclusion,
            notes=payload.notes,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize_experiment_run(run)


@router.get(
    "/experiment-runs/{run_id}/export/markdown",
    response_class=PlainTextResponse,
)
def export_experiment_run_markdown(
    run_id: str,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    run = ExperimentRunService(session).get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Experiment run not found")
    return PlainTextResponse(run.markdown_export or "", media_type="text/markdown")


@router.post("/experiment-runs/{run_id}/analysis", response_model=ExperimentAnalysisRead)
def create_experiment_analysis(
    run_id: str,
    payload: ExperimentAnalysisCreate,
    session: Session = Depends(get_session),
) -> ExperimentAnalysisRead:
    try:
        analysis = ExperimentAnalysisService(session).create_analysis(
            run_id,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize_experiment_analysis(analysis)


@router.get("/experiment-runs/{run_id}/analyses", response_model=list[ExperimentAnalysisRead])
def list_experiment_analyses_for_run(
    run_id: str,
    limit: int = 50,
    session: Session = Depends(get_session),
) -> list[ExperimentAnalysisRead]:
    try:
        analyses = ExperimentAnalysisService(session).list_for_run(run_id, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_serialize_experiment_analysis(analysis) for analysis in analyses]


@router.get("/ideas/{idea_id}/experiment-analyses", response_model=list[ExperimentAnalysisRead])
def list_experiment_analyses_for_idea(
    idea_id: str,
    limit: int = 50,
    session: Session = Depends(get_session),
) -> list[ExperimentAnalysisRead]:
    try:
        analyses = ExperimentAnalysisService(session).list_for_idea(idea_id, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_serialize_experiment_analysis(analysis) for analysis in analyses]


@router.get("/experiment-analyses/{analysis_id}", response_model=ExperimentAnalysisRead)
def get_experiment_analysis(
    analysis_id: str,
    session: Session = Depends(get_session),
) -> ExperimentAnalysisRead:
    analysis = ExperimentAnalysisService(session).get_analysis(analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Experiment analysis not found")
    return _serialize_experiment_analysis(analysis)


@router.get(
    "/experiment-analyses/{analysis_id}/export/markdown",
    response_class=PlainTextResponse,
)
def export_experiment_analysis_markdown(
    analysis_id: str,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    analysis = ExperimentAnalysisService(session).get_analysis(analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Experiment analysis not found")
    return PlainTextResponse(analysis.markdown_export or "", media_type="text/markdown")


@router.post(
    "/experiment-analyses/{analysis_id}/tasks",
    response_model=ResearchTaskGenerationResponse,
)
def create_tasks_from_experiment_analysis(
    analysis_id: str,
    payload: ResearchTaskGenerateRequest,
    session: Session = Depends(get_session),
) -> ResearchTaskGenerationResponse:
    try:
        tasks = ResearchTaskService(session).create_from_experiment_analysis(
            analysis_id,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ResearchTaskGenerationResponse(
        tasks=[_serialize_research_task(task) for task in tasks],
        message=f"Created {len(tasks)} research tasks from experiment analysis {analysis_id}.",
    )


@router.post(
    "/workflows/literature-to-ideas",
    response_model=LiteratureToIdeasWorkflowResponse,
)
def run_literature_to_ideas_workflow(
    payload: LiteratureToIdeasWorkflowRequest,
    session: Session = Depends(get_session),
) -> LiteratureToIdeasWorkflowResponse:
    try:
        result = WorkflowService(session).run_literature_to_ideas(
            paper_id=payload.paper_id,
            max_gaps=payload.max_gaps,
            max_ideas_per_gap=payload.max_ideas_per_gap,
            run_review=payload.run_review,
            run_novelty_check=payload.run_novelty_check,
            run_experiment_plan=payload.run_experiment_plan,
            include_markdown_export=payload.include_markdown_export,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    paper = result.paper
    return LiteratureToIdeasWorkflowResponse(
        job_id=result.job.id,
        paper=_serialize_paper(paper),
        card=_serialize_card(result.card),
        gaps=[_serialize_gap(gap) for gap in result.gaps],
        ideas=[_serialize_idea(idea) for idea in result.ideas],
        novelty_checks=[_serialize_novelty_check(check) for check in result.novelty_checks],
        reviews=[_serialize_review(review) for review in result.reviews],
        experiment_plans=[_serialize_experiment_plan(plan) for plan in result.experiment_plans],
        markdown_export=result.markdown_export,
        message=(
            "Completed literature-to-ideas workflow: "
            f"{len(result.gaps)} gaps, {len(result.ideas)} ideas, "
            f"{len(result.novelty_checks)} novelty checks, {len(result.reviews)} reviews, "
            f"{len(result.experiment_plans)} experiment plans."
        ),
    )


@router.post("/workflows/literature-to-ideas/async", response_model=JobRead)
def queue_literature_to_ideas_workflow(
    payload: LiteratureToIdeasWorkflowRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> JobRead:
    if session.get(Paper, payload.paper_id) is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    job = WorkflowService(session).queue_literature_to_ideas(
        paper_id=payload.paper_id,
        max_gaps=payload.max_gaps,
        max_ideas_per_gap=payload.max_ideas_per_gap,
        run_review=payload.run_review,
        run_novelty_check=payload.run_novelty_check,
        run_experiment_plan=payload.run_experiment_plan,
        include_markdown_export=payload.include_markdown_export,
    )
    background_tasks.add_task(run_literature_to_ideas_job_background, job.id)
    return _serialize_job(job)


@router.post("/search/context", response_model=ContextSearchResponse)
def search_research_context(
    payload: ContextSearchRequest,
    session: Session = Depends(get_session),
) -> ContextSearchResponse:
    try:
        result = RetrievalService(session).search_context(
            query=payload.query,
            paper_ids=payload.paper_ids,
            limit=payload.limit,
            include_graph=payload.include_graph,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ContextSearchResponse(
        query=payload.query,
        retrieval_method="lexical_vector_graph_rag_lite_v0",
        answer_brief=result.answer_brief,
        evidences=[
            ScoredEvidenceRead(
                evidence=_serialize_evidence(scored.item),
                score=scored.score,
                matched_terms=scored.matched_terms,
            )
            for scored in result.evidences
        ],
        gaps=[
            ScoredResearchGapRead(
                gap=_serialize_gap(scored.item),
                score=scored.score,
                matched_terms=scored.matched_terms,
            )
            for scored in result.gaps
        ],
        ideas=[
            ScoredIdeaRead(
                idea=_serialize_idea(scored.item),
                score=scored.score,
                matched_terms=scored.matched_terms,
            )
            for scored in result.ideas
        ],
        graph_nodes=[_serialize_node(node) for node in result.graph_nodes],
        graph_edges=[_serialize_edge(edge) for edge in result.graph_edges],
    )


def _serialize_node(node) -> ResearchNodeRead:
    return ResearchNodeRead(
        id=node.id,
        node_type=node.node_type,
        label=node.label,
        canonical_key=node.canonical_key,
        payload=node.payload_json or {},
        created_at=node.created_at,
        updated_at=node.updated_at,
    )


def _serialize_edge(edge) -> ResearchEdgeRead:
    return ResearchEdgeRead(
        id=edge.id,
        source_node_id=edge.source_node_id,
        target_node_id=edge.target_node_id,
        edge_type=edge.edge_type,
        weight=edge.weight,
        evidence_ids=edge.evidence_ids_json or [],
        payload=edge.payload_json or {},
        created_at=edge.created_at,
        updated_at=edge.updated_at,
    )


@router.get("/graph/nodes", response_model=list[ResearchNodeRead])
def list_graph_nodes(
    node_type: str | None = None,
    limit: int = 100,
    session: Session = Depends(get_session),
) -> list[ResearchNodeRead]:
    return [_serialize_node(node) for node in GraphService(session).list_nodes(node_type, limit)]


@router.get("/graph/edges", response_model=list[ResearchEdgeRead])
def list_graph_edges(
    edge_type: str | None = None,
    limit: int = 100,
    session: Session = Depends(get_session),
) -> list[ResearchEdgeRead]:
    return [_serialize_edge(edge) for edge in GraphService(session).list_edges(edge_type, limit)]
