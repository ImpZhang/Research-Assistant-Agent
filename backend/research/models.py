from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.research.db import Base


def new_id() -> str:
    return uuid4().hex


def utc_now() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class Paper(Base, TimestampMixin):
    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(512), default="")
    authors_json: Mapped[list] = mapped_column(JSON, default=list)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    venue: Mapped[str] = mapped_column(String(255), default="")
    doi: Mapped[str] = mapped_column(String(255), default="")
    arxiv_id: Mapped[str] = mapped_column(String(128), default="")
    source_type: Mapped[str] = mapped_column(String(64), default="upload")
    source_url: Mapped[str] = mapped_column(String(1024), default="")
    filename: Mapped[str] = mapped_column(String(512), default="")
    file_path: Mapped[str] = mapped_column(String(1024), default="")
    domain: Mapped[str] = mapped_column(String(255), default="")
    task: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(64), default="uploaded")


class PaperSection(Base, TimestampMixin):
    __tablename__ = "paper_sections"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"), index=True)
    title: Mapped[str] = mapped_column(String(512), default="")
    section_type: Mapped[str] = mapped_column(String(128), default="")
    level: Mapped[int] = mapped_column(Integer, default=1)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text, default="")
    order_index: Mapped[int] = mapped_column(Integer, default=0)


class Chunk(Base, TimestampMixin):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"), index=True)
    section_id: Mapped[str | None] = mapped_column(ForeignKey("paper_sections.id"), nullable=True)
    chunk_id: Mapped[str] = mapped_column(String(512), index=True)
    parent_chunk_id: Mapped[str] = mapped_column(String(512), default="")
    root_chunk_id: Mapped[str] = mapped_column(String(512), default="")
    chunk_level: Mapped[int] = mapped_column(Integer, default=1)
    chunk_idx: Mapped[int] = mapped_column(Integer, default=0)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text, default="")
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Evidence(Base, TimestampMixin):
    __tablename__ = "evidences"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"), index=True)
    section_id: Mapped[str | None] = mapped_column(ForeignKey("paper_sections.id"), nullable=True)
    chunk_id: Mapped[str] = mapped_column(String(512), default="", index=True)
    evidence_type: Mapped[str] = mapped_column(String(128), index=True)
    text: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    supports: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class PaperCard(Base, TimestampMixin):
    __tablename__ = "paper_cards"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"), index=True, unique=True)
    problem_json: Mapped[dict] = mapped_column(JSON, default=dict)
    motivation_json: Mapped[dict] = mapped_column(JSON, default=dict)
    contributions_json: Mapped[dict] = mapped_column(JSON, default=dict)
    method_json: Mapped[dict] = mapped_column(JSON, default=dict)
    datasets_json: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)
    baselines_json: Mapped[dict] = mapped_column(JSON, default=dict)
    results_json: Mapped[dict] = mapped_column(JSON, default=dict)
    limitations_json: Mapped[dict] = mapped_column(JSON, default=dict)
    future_work_json: Mapped[dict] = mapped_column(JSON, default=dict)
    keywords_json: Mapped[dict] = mapped_column(JSON, default=dict)
    open_questions_json: Mapped[dict] = mapped_column(JSON, default=dict)
    extraction_model: Mapped[str] = mapped_column(String(255), default="")
    extraction_status: Mapped[str] = mapped_column(String(64), default="pending")


class ResearchGap(Base, TimestampMixin):
    __tablename__ = "research_gaps"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(512), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    gap_type: Mapped[str] = mapped_column(String(128), index=True)
    source_paper_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    evidence_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    why_important: Mapped[str] = mapped_column(Text, default="")
    why_unsolved: Mapped[str] = mapped_column(Text, default="")
    possible_approaches_json: Mapped[list] = mapped_column(JSON, default=list)
    feasibility_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    novelty_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(64), default="generated")


