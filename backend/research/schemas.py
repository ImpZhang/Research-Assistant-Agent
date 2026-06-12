from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    service: str


class ResearchProfileUpdate(BaseModel):
    name: str = "Default Research Profile"
    primary_domains: list[str] = Field(default_factory=list)
    active_questions: list[str] = Field(default_factory=list)
    target_venues: list[str] = Field(default_factory=list)
    methodological_preferences: list[str] = Field(default_factory=list)
    resource_constraints: list[str] = Field(default_factory=list)
    risk_tolerance: Literal["low", "medium", "high"] = "medium"
    timeline_horizon: str = ""
    negative_preferences: list[str] = Field(default_factory=list)
    evaluation_weights: dict[str, float] = Field(default_factory=dict)
    notes: str = ""
    created_by: str = "researcher"


class ResearchProfileRead(BaseModel):
    id: str = "default"
    name: str = "Default Research Profile"
    primary_domains: list[str] = Field(default_factory=list)
    active_questions: list[str] = Field(default_factory=list)
    target_venues: list[str] = Field(default_factory=list)
    methodological_preferences: list[str] = Field(default_factory=list)
    resource_constraints: list[str] = Field(default_factory=list)
    risk_tolerance: str = "medium"
    timeline_horizon: str = ""
    negative_preferences: list[str] = Field(default_factory=list)
    evaluation_weights: dict[str, float] = Field(default_factory=dict)
    notes: str = ""
    markdown_export: str = ""
    created_by: str = "researcher"
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProjectSetupWizardRequest(ResearchProfileUpdate):
    customer_context: str = ""
    success_criteria: list[str] = Field(default_factory=list)
    first_milestone: str = ""


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


class OpportunityRadarTaskGenerateRequest(BaseModel):
    limit: int = 5
    actions_per_opportunity: int = 2
    created_by: str = "system"


class ClaimValidationQueueTaskGenerateRequest(BaseModel):
    idea_id: str | None = None
    limit: int = 5
    priority_filter: list[Literal["critical", "high", "medium", "low"]] = Field(
        default_factory=lambda: ["critical", "high"]
    )
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


class ClaimValidationResultCreate(BaseModel):
    validation_status: Literal[
        "supported",
        "challenged",
        "needs_more_evidence",
        "inconclusive",
    ] = "inconclusive"
    evidence_ids: list[str] = Field(default_factory=list)
    notes: str = ""
    next_action: str = ""
    mark_task_done: bool = True
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
    task_ids: list[str] = Field(default_factory=list)
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


class IdeaDecisionMemoCreate(BaseModel):
    decision: Literal["pursue", "revise", "park", "reject"] = "revise"
    rationale: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    next_commitments: list[str] = Field(default_factory=list)
    created_by: str = "researcher"


class IdeaDecisionMemoRead(BaseModel):
    id: str
    idea_id: str
    decision: str
    rationale: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    risk_register: list[str] = Field(default_factory=list)
    next_commitments: list[str] = Field(default_factory=list)
    source_artifacts: dict[str, Any] = Field(default_factory=dict)
    markdown_export: str = ""
    created_by: str = "researcher"
    created_at: datetime
    updated_at: datetime


class IdeaAssumptionAuditCreate(BaseModel):
    assumptions: list[dict[str, Any]] = Field(default_factory=list)
    created_by: str = "system"


class IdeaAssumptionAuditRead(BaseModel):
    id: str
    idea_id: str
    status: str
    assumptions: list[dict[str, Any]] = Field(default_factory=list)
    source_artifacts: dict[str, Any] = Field(default_factory=dict)
    markdown_export: str = ""
    created_by: str = "system"
    created_at: datetime
    updated_at: datetime


class IdeaEvidenceLedgerCreate(BaseModel):
    claims: list[str] = Field(default_factory=list)
    created_by: str = "system"


class IdeaEvidenceLedgerRead(BaseModel):
    id: str
    idea_id: str
    status: str
    claims: list[dict[str, Any]] = Field(default_factory=list)
    evidence_links: list[dict[str, Any]] = Field(default_factory=list)
    counterevidence: list[dict[str, Any]] = Field(default_factory=list)
    missing_evidence: list[dict[str, Any]] = Field(default_factory=list)
    risk_register: list[dict[str, Any]] = Field(default_factory=list)
    source_artifacts: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    coverage_score: float = 0.0
    markdown_export: str = ""
    created_by: str = "system"
    created_at: datetime
    updated_at: datetime


