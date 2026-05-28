from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    service: str


class PaperCreate(BaseModel):
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    filename: str = ""
    file_path: str = ""
    domain: str = ""
    task: str = ""


class PaperRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    filename: str = ""
    domain: str = ""
    task: str = ""
    status: str
    created_at: datetime
    updated_at: datetime


class PaperDetail(PaperRead):
    section_count: int = 0
    chunk_count: int = 0
    evidence_count: int = 0


class PaperUploadResponse(BaseModel):
    paper: PaperRead
    section_count: int
    chunk_count: int
    evidence_count: int
    message: str


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    paper_id: str
    evidence_type: str
    text: str
    summary: str = ""
    supports: str = ""
    confidence: float = 0.0
    page_number: int | None = None


class PaperCardFieldItem(BaseModel):
    text: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class PaperCardPayload(BaseModel):
    problem: list[PaperCardFieldItem] = Field(default_factory=list)
    motivation: list[PaperCardFieldItem] = Field(default_factory=list)
    contributions: list[PaperCardFieldItem] = Field(default_factory=list)
    method: list[PaperCardFieldItem] = Field(default_factory=list)
    datasets: list[PaperCardFieldItem] = Field(default_factory=list)
    metrics: list[PaperCardFieldItem] = Field(default_factory=list)
    baselines: list[PaperCardFieldItem] = Field(default_factory=list)
    results: list[PaperCardFieldItem] = Field(default_factory=list)
    limitations: list[PaperCardFieldItem] = Field(default_factory=list)
    future_work: list[PaperCardFieldItem] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    open_questions: list[PaperCardFieldItem] = Field(default_factory=list)


class ResearchGapCreate(BaseModel):
    title: str
    description: str
    gap_type: str
    source_paper_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class IdeaScore(BaseModel):
    novelty: float | None = None
    feasibility: float | None = None
    impact: float | None = None
    evidence_support: float | None = None
    experimental_verifiability: float | None = None
    resource_cost: float | None = None
    publication_potential: float | None = None
    overall_score: float | None = None
    rationale: str = ""


class IdeaCreate(BaseModel):
    title: str
    research_question: str
    core_hypothesis: str
    motivation: str = ""
    related_gap_ids: list[str] = Field(default_factory=list)
    related_paper_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    method_sketch: str = ""
    expected_contribution: str = ""
    novelty_argument: str = ""
    datasets: list[str] = Field(default_factory=list)
    baselines: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    resource_requirements: str = ""
    target_venues: list[str] = Field(default_factory=list)


class JobRead(BaseModel):
    id: str
    job_type: str
    status: Literal["pending", "running", "completed", "failed"]
    progress: float = 0.0
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


class ProjectStatus(BaseModel):
    service: str
    phase: str
    graph_rag_lite_enabled: bool
    mcp_enabled: bool
    implemented_capabilities: list[str]
    next_capabilities: list[str]
