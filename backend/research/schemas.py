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
    parent_idea_id: str | None = None
    created_at: datetime
    updated_at: datetime


class IdeaGenerationResponse(BaseModel):
    ideas: list[IdeaRead]
    message: str


class IdeaRefinementRequest(BaseModel):
    focus: str = ""
    preserve_evidence: bool = True


class IdeaRefinementResponse(BaseModel):
    source_idea: IdeaRead
    refined_idea: IdeaRead
    applied_actions: list[str] = Field(default_factory=list)
    message: str


class IdeaRankingRequest(BaseModel):
    idea_ids: list[str] = Field(default_factory=list)
    gap_ids: list[str] = Field(default_factory=list)
    paper_ids: list[str] = Field(default_factory=list)
    limit: int = 10
    weights: dict[str, float] = Field(default_factory=dict)
    include_refined: bool = True
    deduplicate_lineage: bool = True


class RankedIdeaRead(BaseModel):
    rank: int
    idea: IdeaRead
    weighted_score: float
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    rationale: list[str] = Field(default_factory=list)


class IdeaRankingResponse(BaseModel):
    ranked_ideas: list[RankedIdeaRead] = Field(default_factory=list)
    message: str


class IdeaPortfolioExportRequest(IdeaRankingRequest):
    title: str = "Research Idea Portfolio"


class IdeaPortfolioSnapshotCreate(IdeaPortfolioExportRequest):
    description: str = ""
    created_by: str = "researcher"


class IdeaPortfolioSnapshotRead(BaseModel):
    id: str
    title: str
    description: str = ""
    ranking_request: dict[str, Any] = Field(default_factory=dict)
    idea_ids: list[str] = Field(default_factory=list)
    ranked_items: list[dict[str, Any]] = Field(default_factory=list)
    markdown_export_chars: int = 0
    created_by: str = "researcher"
    created_at: datetime
    updated_at: datetime


class IdeaPortfolioSnapshotDetail(IdeaPortfolioSnapshotRead):
    markdown_export: str = ""


class IdeaPortfolioComparisonRequest(BaseModel):
    baseline_snapshot_id: str
    candidate_snapshot_id: str


class IdeaPortfolioComparisonResponse(BaseModel):
    baseline_snapshot_id: str
    candidate_snapshot_id: str
    baseline_title: str
    candidate_title: str
    added_idea_ids: list[str] = Field(default_factory=list)
    removed_idea_ids: list[str] = Field(default_factory=list)
    kept_idea_ids: list[str] = Field(default_factory=list)
    rank_changes: list[dict[str, Any]] = Field(default_factory=list)
    summary: str
    markdown_export: str = ""


class RelatedWorkMatrixCreate(BaseModel):
    include_external: bool = True
    limit: int = 8
    created_by: str = "system"


class RelatedWorkMatrixItem(BaseModel):
    source_type: str
    source_id: str
    title: str
    overlap_score: float = 0.0
    shared_terms: list[str] = Field(default_factory=list)
    relevance: str = ""
    differentiator: str = ""
    url: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class RelatedWorkMatrixRead(BaseModel):
    id: str
    idea_id: str
    status: str
    query: str
    items: list[RelatedWorkMatrixItem] = Field(default_factory=list)
    differentiators: list[str] = Field(default_factory=list)
    missing_searches: list[str] = Field(default_factory=list)
    checked_sources: list[str] = Field(default_factory=list)
    summary: str = ""
    markdown_export: str = ""
    created_by: str = "system"
    created_at: datetime
    updated_at: datetime


class ProposalDraftCreate(BaseModel):
    related_work_matrix_id: str | None = None
    experiment_plan_id: str | None = None
    include_latest_related_work: bool = True
    include_latest_experiment_plan: bool = True
    created_by: str = "system"


class ProposalDraftRead(BaseModel):
    id: str
    idea_id: str
    status: str
    title: str
    abstract: str = ""
    problem_statement: str = ""
    novelty_statement: str = ""
    related_work_summary: str = ""
    method_summary: str = ""
    experiment_summary: str = ""
    risk_mitigation: str = ""
    milestone_plan: list[dict[str, Any]] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    related_work_matrix_id: str | None = None
    experiment_plan_id: str | None = None
    markdown_export: str = ""
    created_by: str = "system"
    created_at: datetime
    updated_at: datetime


class ProposalReviewCreate(BaseModel):
    reviewer_type: str = "advisor"
    created_by: str = "system"


class ProposalReviewRead(BaseModel):
    id: str
    proposal_draft_id: str
    idea_id: str
    reviewer_type: str = "advisor"
    decision: str
    readiness_score: float = 0.0
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    required_revisions: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    summary: str = ""
    markdown_export: str = ""
    created_by: str = "system"
    created_at: datetime
    updated_at: datetime