class IdeaClaimValidationPacketResponse(BaseModel):
    idea: "IdeaRead"
    ledger: IdeaEvidenceLedgerRead
    claim: dict[str, Any] = Field(default_factory=dict)
    supporting_evidence: list[EvidenceRead] = Field(default_factory=list)
    evidence_links: list[dict[str, Any]] = Field(default_factory=list)
    counterevidence: list[dict[str, Any]] = Field(default_factory=list)
    missing_evidence: list[dict[str, Any]] = Field(default_factory=list)
    related_tasks: list[ResearchTaskRead] = Field(default_factory=list)
    validation_actions: list[str] = Field(default_factory=list)
    graph_edge_summary: dict[str, int] = Field(default_factory=dict)
    markdown_export: str = ""
    message: str


class ClaimValidationQueueItem(BaseModel):
    idea: "IdeaRead"
    ledger_id: str
    ledger_created_at: datetime
    claim_id: str
    claim: str
    claim_type: str = ""
    support_level: str = ""
    priority: str = "medium"
    urgency_score: float = 0.0
    supporting_evidence_count: int = 0
    missing_evidence_count: int = 0
    counterevidence_count: int = 0
    related_task_count: int = 0
    next_validation: str = ""
    recommended_action: str = ""


class ClaimValidationQueueResponse(BaseModel):
    items: list[ClaimValidationQueueItem] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    markdown_export: str = ""
    message: str


class IdeaLineageResponse(BaseModel):
    idea: IdeaRead
    research_plans: list["ResearchPlanRead"] = Field(default_factory=list)
    related_work_matrices: list[RelatedWorkMatrixRead] = Field(default_factory=list)
    proposal_drafts: list[ProposalDraftRead] = Field(default_factory=list)
    proposal_reviews: list[ProposalReviewRead] = Field(default_factory=list)
    proposal_revisions: list[ProposalRevisionRead] = Field(default_factory=list)
    experiment_runs: list[ExperimentRunRead] = Field(default_factory=list)
    experiment_analyses: list[ExperimentAnalysisRead] = Field(default_factory=list)
    decision_memos: list[IdeaDecisionMemoRead] = Field(default_factory=list)
    assumption_audits: list[IdeaAssumptionAuditRead] = Field(default_factory=list)
    evidence_ledgers: list[IdeaEvidenceLedgerRead] = Field(default_factory=list)
    research_tasks: list[ResearchTaskRead] = Field(default_factory=list)
    task_board_snapshots: list[TaskBoardSnapshotRead] = Field(default_factory=list)
    graph_edge_summary: dict[str, int] = Field(default_factory=dict)
    markdown_export: str = ""
    message: str


class IdeaProgressResponse(BaseModel):
    idea: IdeaRead
    artifact_counts: dict[str, int] = Field(default_factory=dict)
    latest_artifacts: dict[str, Any] = Field(default_factory=dict)
    task_summary: dict[str, Any] = Field(default_factory=dict)
    experiment_summary: dict[str, Any] = Field(default_factory=dict)
    blockers: list[dict[str, Any]] = Field(default_factory=list)
    recommended_next_step: str = ""
    markdown_export: str = ""
    message: str


class IdeaResearchPacketResponse(BaseModel):
    idea: IdeaRead
    latest_artifacts: dict[str, Any] = Field(default_factory=dict)
    open_tasks: list[ResearchTaskRead] = Field(default_factory=list)
    graph_edge_summary: dict[str, int] = Field(default_factory=dict)
    markdown_export: str = ""
    message: str


class IdeaTimelineEvent(BaseModel):
    event_type: str
    artifact_type: str
    artifact_id: str
    title: str
    status: str = ""
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class IdeaTimelineResponse(BaseModel):
    idea: IdeaRead
    events: list[IdeaTimelineEvent] = Field(default_factory=list)
    markdown_export: str = ""
    message: str


class IdeaReadinessResponse(BaseModel):
    idea: IdeaRead
    readiness_score: float = 0.0
    decision: str = "needs_work"
    score_breakdown: dict[str, Any] = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    markdown_export: str = ""
    message: str


class IdeaQualityGateResponse(BaseModel):
    idea: IdeaRead
    gate_score: float = 0.0
    decision: str = "needs_targeted_revision"
    score_breakdown: dict[str, Any] = Field(default_factory=dict)
    required_evidence: list[dict[str, Any]] = Field(default_factory=list)
    blocking_risks: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    latest_artifacts: dict[str, Any] = Field(default_factory=dict)
    markdown_export: str = ""
    message: str


