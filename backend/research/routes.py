from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.research.config import settings
from backend.research.db import get_session
from backend.research.schemas import PaperCreate, PaperRead, ProjectStatus
from backend.research.services.paper_service import PaperService


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