class ProposalRevisionCreate(BaseModel):
    proposal_review_id: str | None = None
    include_latest_review: bool = True
    created_by: str = "system"


class ProposalRevisionRead(BaseModel):
    id: str
    proposal_draft_id: str
    proposal_review_id: str | None = None
    idea_id: str
    status: str
    revision_summary: str = ""
    applied_revisions: list[str] = Field(default_factory=list)
    missing_evidence_actions: list[str] = Field(default_factory=list)
    revised_sections: dict[str, Any] = Field(default_factory=dict)
    markdown_export: str = ""
    created_by: str = "system"
    created_at: datetime
    updated_at: datetime


class ResearchTaskGenerateRequest(BaseModel):
    created_by: str = "system"


class ResearchTaskUpdate(BaseModel):
    status: Literal["todo", "doing", "blocked", "done", "archived"] | None = None
    priority: Literal["low", "medium", "high", "critical"] | None = None
    description: str | None = None
    note: str = ""
    created_by: str = "system"


class ResearchTaskRead(BaseModel):
    id: str
    idea_id: str | None = None
    owner_type: str
    owner_id: str
    source_type: str = ""
    source_id: str = ""
    title: str
    description: str = ""
    priority: str = "medium"
    status: str = "todo"
    due_phase: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_by: str = "system"
    created_at: datetime
    updated_at: datetime


class ResearchTaskEventCreate(BaseModel):
    event_type: Literal["note", "progress", "blocker", "decision", "evidence"] = "note"
    note: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_by: str = "system"


class ResearchTaskEventRead(BaseModel):
    id: str
    task_id: str
    idea_id: str | None = None
    event_type: str
    status_from: str = ""
    status_to: str = ""
    priority_from: str = ""
    priority_to: str = ""
    note: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_by: str = "system"
    created_at: datetime
    updated_at: datetime


class ResearchTaskGenerationResponse(BaseModel):
    tasks: list[ResearchTaskRead] = Field(default_factory=list)
    message: str


class TaskBoardSnapshotCreate(BaseModel):
    title: str = "Research Task Board"
    idea_id: str | None = None
    owner_type: str = ""
    statuses: list[str] = Field(default_factory=list)
    created_by: str = "system"


class TaskBoardSnapshotRead(BaseModel):
    id: str
    title: str
    idea_id: str | None = None
    owner_type: str = ""
    status_filter: list[str] = Field(default_factory=list)
    task_ids: list[str] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    markdown_export_chars: int = 0
    created_by: str = "system"
    created_at: datetime
    updated_at: datetime


class TaskBoardSnapshotDetail(TaskBoardSnapshotRead):
    markdown_export: str = ""


class ExperimentRunCreate(BaseModel):
    title: str = ""
    task_id: str | None = None
    status: Literal["planned", "running", "completed", "failed", "inconclusive"] = "running"
    dataset_snapshot: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    metric_results: dict[str, Any] = Field(default_factory=dict)
    artifact_links: list[dict[str, Any]] = Field(default_factory=list)
    conclusion: str = ""
    notes: str = ""
    created_by: str = "system"


class ExperimentRunUpdate(BaseModel):
    status: Literal["planned", "running", "completed", "failed", "inconclusive"] | None = None
    dataset_snapshot: str | None = None
    parameters: dict[str, Any] | None = None
    metric_results: dict[str, Any] | None = None
    artifact_links: list[dict[str, Any]] | None = None
    conclusion: str | None = None
    notes: str | None = None
    created_by: str = "system"


class ExperimentRunRead(BaseModel):
    id: str
    experiment_plan_id: str
    idea_id: str
    task_id: str | None = None
    title: str
    status: str
    objective_snapshot: str = ""
    hypothesis_snapshot: str = ""
    dataset_snapshot: str = ""
    baseline_snapshot: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    metric_results: dict[str, Any] = Field(default_factory=dict)
    artifact_links: list[dict[str, Any]] = Field(default_factory=list)
    conclusion: str = ""
    notes: str = ""
    markdown_export: str = ""
    created_by: str = "system"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ExperimentAnalysisCreate(BaseModel):
    created_by: str = "system"


class ExperimentAnalysisRead(BaseModel):
    id: str
    experiment_run_id: str
    experiment_plan_id: str
    idea_id: str
    task_id: str | None = None
    decision: str
    confidence: float = 0.0
    metric_interpretation: dict[str, Any] = Field(default_factory=dict)
    key_findings: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    markdown_export: str = ""
    created_by: str = "system"
    created_at: datetime
    updated_at: datetime