class Idea(Base, TimestampMixin):
    __tablename__ = "ideas"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(512), default="")
    research_question: Mapped[str] = mapped_column(Text, default="")
    core_hypothesis: Mapped[str] = mapped_column(Text, default="")
    motivation: Mapped[str] = mapped_column(Text, default="")
    related_gap_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    related_paper_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    evidence_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    method_sketch: Mapped[str] = mapped_column(Text, default="")
    expected_contribution: Mapped[str] = mapped_column(Text, default="")
    novelty_argument: Mapped[str] = mapped_column(Text, default="")
    datasets_json: Mapped[list] = mapped_column(JSON, default=list)
    baselines_json: Mapped[list] = mapped_column(JSON, default=list)
    metrics_json: Mapped[list] = mapped_column(JSON, default=list)
    risks_json: Mapped[list] = mapped_column(JSON, default=list)
    resource_requirements: Mapped[str] = mapped_column(Text, default="")
    target_venues_json: Mapped[list] = mapped_column(JSON, default=list)
    score_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(64), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_idea_id: Mapped[str | None] = mapped_column(ForeignKey("ideas.id"), nullable=True)


class Review(Base, TimestampMixin):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), index=True)
    reviewer_type: Mapped[str] = mapped_column(String(128), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    major_concerns_json: Mapped[list] = mapped_column(JSON, default=list)
    minor_concerns_json: Mapped[list] = mapped_column(JSON, default=list)
    required_experiments_json: Mapped[list] = mapped_column(JSON, default=list)
    decision: Mapped[str] = mapped_column(String(64), default="")
    action_items_json: Mapped[list] = mapped_column(JSON, default=list)


class NoveltyCheck(Base, TimestampMixin):
    __tablename__ = "novelty_checks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), index=True)
    status: Mapped[str] = mapped_column(String(64), default="completed")
    risk_level: Mapped[str] = mapped_column(String(64), default="unknown")
    summary: Mapped[str] = mapped_column(Text, default="")
    local_overlap_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    external_overlap_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    collision_signals_json: Mapped[list] = mapped_column(JSON, default=list)
    missing_searches_json: Mapped[list] = mapped_column(JSON, default=list)
    recommended_actions_json: Mapped[list] = mapped_column(JSON, default=list)
    checked_sources_json: Mapped[list] = mapped_column(JSON, default=list)


class ExperimentPlan(Base, TimestampMixin):
    __tablename__ = "experiment_plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), index=True)
    objective: Mapped[str] = mapped_column(Text, default="")
    hypothesis: Mapped[str] = mapped_column(Text, default="")
    datasets_json: Mapped[list] = mapped_column(JSON, default=list)
    baselines_json: Mapped[list] = mapped_column(JSON, default=list)
    metrics_json: Mapped[list] = mapped_column(JSON, default=list)
    main_experiment_json: Mapped[dict] = mapped_column(JSON, default=dict)
    ablation_studies_json: Mapped[list] = mapped_column(JSON, default=list)
    robustness_tests_json: Mapped[list] = mapped_column(JSON, default=list)
    expected_tables_json: Mapped[list] = mapped_column(JSON, default=list)
    failure_modes_json: Mapped[list] = mapped_column(JSON, default=list)
    fallback_plan: Mapped[str] = mapped_column(Text, default="")
    compute_requirements: Mapped[str] = mapped_column(Text, default="")
    timeline_json: Mapped[dict] = mapped_column(JSON, default=dict)


class ExperimentRun(Base, TimestampMixin):
    __tablename__ = "experiment_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    experiment_plan_id: Mapped[str] = mapped_column(ForeignKey("experiment_plans.id"), index=True)
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), index=True)
    task_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_tasks.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(64), default="running", index=True)
    objective_snapshot: Mapped[str] = mapped_column(Text, default="")
    hypothesis_snapshot: Mapped[str] = mapped_column(Text, default="")
    dataset_snapshot: Mapped[str] = mapped_column(Text, default="")
    baseline_snapshot_json: Mapped[list] = mapped_column(JSON, default=list)
    parameters_json: Mapped[dict] = mapped_column(JSON, default=dict)
    metric_results_json: Mapped[dict] = mapped_column(JSON, default=dict)
    artifact_links_json: Mapped[list] = mapped_column(JSON, default=list)
    conclusion: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    markdown_export: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(128), default="system")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExperimentAnalysis(Base, TimestampMixin):
    __tablename__ = "experiment_analyses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    experiment_run_id: Mapped[str] = mapped_column(ForeignKey("experiment_runs.id"), index=True)
    experiment_plan_id: Mapped[str] = mapped_column(ForeignKey("experiment_plans.id"), index=True)
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), index=True)
    task_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_tasks.id"), nullable=True, index=True
    )
    decision: Mapped[str] = mapped_column(String(128), default="needs_more_evidence", index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    metric_interpretation_json: Mapped[dict] = mapped_column(JSON, default=dict)
    key_findings_json: Mapped[list] = mapped_column(JSON, default=list)
    concerns_json: Mapped[list] = mapped_column(JSON, default=list)
    next_actions_json: Mapped[list] = mapped_column(JSON, default=list)
    markdown_export: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(128), default="system")


