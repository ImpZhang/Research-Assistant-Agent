from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from backend.research.config import settings
from backend.research.db import get_session
from backend.research.models import (
    Chunk,
    Evidence,
    ExperimentPlan,
    Idea,
    IdeaFeedback,
    Job,
    NoveltyCheck,
    Paper,
    PaperCard,
    PaperSection,
    ResearchGap,
    Review,
)
from backend.research.schemas import (
    ContextSearchRequest,
    ContextSearchResponse,
    EmbeddingRebuildRequest,
    EmbeddingRebuildResponse,
    EvidenceRead,
    ExperimentPlanRead,
    GapMiningRequest,
    GapMiningResponse,
    IdeaFeedbackCreate,
    IdeaFeedbackRead,
    IdeaGenerationRequest,
    IdeaGenerationResponse,
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
    ProjectStatus,
    RankedIdeaRead,
    ResearchEdgeRead,
    ResearchGapRead,
    ResearchNodeRead,
    ReviewRead,
    ScoredEvidenceRead,
    ScoredIdeaRead,
    ScoredResearchGapRead,
)
from backend.research.services.document_ingestion import DocumentIngestionService
from backend.research.services.embedding_service import EmbeddingService
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
from backend.research.services.retrieval_service import RetrievalService
from backend.research.services.review_service import ReviewService
from backend.research.services.structured_extraction_service import StructuredExtractionService
from backend.research.services.structured_idea_service import StructuredIdeaService
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
            "human_idea_feedback",
            "local_novelty_collision_check",
            "literature_backed_novelty_screening",
            "reviewer_simulation",
            "experiment_planning",
            "literature_to_ideas_workflow",
            "async_literature_to_ideas_workflow",
            "workflow_job_trace",
            "workflow_job_artifact_snapshot",
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


@router.get("/ideas/{idea_id}", response_model=IdeaRead)
def get_idea(idea_id: str, session: Session = Depends(get_session)) -> IdeaRead:
    idea = IdeaService(session).get_idea(idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")
    return _serialize_idea(idea)


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