class IdeaQualityGateSummary(BaseModel):
    idea_id: str
    title: str
    status: str
    gate_score: float = 0.0
    decision: str = "needs_targeted_revision"
    missing_evidence_count: int = 0
    blocking_risk_count: int = 0
    top_risks: list[str] = Field(default_factory=list)
    top_actions: list[str] = Field(default_factory=list)


class ProjectQualityGateOverviewResponse(BaseModel):
    idea_count: int = 0
    average_gate_score: float = 0.0
    decision_counts: dict[str, int] = Field(default_factory=dict)
    advance_candidates: list[IdeaQualityGateSummary] = Field(default_factory=list)
    de_risk_candidates: list[IdeaQualityGateSummary] = Field(default_factory=list)
    revision_candidates: list[IdeaQualityGateSummary] = Field(default_factory=list)
    parked_or_rejected: list[IdeaQualityGateSummary] = Field(default_factory=list)
    markdown_export: str = ""
    message: str


class ProjectQualityGateTaskGenerateRequest(BaseModel):
    limit: int = Field(default=5, ge=1, le=20)
    actions_per_idea: int = Field(default=2, ge=1, le=5)
    decisions: list[str] = Field(
        default_factory=lambda: [
            "de_risk_novelty",
            "needs_targeted_revision",
            "revise_before_investment",
        ]
    )
    created_by: str = "system"


class IdeaReadinessSummary(BaseModel):
    idea_id: str
    title: str
    status: str
    readiness_score: float = 0.0
    decision: str = "needs_work"
    blocker_count: int = 0
    top_blockers: list[str] = Field(default_factory=list)


class ProjectReadinessOverviewResponse(BaseModel):
    idea_count: int = 0
    average_readiness: float = 0.0
    decision_counts: dict[str, int] = Field(default_factory=dict)
    top_ready: list[IdeaReadinessSummary] = Field(default_factory=list)
    needs_work: list[IdeaReadinessSummary] = Field(default_factory=list)
    markdown_export: str = ""
    message: str


class ResearchOpportunityItem(BaseModel):
    idea_id: str
    title: str
    status: str
    rank: int = 0
    opportunity_type: str = "incubate"
    priority: str = "medium"
    radar_score: float = 0.0
    weighted_score: float = 0.0
    readiness_score: float = 0.0
    readiness_decision: str = "needs_work"
    why_now: str = ""
    blocking_risks: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    evidence_signals: list[str] = Field(default_factory=list)
    task_signals: dict[str, Any] = Field(default_factory=dict)


class ResearchOpportunityRadarResponse(BaseModel):
    profile_name: str = "Default Research Profile"
    idea_count: int = 0
    opportunity_count: int = 0
    top_opportunities: list[ResearchOpportunityItem] = Field(default_factory=list)
    risk_watchlist: list[ResearchOpportunityItem] = Field(default_factory=list)
    recommended_sequence: list[str] = Field(default_factory=list)
    markdown_export: str = ""
    message: str


class ResearchOverviewResponse(BaseModel):
    idea_count: int = 0
    status_counts: dict[str, int] = Field(default_factory=dict)
    task_summary: dict[str, Any] = Field(default_factory=dict)
    recent_experiment_analyses: list[dict[str, Any]] = Field(default_factory=list)
    blocked_tasks: list[dict[str, Any]] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    markdown_export: str = ""
    message: str


class ProjectTriageBriefResponse(BaseModel):
    generated_at: datetime
    idea_count: int = 0
    open_task_count: int = 0
    blocked_task_count: int = 0
    average_readiness: float = 0.0
    average_quality_gate_score: float = 0.0
    opportunity_count: int = 0
    recommended_focus: list[str] = Field(default_factory=list)
    risk_focus: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    markdown_export: str = ""
    message: str


class ProjectCockpitResponse(BaseModel):
    generated_at: datetime
    phase: str = "setup"
    readiness_level: str = "getting_started"
    primary_next_action: dict[str, Any] = Field(default_factory=dict)
    quick_actions: list[dict[str, Any]] = Field(default_factory=list)
    workflow_stages: list[dict[str, Any]] = Field(default_factory=list)
    setup_status: list[dict[str, Any]] = Field(default_factory=list)
    project_metrics: dict[str, Any] = Field(default_factory=dict)
    risk_alerts: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    source_summaries: dict[str, Any] = Field(default_factory=dict)
    markdown_export: str = ""
    message: str


