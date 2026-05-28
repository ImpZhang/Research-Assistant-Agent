from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.research.config import settings
from backend.research.db import get_session
from backend.research.models import Chunk, Evidence, Paper, PaperSection
from backend.research.schemas import (
    EvidenceRead,
    ExperimentPlanRead,
    GapMiningRequest,
    GapMiningResponse,
    IdeaGenerationRequest,
    IdeaGenerationResponse,
    IdeaRead,
    IdeaScore,
    PaperCreate,
    PaperCardPayload,
    PaperCardRead,
    PaperDetail,
    PaperRead,
    PaperUploadResponse,
    ProjectStatus,
    ResearchGapRead,
    ReviewRead,
)
from backend.research.services.document_ingestion import DocumentIngestionService
from backend.research.services.experiment_service import ExperimentService
from backend.research.services.gap_service import GapService
from backend.research.services.idea_service import IdeaService
from backend.research.services.paper_card_service import PaperCardService
from backend.research.services.paper_service import PaperService
from backend.research.services.review_service import ReviewService


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
            "graph_rag_lite_schema",
            "requirements_and_technical_docs",
        ],
        next_capabilities=[
            "document_ingestion_graph",
            "paper_card_extraction",
            "evidence_extraction",
            "evidence_vector_index",
        ],
    )


@router.get("/papers", response_model=list[PaperRead])
def list_papers(session: Session = Depends(get_session)) -> list[PaperRead]:
    papers = PaperService(session).list_papers()
    return [
        PaperRead(
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
        for paper in papers
    ]


@router.get("/papers/{paper_id}", response_model=PaperDetail)
def get_paper(paper_id: str, session: Session = Depends(get_session)) -> PaperDetail:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    return PaperDetail(
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
        section_count=session.query(PaperSection).filter(PaperSection.paper_id == paper_id).count(),
        chunk_count=session.query(Chunk).filter(Chunk.paper_id == paper_id).count(),
        evidence_count=session.query(Evidence).filter(Evidence.paper_id == paper_id).count(),
    )


@router.post("/papers", response_model=PaperRead)
def create_paper(payload: PaperCreate, session: Session = Depends(get_session)) -> PaperRead:
    paper = PaperService(session).create_paper(payload)
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
        paper=PaperRead(
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
        ),
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


def _serialize_card(card) -> PaperCardRead:
    return PaperCardRead(
        id=card.id,
        paper_id=card.paper_id,
        payload=PaperCardPayload(
            problem=card.problem_json.get("items", []) if card.problem_json else [],
            motivation=card.motivation_json.get("items", []) if card.motivation_json else [],
            contributions=card.contributions_json.get("items", []) if card.contributions_json else [],
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
        created_at=idea.created_at,
        updated_at=idea.updated_at,
    )


@router.post("/ideas/generate", response_model=IdeaGenerationResponse)
def generate_ideas(
    payload: IdeaGenerationRequest,
    session: Session = Depends(get_session),
) -> IdeaGenerationResponse:
    ideas = IdeaService(session).generate_from_gaps(payload.gap_ids, payload.max_ideas_per_gap)
    return IdeaGenerationResponse(
        ideas=[_serialize_idea(idea) for idea in ideas],
        message=f"Generated {len(ideas)} research ideas from selected gaps.",
    )


@router.post("/gaps/{gap_id}/ideas", response_model=IdeaGenerationResponse)
def generate_ideas_for_gap(
    gap_id: str,
    session: Session = Depends(get_session),
) -> IdeaGenerationResponse:
    if GapService(session).get_gap(gap_id) is None:
        raise HTTPException(status_code=404, detail="Research gap not found")
    ideas = IdeaService(session).generate_from_gaps([gap_id], 2)
    return IdeaGenerationResponse(
        ideas=[_serialize_idea(idea) for idea in ideas],
        message=f"Generated {len(ideas)} research ideas from gap {gap_id}.",
    )


@router.get("/ideas", response_model=list[IdeaRead])
def list_ideas(session: Session = Depends(get_session)) -> list[IdeaRead]:
    return [_serialize_idea(idea) for idea in IdeaService(session).list_ideas()]


@router.get("/ideas/{idea_id}", response_model=IdeaRead)
def get_idea(idea_id: str, session: Session = Depends(get_session)) -> IdeaRead:
    idea = IdeaService(session).get_idea(idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")
    return _serialize_idea(idea)


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
    return [_serialize_review(review) for review in ReviewService(session).list_reviews_for_idea(idea_id)]


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