class IdeaFeedback(Base, TimestampMixin):
    __tablename__ = "idea_feedback"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), index=True)
    decision: Mapped[str] = mapped_column(String(64), default="revise", index=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    comment: Mapped[str] = mapped_column(Text, default="")
    tags_json: Mapped[list] = mapped_column(JSON, default=list)
    created_by: Mapped[str] = mapped_column(String(128), default="researcher")


class IdeaDecisionMemo(Base, TimestampMixin):
    __tablename__ = "idea_decision_memos"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), index=True)
    decision: Mapped[str] = mapped_column(String(64), default="revise", index=True)
    rationale_json: Mapped[list] = mapped_column(JSON, default=list)
    evidence_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    risk_register_json: Mapped[list] = mapped_column(JSON, default=list)
    next_commitments_json: Mapped[list] = mapped_column(JSON, default=list)
    source_artifacts_json: Mapped[dict] = mapped_column(JSON, default=dict)
    markdown_export: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(128), default="researcher")


class IdeaAssumptionAudit(Base, TimestampMixin):
    __tablename__ = "idea_assumption_audits"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), index=True)
    status: Mapped[str] = mapped_column(String(64), default="completed", index=True)
    assumptions_json: Mapped[list] = mapped_column(JSON, default=list)
    source_artifacts_json: Mapped[dict] = mapped_column(JSON, default=dict)
    markdown_export: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(128), default="system")


class RelatedWorkMatrix(Base, TimestampMixin):
    __tablename__ = "related_work_matrices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), index=True)
    status: Mapped[str] = mapped_column(String(64), default="completed", index=True)
    query: Mapped[str] = mapped_column(Text, default="")
    items_json: Mapped[list] = mapped_column(JSON, default=list)
    differentiators_json: Mapped[list] = mapped_column(JSON, default=list)
    missing_searches_json: Mapped[list] = mapped_column(JSON, default=list)
    checked_sources_json: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    markdown_export: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(128), default="system")


class ProposalDraft(Base, TimestampMixin):
    __tablename__ = "proposal_drafts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), index=True)
    status: Mapped[str] = mapped_column(String(64), default="draft", index=True)
    title: Mapped[str] = mapped_column(String(512), default="")
    abstract: Mapped[str] = mapped_column(Text, default="")
    problem_statement: Mapped[str] = mapped_column(Text, default="")
    novelty_statement: Mapped[str] = mapped_column(Text, default="")
    related_work_summary: Mapped[str] = mapped_column(Text, default="")
    method_summary: Mapped[str] = mapped_column(Text, default="")
    experiment_summary: Mapped[str] = mapped_column(Text, default="")
    risk_mitigation: Mapped[str] = mapped_column(Text, default="")
    milestone_plan_json: Mapped[list] = mapped_column(JSON, default=list)
    evidence_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    related_work_matrix_id: Mapped[str | None] = mapped_column(
        ForeignKey("related_work_matrices.id"),
        nullable=True,
    )
    experiment_plan_id: Mapped[str | None] = mapped_column(
        ForeignKey("experiment_plans.id"),
        nullable=True,
    )
    markdown_export: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(128), default="system")


class ProposalReview(Base, TimestampMixin):
    __tablename__ = "proposal_reviews"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    proposal_draft_id: Mapped[str] = mapped_column(
        ForeignKey("proposal_drafts.id"),
        index=True,
    )
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), index=True)
    reviewer_type: Mapped[str] = mapped_column(String(128), default="advisor")
    decision: Mapped[str] = mapped_column(String(64), default="revise", index=True)
    readiness_score: Mapped[float] = mapped_column(Float, default=0.0)
    strengths_json: Mapped[list] = mapped_column(JSON, default=list)
    concerns_json: Mapped[list] = mapped_column(JSON, default=list)
    required_revisions_json: Mapped[list] = mapped_column(JSON, default=list)
    missing_evidence_json: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    markdown_export: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(128), default="system")