class ProjectOnboardingChecklistItem(BaseModel):
    id: str
    label: str
    status: Literal["done", "todo", "warning"] = "todo"
    detail: str = ""
    required: bool = True
    action_label: str = ""
    action_method: str = "GET"
    action_path: str = ""


class ProjectOnboardingReadinessResponse(BaseModel):
    generated_at: datetime
    readiness_score: float = 0.0
    readiness_level: str = "not_ready"
    required_done: int = 0
    required_total: int = 0
    missing_required: list[str] = Field(default_factory=list)
    checklist: list[ProjectOnboardingChecklistItem] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    quick_actions: list[dict[str, Any]] = Field(default_factory=list)
    project_metrics: dict[str, Any] = Field(default_factory=dict)
    markdown_export: str = ""
    message: str


class ProjectBundleReadinessResponse(BaseModel):
    generated_at: datetime
    readiness_score: float = 0.0
    readiness_level: str = "not_ready"
    required_done: int = 0
    required_total: int = 0
    missing_required: list[str] = Field(default_factory=list)
    checklist: list[ProjectOnboardingChecklistItem] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    quick_actions: list[dict[str, Any]] = Field(default_factory=list)
    manifest_summary: dict[str, Any] = Field(default_factory=dict)
    markdown_export: str = ""
    message: str


class ProjectBundleReadinessTaskGenerateRequest(BaseModel):
    limit: int = Field(default=8, ge=1, le=20)
    include_optional: bool = True
    created_by: str = "system"


class ProjectBundleReadinessSnapshotCreate(BaseModel):
    title: str = "Project Bundle Readiness Snapshot"
    created_by: str = "researcher"


class ProjectBundleReadinessSnapshotComparisonRequest(BaseModel):
    baseline_snapshot_id: str
    candidate_snapshot_id: str


class ProjectBundleReadinessSnapshotComparisonTaskGenerateRequest(
    ProjectBundleReadinessSnapshotComparisonRequest
):
    limit: int = Field(default=8, ge=1, le=20)
    include_missing_required: bool = True
    include_recommended_actions: bool = True
    include_quick_actions: bool = True
    created_by: str = "system"


class ProjectBundleReadinessSnapshotComparisonResponse(BaseModel):
    baseline_snapshot_id: str
    candidate_snapshot_id: str
    baseline_title: str
    candidate_title: str
    readiness_delta: dict[str, Any] = Field(default_factory=dict)
    missing_required_delta: dict[str, Any] = Field(default_factory=dict)
    manifest_delta: dict[str, Any] = Field(default_factory=dict)
    added_missing_required: list[str] = Field(default_factory=list)
    removed_missing_required: list[str] = Field(default_factory=list)
    kept_missing_required: list[str] = Field(default_factory=list)
    added_recommended_actions: list[str] = Field(default_factory=list)
    removed_recommended_actions: list[str] = Field(default_factory=list)
    kept_recommended_actions: list[str] = Field(default_factory=list)
    added_quick_actions: list[str] = Field(default_factory=list)
    removed_quick_actions: list[str] = Field(default_factory=list)
    kept_quick_actions: list[str] = Field(default_factory=list)
    summary: str
    markdown_export: str = ""


class ProjectBundleReleaseCreate(BaseModel):
    title: str = "Project Bundle Release Note"
    recipient: str = "advisor_or_customer"
    release_notes: str = ""
    created_by: str = "researcher"


class ProjectBundleReleaseTaskGenerateRequest(BaseModel):
    limit: int = Field(default=6, ge=1, le=20)
    include_missing_required: bool = True
    include_handoff_checks: bool = True
    created_by: str = "system"


class ProjectBundleReleaseProgressResponse(BaseModel):
    release_id: str
    title: str
    recipient: str
    generated_at: datetime
    task_summary: dict[str, Any] = Field(default_factory=dict)
    completion_ratio: float = 0.0
    blocked_tasks: list[ResearchTaskRead] = Field(default_factory=list)
    open_tasks: list[ResearchTaskRead] = Field(default_factory=list)
    done_tasks: list[ResearchTaskRead] = Field(default_factory=list)
    next_tasks: list[ResearchTaskRead] = Field(default_factory=list)
    markdown_export: str = ""
    message: str