class IdeaLineageResponse(BaseModel):
    idea: IdeaRead
    related_work_matrices: list[RelatedWorkMatrixRead] = Field(default_factory=list)
    proposal_drafts: list[ProposalDraftRead] = Field(default_factory=list)
    proposal_reviews: list[ProposalReviewRead] = Field(default_factory=list)
    proposal_revisions: list[ProposalRevisionRead] = Field(default_factory=list)
    experiment_runs: list[ExperimentRunRead] = Field(default_factory=list)
    experiment_analyses: list[ExperimentAnalysisRead] = Field(default_factory=list)
    research_tasks: list[ResearchTaskRead] = Field(default_factory=list)
    task_board_snapshots: list[TaskBoardSnapshotRead] = Field(default_factory=list)
    graph_edge_summary: dict[str, int] = Field(default_factory=dict)
    markdown_export: str = ""
    message: str


class IdeaFeedbackCreate(BaseModel):
    decision: Literal["shortlist", "accept", "revise", "reject", "archive"] = "revise"
    rating: float | None = None
    comment: str = ""
    tags: list[str] = Field(default_factory=list)
    created_by: str = "researcher"


class IdeaFeedbackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    idea_id: str
    decision: str
    rating: float | None = None
    comment: str = ""
    tags: list[str] = Field(default_factory=list)
    created_by: str = "researcher"
    created_at: datetime
    updated_at: datetime


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


class NoveltyCheckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    idea_id: str
    status: str
    risk_level: str
    summary: str
    local_overlap_score: float | None = None
    external_overlap_score: float | None = None
    collision_signals: list[dict[str, Any]] = Field(default_factory=list)
    missing_searches: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    checked_sources: list[str] = Field(default_factory=list)
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
    run_novelty_check: bool = True
    run_review: bool = True
    run_experiment_plan: bool = True
    include_markdown_export: bool = True


class LiteratureToIdeasWorkflowResponse(BaseModel):
    job_id: str = ""
    paper: PaperRead
    card: PaperCardRead
    gaps: list[ResearchGapRead]
    ideas: list[IdeaRead]
    novelty_checks: list[NoveltyCheckRead] = Field(default_factory=list)
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


class ContextSearchRequest(BaseModel):
    query: str
    paper_ids: list[str] = Field(default_factory=list)
    limit: int = 8
    include_graph: bool = True


class ScoredEvidenceRead(BaseModel):
    evidence: EvidenceRead
    score: float
    matched_terms: list[str] = Field(default_factory=list)


class ScoredResearchGapRead(BaseModel):
    gap: ResearchGapRead
    score: float
    matched_terms: list[str] = Field(default_factory=list)


class ScoredIdeaRead(BaseModel):
    idea: IdeaRead
    score: float
    matched_terms: list[str] = Field(default_factory=list)


class ContextSearchResponse(BaseModel):
    query: str
    retrieval_method: str
    answer_brief: str
    evidences: list[ScoredEvidenceRead]
    gaps: list[ScoredResearchGapRead]
    ideas: list[ScoredIdeaRead]
    graph_nodes: list[ResearchNodeRead] = Field(default_factory=list)
    graph_edges: list[ResearchEdgeRead] = Field(default_factory=list)


class LiteratureSearchRequest(BaseModel):
    query: str
    limit: int = 8
    include_external: bool = False


class LiteratureSearchItem(BaseModel):
    provider: str
    source_id: str = ""
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    url: str = ""
    abstract: str = ""
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class LiteratureSearchResponse(BaseModel):
    query: str
    local_status: str
    external_status: str
    items: list[LiteratureSearchItem]
    message: str


class EmbeddingRebuildRequest(BaseModel):
    owner_types: list[str] = Field(default_factory=lambda: ["evidence", "gap", "idea"])
    paper_ids: list[str] = Field(default_factory=list)
    limit: int = 500


class EmbeddingRebuildResponse(BaseModel):
    model: str
    dimension: int
    indexed_count: int
    evidence_count: int
    gap_count: int
    idea_count: int
    message: str


class JobRead(BaseModel):
    id: str
    job_type: str
    status: Literal["pending", "running", "completed", "failed"]
    progress: float = 0.0
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


class JobArtifactsResponse(BaseModel):
    job: JobRead
    paper: PaperRead | None = None
    card: PaperCardRead | None = None
    gaps: list[ResearchGapRead] = Field(default_factory=list)
    ideas: list[IdeaRead] = Field(default_factory=list)
    novelty_checks: list[NoveltyCheckRead] = Field(default_factory=list)
    reviews: list[ReviewRead] = Field(default_factory=list)
    experiment_plans: list[ExperimentPlanRead] = Field(default_factory=list)
    markdown_export: str = ""
    message: str


class ProjectStatus(BaseModel):
    service: str
    phase: str
    graph_rag_lite_enabled: bool
    mcp_enabled: bool
    implemented_capabilities: list[str]
    next_capabilities: list[str]