class ProposalRevision(Base, TimestampMixin):
    __tablename__ = "proposal_revisions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    proposal_draft_id: Mapped[str] = mapped_column(
        ForeignKey("proposal_drafts.id"),
        index=True,
    )
    proposal_review_id: Mapped[str | None] = mapped_column(
        ForeignKey("proposal_reviews.id"),
        nullable=True,
        index=True,
    )
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), index=True)
    status: Mapped[str] = mapped_column(String(64), default="revised", index=True)
    revision_summary: Mapped[str] = mapped_column(Text, default="")
    applied_revisions_json: Mapped[list] = mapped_column(JSON, default=list)
    missing_evidence_actions_json: Mapped[list] = mapped_column(JSON, default=list)
    revised_sections_json: Mapped[dict] = mapped_column(JSON, default=dict)
    markdown_export: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(128), default="system")


class ResearchTask(Base, TimestampMixin):
    __tablename__ = "research_tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    idea_id: Mapped[str | None] = mapped_column(ForeignKey("ideas.id"), nullable=True, index=True)
    owner_type: Mapped[str] = mapped_column(String(128), default="proposal_revision", index=True)
    owner_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    source_type: Mapped[str] = mapped_column(String(128), default="", index=True)
    source_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    title: Mapped[str] = mapped_column(String(512), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(64), default="medium", index=True)
    status: Mapped[str] = mapped_column(String(64), default="todo", index=True)
    due_phase: Mapped[str] = mapped_column(String(128), default="")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(128), default="system")


class ResearchTaskEvent(Base, TimestampMixin):
    __tablename__ = "research_task_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("research_tasks.id"), index=True)
    idea_id: Mapped[str | None] = mapped_column(ForeignKey("ideas.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(128), default="note", index=True)
    status_from: Mapped[str] = mapped_column(String(64), default="")
    status_to: Mapped[str] = mapped_column(String(64), default="")
    priority_from: Mapped[str] = mapped_column(String(64), default="")
    priority_to: Mapped[str] = mapped_column(String(64), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(128), default="system")


class TaskBoardSnapshot(Base, TimestampMixin):
    __tablename__ = "task_board_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(512), default="Research Task Board")
    idea_id: Mapped[str | None] = mapped_column(ForeignKey("ideas.id"), nullable=True, index=True)
    owner_type: Mapped[str] = mapped_column(String(128), default="")
    status_filter_json: Mapped[list] = mapped_column(JSON, default=list)
    task_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    markdown_export: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(128), default="system")


class IdeaPortfolioSnapshot(Base, TimestampMixin):
    __tablename__ = "idea_portfolio_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(512), default="Research Idea Portfolio")
    description: Mapped[str] = mapped_column(Text, default="")
    ranking_request_json: Mapped[dict] = mapped_column(JSON, default=dict)
    idea_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    ranked_items_json: Mapped[list] = mapped_column(JSON, default=list)
    markdown_export: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(128), default="researcher")


class ResearchBrief(Base, TimestampMixin):
    __tablename__ = "research_briefs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(512), default="Advisor Research Brief")
    scope: Mapped[str] = mapped_column(String(128), default="project", index=True)
    idea_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    markdown_export: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(128), default="researcher")


class ResearchNode(Base, TimestampMixin):
    __tablename__ = "research_nodes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    node_type: Mapped[str] = mapped_column(String(128), index=True)
    label: Mapped[str] = mapped_column(String(512), index=True)
    canonical_key: Mapped[str] = mapped_column(String(512), index=True, default="")
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)


class ResearchEdge(Base, TimestampMixin):
    __tablename__ = "research_edges"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    source_node_id: Mapped[str] = mapped_column(ForeignKey("research_nodes.id"), index=True)
    target_node_id: Mapped[str] = mapped_column(ForeignKey("research_nodes.id"), index=True)
    edge_type: Mapped[str] = mapped_column(String(128), index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    evidence_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)


class ResearchEmbedding(Base, TimestampMixin):
    __tablename__ = "research_embeddings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    owner_type: Mapped[str] = mapped_column(String(128), index=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    embedding_model: Mapped[str] = mapped_column(String(255), default="local_hash_embedding_v0")
    dimension: Mapped[int] = mapped_column(Integer, default=128)
    text_hash: Mapped[str] = mapped_column(String(64), index=True, default="")
    vector_json: Mapped[list] = mapped_column(JSON, default=list)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    job_type: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(64), default="pending", index=True)
    input_json: Mapped[dict] = mapped_column(JSON, default=dict)
    output_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