class ProjectBundleReleaseFeedbackCreate(BaseModel):
    title: str = "Project Bundle Release Feedback"
    recipient: str = ""
    feedback_status: Literal[
        "received",
        "accepted",
        "changes_requested",
        "blocked",
        "rejected",
    ] = "received"
    signoff_confirmed: bool = False
    feedback_notes: str = ""
    requested_changes: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    accepted_artifacts: list[str] = Field(default_factory=list)
    created_by: str = "researcher"


class ProjectBundleReleaseFeedbackTaskGenerateRequest(BaseModel):
    limit: int = Field(default=6, ge=1, le=20)
    include_requested_changes: bool = True
    include_blockers: bool = True
    include_signoff_check: bool = True
    created_by: str = "system"


class ProjectBundleReleaseCloseoutTaskGenerateRequest(BaseModel):
    limit: int = Field(default=6, ge=1, le=20)
    include_blockers: bool = True
    include_next_actions: bool = True
    include_signoff_check: bool = True
    created_by: str = "system"


class ProjectBundleReleaseCloseoutResponse(BaseModel):
    release_id: str
    title: str
    recipient: str
    generated_at: datetime
    closeout_status: str
    ready_to_close: bool = False
    signoff_confirmed: bool = False
    release_progress: ProjectBundleReleaseProgressResponse
    latest_feedback: dict[str, Any] = Field(default_factory=dict)
    feedback_task_summary: dict[str, Any] = Field(default_factory=dict)
    blocking_reasons: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    markdown_export: str = ""
    message: str


class ProjectBundleReleaseAcceptancePacketResponse(BaseModel):
    release_id: str
    title: str
    recipient: str
    generated_at: datetime
    acceptance_status: str
    ready_for_signoff: bool = False
    signoff_confirmed: bool = False
    release_note: dict[str, Any] = Field(default_factory=dict)
    release_progress: ProjectBundleReleaseProgressResponse
    latest_feedback: dict[str, Any] = Field(default_factory=dict)
    closeout: ProjectBundleReleaseCloseoutResponse
    closeout_task_summary: dict[str, Any] = Field(default_factory=dict)
    open_closeout_tasks: list[ResearchTaskRead] = Field(default_factory=list)
    checklist: list[dict[str, Any]] = Field(default_factory=list)
    remaining_actions: list[str] = Field(default_factory=list)
    markdown_export: str = ""
    message: str


class ProjectBundleReleaseAcceptancePacketSnapshotCreate(BaseModel):
    title: str = "Project Bundle Release Acceptance Packet Snapshot"
    created_by: str = "researcher"


class ProjectBundleReleaseAcceptancePacketSnapshotComparisonRequest(BaseModel):
    baseline_snapshot_id: str
    candidate_snapshot_id: str


class ProjectBundleReleaseAcceptancePacketSnapshotComparisonTaskGenerateRequest(
    ProjectBundleReleaseAcceptancePacketSnapshotComparisonRequest
):
    limit: int = Field(default=6, ge=1, le=20)
    include_remaining_actions: bool = True
    include_checklist_regressions: bool = True
    include_status_regression: bool = True
    created_by: str = "system"


class ProjectBundleReleaseAcceptancePacketSnapshotComparisonResponse(BaseModel):
    baseline_snapshot_id: str
    candidate_snapshot_id: str
    baseline_title: str
    candidate_title: str
    release_id: str
    status_delta: dict[str, Any] = Field(default_factory=dict)
    signoff_delta: dict[str, Any] = Field(default_factory=dict)
    closeout_delta: dict[str, Any] = Field(default_factory=dict)
    remaining_action_delta: dict[str, Any] = Field(default_factory=dict)
    checklist_delta: dict[str, Any] = Field(default_factory=dict)
    added_remaining_actions: list[str] = Field(default_factory=list)
    removed_remaining_actions: list[str] = Field(default_factory=list)
    kept_remaining_actions: list[str] = Field(default_factory=list)
    newly_blocked_checklist_items: list[str] = Field(default_factory=list)
    resolved_checklist_items: list[str] = Field(default_factory=list)
    kept_open_checklist_items: list[str] = Field(default_factory=list)
    summary: str
    markdown_export: str = ""


class ProjectBundleReleaseReviewSessionTaskGenerateRequest(BaseModel):
    limit: int = Field(default=8, ge=1, le=20)
    include_decisions: bool = True
    include_risks: bool = True
    include_follow_up_actions: bool = True
    created_by: str = "system"


