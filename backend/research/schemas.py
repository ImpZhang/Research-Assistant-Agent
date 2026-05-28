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


class PaperCardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    paper_id: str
    payload: PaperCardPayload
    extraction_model: str = ""
    extraction_status: str
    created_at: datetime
    updated_at: datetime


class ResearchGapCreate(BaseModel):
    title: str
    description: str
    gap_type: str
    source_paper_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class GapMiningRequest(BaseModel):
    paper_ids: list[str] = Field(default_factory=list)
    max_gaps: int = 10


class ResearchGapRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    gap_type: str
    source_paper_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    why_important: str = ""
    why_unsolved: str = ""
    possible_approaches: list[str] = Field(default_factory=list)
    feasibility_score: float | None = None
    novelty_score: float | None = None
    risk_level: str = ""
    status: str
    created_at: datetime
    updated_at: datetime


class GapMiningResponse(BaseModel):
    gaps: list[ResearchGapRead]
    message: str


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


class IdeaGenerationRequest(BaseModel):
    gap_ids: list[str] = Field(default_factory=list)
    max_ideas_per_gap: int = 2


class IdeaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
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
    score: IdeaScore = Field(default_factory=IdeaScore)
    status: str
    version: int
    created_at: datetime
    updated_at: datetime


class IdeaGenerationResponse(BaseModel):
    ideas: list[IdeaRead]
    message: str


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    idea_id: str
    reviewer_type: str
    summary: str
    major_concerns: list[str] = Field(default_factory=list)
    minor_concerns: list[str] = Field(default_factory=list)
    required_experiments: list[str] = Field(default_factory=list)
    decision: str
    action_items: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ExperimentPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    idea_id: str
    objective: str
    hypothesis: str
    datasets: list[str] = Field(default_factory=list)
    baselines: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    main_experiment: dict[str, Any] = Field(default_factory=dict)
    ablation_studies: list[dict[str, Any]] = Field(default_factory=list)
    robustness_tests: list[dict[str, Any]] = Field(default_factory=list)
    expected_tables: list[dict[str, Any]] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)
    fallback_plan: str = ""
    compute_requirements: str = ""
    timeline: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class LiteratureToIdeasWorkflowRequest(BaseModel):
    paper_id: str
    max_gaps: int = 4
    max_ideas_per_gap: int = 2
    run_review: bool = True
    run_experiment_plan: bool = True
    include_markdown_export: bool = True


class LiteratureToIdeasWorkflowResponse(BaseModel):
    paper: PaperRead
    card: PaperCardRead
    gaps: list[ResearchGapRead]
    ideas: list[IdeaRead]
    reviews: list[ReviewRead] = Field(default_factory=list)
    experiment_plans: list[ExperimentPlanRead] = Field(default_factory=list)
    markdown_export: str = ""
    message: str


class ResearchNodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    node_type: str
    label: str
    canonical_key: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ResearchEdgeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_node_id: str
    target_node_id: str
    edge_type: str
    weight: float = 1.0
    evidence_ids: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


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