class ProjectBundleReleaseReviewSessionResponse(BaseModel):
    release_id: str
    title: str
    recipient: str
    generated_at: datetime
    review_status: str
    ready_for_review: bool = False
    acceptance_status: str
    release_note: dict[str, Any] = Field(default_factory=dict)
    release_progress: ProjectBundleReleaseProgressResponse
    latest_feedback: dict[str, Any] = Field(default_factory=dict)
    closeout: ProjectBundleReleaseCloseoutResponse
    acceptance_packet: ProjectBundleReleaseAcceptancePacketResponse
    latest_acceptance_snapshot: dict[str, Any] = Field(default_factory=dict)
    acceptance_snapshot_comparison: dict[str, Any] = Field(default_factory=dict)
    review_task_summary: dict[str, Any] = Field(default_factory=dict)
    agenda: list[str] = Field(default_factory=list)
    decisions_needed: list[str] = Field(default_factory=list)
    risk_items: list[str] = Field(default_factory=list)
    follow_up_actions: list[str] = Field(default_factory=list)
    artifact_links: list[dict[str, Any]] = Field(default_factory=list)
    markdown_export: str = ""
    message: str


class ProjectBundleReleaseReviewOutcomeCreate(BaseModel):
    title: str = "Project Bundle Release Review Outcome"
    review_decision: Literal[
        "approved",
        "approved_with_changes",
        "changes_requested",
        "follow_up_needed",
        "blocked",
        "rejected",
    ] = "follow_up_needed"
    participants: list[str] = Field(default_factory=list)
    outcome_notes: str = ""
    decisions: list[str] = Field(default_factory=list)
    accepted_artifacts: list[str] = Field(default_factory=list)
    follow_up_actions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    signoff_confirmed: bool = False
    created_by: str = "researcher"


class ProjectBundleReleaseReviewOutcomeTaskGenerateRequest(BaseModel):
    limit: int = Field(default=8, ge=1, le=20)
    include_decisions: bool = True
    include_risks: bool = True
    include_follow_up_actions: bool = True
    include_signoff_check: bool = True
    created_by: str = "system"


class ProjectBundleReleaseReviewOutcomeProgressResponse(BaseModel):
    release_id: str
    outcome_id: str
    title: str
    recipient: str
    generated_at: datetime
    review_decision: str
    signoff_confirmed: bool = False
    task_summary: dict[str, Any] = Field(default_factory=dict)
    completion_ratio: float = 0.0
    blocked_tasks: list[ResearchTaskRead] = Field(default_factory=list)
    open_tasks: list[ResearchTaskRead] = Field(default_factory=list)
    done_tasks: list[ResearchTaskRead] = Field(default_factory=list)
    next_tasks: list[ResearchTaskRead] = Field(default_factory=list)
    markdown_export: str = ""
    message: str


class ProjectBundleReleaseReviewOutcomeSignoffCreate(BaseModel):
    title: str = "Project Bundle Release Review Outcome Signoff"
    signoff_decision: Literal[
        "signed_off",
        "signed_off_with_notes",
        "deferred",
        "declined",
    ] = "deferred"
    approver: str = "advisor_or_customer"
    signoff_notes: str = ""
    accepted_artifacts: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    evidence_links: list[str] = Field(default_factory=list)
    created_by: str = "researcher"


class ProjectSetupWizardResponse(BaseModel):
    generated_at: datetime
    profile: ResearchProfileRead
    readiness: ProjectOnboardingReadinessResponse
    recommended_next_steps: list[str] = Field(default_factory=list)
    quick_actions: list[dict[str, Any]] = Field(default_factory=list)
    markdown_export: str = ""
    message: str


class ProjectOnboardingTaskGenerateRequest(BaseModel):
    limit: int = Field(default=8, ge=1, le=20)
    include_optional: bool = True
    created_by: str = "system"


class ProjectOnboardingProgressResponse(BaseModel):
    generated_at: datetime
    readiness: ProjectOnboardingReadinessResponse
    task_summary: dict[str, Any] = Field(default_factory=dict)
    next_action: str = ""
    blocked_tasks: list[ResearchTaskRead] = Field(default_factory=list)
    next_tasks: list[ResearchTaskRead] = Field(default_factory=list)
    markdown_export: str = ""
    message: str


class ProjectPilotReportResponse(BaseModel):
    generated_at: datetime
    report_status: str = "draft"
    executive_summary: str = ""
    readiness_level: str = "not_ready"
    cockpit_phase: str = "setup"
    onboarding: ProjectOnboardingProgressResponse
    cockpit: ProjectCockpitResponse
    key_metrics: dict[str, Any] = Field(default_factory=dict)
    risks: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    quick_actions: list[dict[str, Any]] = Field(default_factory=list)
    markdown_export: str = ""
    message: str


class ProjectPilotReportSnapshotCreate(BaseModel):
    title: str = "Pilot Status Report Snapshot"
    created_by: str = "researcher"


class ProjectPilotReportSnapshotTaskGenerateRequest(BaseModel):
    limit: int = Field(default=8, ge=1, le=20)
    include_risks: bool = True
    include_next_actions: bool = True
    include_quick_actions: bool = True
    created_by: str = "system"


class ProjectPilotReportSnapshotComparisonRequest(BaseModel):
    baseline_snapshot_id: str
    candidate_snapshot_id: str


class ProjectPilotReportSnapshotComparisonTaskGenerateRequest(
    ProjectPilotReportSnapshotComparisonRequest
):
    limit: int = Field(default=8, ge=1, le=20)
    include_risks: bool = True
    include_next_actions: bool = True
    include_quick_actions: bool = True
    created_by: str = "system"


class ProjectPilotReportSnapshotComparisonResponse(BaseModel):
    baseline_snapshot_id: str
    candidate_snapshot_id: str
    baseline_title: str
    candidate_title: str
    status_change: dict[str, Any] = Field(default_factory=dict)
    metric_delta: dict[str, Any] = Field(default_factory=dict)
    added_risks: list[str] = Field(default_factory=list)
    removed_risks: list[str] = Field(default_factory=list)
    kept_risks: list[str] = Field(default_factory=list)
    added_next_actions: list[str] = Field(default_factory=list)
    removed_next_actions: list[str] = Field(default_factory=list)
    kept_next_actions: list[str] = Field(default_factory=list)
    added_quick_actions: list[str] = Field(default_factory=list)
    removed_quick_actions: list[str] = Field(default_factory=list)
    kept_quick_actions: list[str] = Field(default_factory=list)
    summary: str
    markdown_export: str = ""


class ProjectCockpitTaskGenerateRequest(BaseModel):
    limit: int = Field(default=8, ge=1, le=20)
    include_primary_action: bool = True
    include_next_actions: bool = True
    include_risks: bool = True
    include_highlights: bool = False
    created_by: str = "system"


class ProjectTriageTaskGenerateRequest(BaseModel):
    limit: int = Field(default=8, ge=1, le=20)
    include_risks: bool = True
    created_by: str = "system"


class ProjectTriageSnapshotCreate(BaseModel):
    title: str = "Project Triage Snapshot"
    idea_limit: int = Field(default=50, ge=1, le=200)
    opportunity_limit: int = Field(default=8, ge=1, le=20)
    created_by: str = "researcher"


class ProjectTriageSnapshotRead(BaseModel):
    id: str
    title: str
    summary: dict[str, Any] = Field(default_factory=dict)
    recommended_focus: list[str] = Field(default_factory=list)
    risk_focus: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    source_ids: dict[str, Any] = Field(default_factory=dict)
    markdown_export_chars: int = 0
    created_by: str = "researcher"
    created_at: datetime
    updated_at: datetime


class ProjectTriageSnapshotDetail(ProjectTriageSnapshotRead):
    markdown_export: str = ""


class ProjectTriageSnapshotComparisonRequest(BaseModel):
    baseline_snapshot_id: str
    candidate_snapshot_id: str


class ProjectTriageSnapshotComparisonTaskGenerateRequest(ProjectTriageSnapshotComparisonRequest):
    limit: int = Field(default=8, ge=1, le=20)
    include_focus: bool = True
    include_risks: bool = True
    created_by: str = "system"


class ProjectTriageSnapshotComparisonResponse(BaseModel):
    baseline_snapshot_id: str
    candidate_snapshot_id: str
    baseline_title: str
    candidate_title: str
    metric_delta: dict[str, Any] = Field(default_factory=dict)
    added_focus: list[str] = Field(default_factory=list)
    removed_focus: list[str] = Field(default_factory=list)
    kept_focus: list[str] = Field(default_factory=list)
    added_risks: list[str] = Field(default_factory=list)
    removed_risks: list[str] = Field(default_factory=list)
    kept_risks: list[str] = Field(default_factory=list)
    added_next_actions: list[str] = Field(default_factory=list)
    removed_next_actions: list[str] = Field(default_factory=list)
    kept_next_actions: list[str] = Field(default_factory=list)
    summary: str
    markdown_export: str = ""


class ResearchBriefCreate(BaseModel):
    title: str = "Advisor Research Brief"
    scope: Literal["project", "idea_set"] = "project"
    idea_ids: list[str] = Field(default_factory=list)
    created_by: str = "researcher"


class ResearchBriefRead(BaseModel):
    id: str
    title: str
    scope: str = "project"
    idea_ids: list[str] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    markdown_export_chars: int = 0
    created_by: str = "researcher"
    created_at: datetime
    updated_at: datetime


class ResearchBriefDetail(ResearchBriefRead):
    markdown_export: str = ""


class ResearchPlanCreate(BaseModel):
    title: str = "Research Execution Plan"
    horizon_days: int = 14
    idea_ids: list[str] = Field(default_factory=list)
    created_by: str = "researcher"


class ResearchPlanRead(BaseModel):
    id: str
    title: str
    horizon_days: int = 14
    idea_ids: list[str] = Field(default_factory=list)
    profile_summary: dict[str, Any] = Field(default_factory=dict)
    plan_items: list[dict[str, Any]] = Field(default_factory=list)
    source_ids: dict[str, Any] = Field(default_factory=dict)
    markdown_export_chars: int = 0
    created_by: str = "researcher"
    created_at: datetime
    updated_at: datetime


class ResearchPlanDetail(ResearchPlanRead):
    markdown_export: str = ""


class ResearchPlanProgressResponse(BaseModel):
    plan: ResearchPlanRead
    task_summary: dict[str, Any] = Field(default_factory=dict)
    tasks: list[ResearchTaskRead] = Field(default_factory=list)
    markdown_export: str = ""
    message: str


class ToolManifestItem(BaseModel):
    name: str
    description: str
    method: str
    path: str
    input_model: str = ""
    output_model: str = ""
    side_effect: bool = False


class ToolManifestResponse(BaseModel):
    service: str
    mcp_enabled: bool
    tools: list[ToolManifestItem] = Field(default_factory=list)
    message: str


class ToolBridgeSpecItem(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    http: dict[str, Any] = Field(default_factory=dict)
    output_model: str = ""
    side_effect: bool = False
    annotations: dict[str, Any] = Field(default_factory=dict)


class ToolBridgeSpecResponse(BaseModel):
    service: str
    protocol: str = "research-assistant-http-tool-bridge.v1"
    mcp_enabled: bool
    tools: list[ToolBridgeSpecItem] = Field(default_factory=list)
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


class NoveltyRefreshRequest(BaseModel):
    include_external: bool = True
    limit: int = 8
    query_override: str = ""


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


class AdvisorChatRequest(BaseModel):
    question: str = Field(min_length=1)
    idea_id: str | None = None
    paper_ids: list[str] = Field(default_factory=list)
    include_cockpit: bool = True
    include_context: bool = True
    context_limit: int = Field(default=5, ge=1, le=15)
    created_by: str = "researcher"


class AdvisorChatResponse(BaseModel):
    question: str
    intent: str = "project_status"
    answer: str
    answer_markdown: str = ""
    cockpit_phase: str = ""
    readiness_level: str = ""
    recommended_actions: list[str] = Field(default_factory=list)
    risk_alerts: list[str] = Field(default_factory=list)
    tool_suggestions: list[dict[str, Any]] = Field(default_factory=list)
    cited_evidences: list[ScoredEvidenceRead] = Field(default_factory=list)
    cited_gaps: list[ScoredResearchGapRead] = Field(default_factory=list)
    cited_ideas: list[ScoredIdeaRead] = Field(default_factory=list)
    source_summaries: dict[str, Any] = Field(default_factory=dict)
    message: str


class AdvisorChatTaskGenerateRequest(AdvisorChatRequest):
    limit: int = Field(default=8, ge=1, le=20)
    include_recommendations: bool = True
    include_risks: bool = True
    include_tool_suggestions: bool = False


class AdvisorActionSessionRequest(AdvisorChatTaskGenerateRequest):
    snapshot_title: str = "Advisor Action Session"
    snapshot_statuses: list[str] = Field(default_factory=lambda: ["todo", "doing", "blocked"])
    include_snapshot: bool = True


class AdvisorActionSessionResponse(BaseModel):
    chat: AdvisorChatResponse
    tasks: list[ResearchTaskRead] = Field(default_factory=list)
    snapshot: TaskBoardSnapshotDetail | None = None
    progress_summary: dict[str, Any] = Field(default_factory=dict)
    markdown_export: str = ""
    message: str


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
    status: Literal["pending", "running", "completed", "failed", "canceled"]
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
