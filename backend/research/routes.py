import io
import json
import zipfile
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import PlainTextResponse, Response
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
    IdeaAssumptionAudit,
    IdeaDecisionMemo,
    IdeaEvidenceLedger,
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
    ProjectTriageSnapshot,
    RelatedWorkMatrix,
    ResearchBrief,
    ResearchEdge,
    ResearchGap,
    ResearchNode,
    ResearchPlanSnapshot,
    ResearchProfile,
    Review,
    ResearchTask,
    ResearchTaskEvent,
    TaskBoardSnapshot,
)
from backend.research.schemas import (
    ClaimValidationQueueItem,
    ClaimValidationQueueResponse,
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
    IdeaAssumptionAuditCreate,
    IdeaAssumptionAuditRead,
    IdeaClaimValidationPacketResponse,
    IdeaFeedbackCreate,
    IdeaFeedbackRead,
    IdeaGenerationRequest,
    IdeaGenerationResponse,
    IdeaDecisionMemoCreate,
    IdeaDecisionMemoRead,
    IdeaEvidenceLedgerCreate,
    IdeaEvidenceLedgerRead,
    IdeaLineageResponse,
    IdeaProgressResponse,
    IdeaQualityGateResponse,
    IdeaQualityGateSummary,
    IdeaReadinessResponse,
    IdeaReadinessSummary,
    IdeaResearchPacketResponse,
    IdeaTimelineEvent,
    IdeaTimelineResponse,
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
    NoveltyRefreshRequest,
    OpportunityRadarTaskGenerateRequest,
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
    ProjectQualityGateOverviewResponse,
    ProjectQualityGateTaskGenerateRequest,
    ProjectReadinessOverviewResponse,
    ProjectStatus,
    ProjectTriageBriefResponse,
    ProjectTriageSnapshotComparisonRequest,
    ProjectTriageSnapshotComparisonResponse,
    ProjectTriageSnapshotComparisonTaskGenerateRequest,
    ProjectTriageSnapshotCreate,
    ProjectTriageSnapshotDetail,
    ProjectTriageSnapshotRead,
    ProjectTriageTaskGenerateRequest,
    RankedIdeaRead,
    RelatedWorkMatrixCreate,
    RelatedWorkMatrixRead,
    ResearchBriefCreate,
    ResearchBriefDetail,
    ResearchBriefRead,
    ResearchEdgeRead,
    ResearchGapRead,
    ResearchNodeRead,
    ResearchOpportunityItem,
    ResearchOpportunityRadarResponse,
    ResearchOverviewResponse,
    ResearchPlanCreate,
    ResearchPlanDetail,
    ResearchPlanProgressResponse,
    ResearchPlanRead,
    ResearchProfileRead,
    ResearchProfileUpdate,
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
    ToolBridgeSpecResponse,
    ToolManifestItem,
    ToolManifestResponse,
)
from backend.research.services.brief_service import ResearchBriefService
from backend.research.services.assumption_audit_service import IdeaAssumptionAuditService
from backend.research.services.document_ingestion import DocumentIngestionService
from backend.research.services.decision_memo_service import IdeaDecisionMemoService
from backend.research.services.embedding_service import EmbeddingService
from backend.research.services.evidence_ledger_service import IdeaEvidenceLedgerService
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
from backend.research.services.research_plan_service import ResearchPlanService
from backend.research.services.research_profile_service import (
    ResearchProfileService,
    default_research_profile_markdown,
    render_research_profile_markdown,
)
from backend.research.services.retrieval_service import RetrievalService
from backend.research.services.review_service import ReviewService
from backend.research.services.structured_extraction_service import StructuredExtractionService
from backend.research.services.structured_idea_service import StructuredIdeaService
from backend.research.services.task_service import ResearchTaskService
from backend.research.services.task_board_service import TaskBoardService
from backend.research.services.tool_bridge_service import build_tool_bridge_items
from backend.research.services.triage_snapshot_service import ProjectTriageSnapshotService
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
            "research_profile_constraints",
            "research_plan_snapshots",
            "research_plan_task_generation",
            "research_plan_progress_integration",
            "research_plan_progress_tracking",
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
            "idea_research_packet",
            "idea_activity_timeline",
            "idea_readiness_scoring",
            "idea_quality_gate",
            "idea_quality_gate_task_generation",
            "idea_readiness_task_generation",
            "idea_decision_memos",
            "idea_decision_task_generation",
            "idea_assumption_audits",
            "idea_evidence_ledgers",
            "idea_evidence_task_generation",
            "claim_evidence_graph_links",
            "claim_validation_packets",
            "claim_validation_queue",
            "project_progress_overview",
            "project_triage_brief",
            "project_triage_task_generation",
            "project_triage_snapshots",
            "project_triage_snapshot_comparison",
            "project_triage_snapshot_comparison_task_generation",
            "project_readiness_overview",
            "project_quality_gate_overview",
            "project_quality_gate_task_generation",
            "research_opportunity_radar",
            "opportunity_radar_task_generation",
            "idea_artifact_bundle_export",
            "project_handoff_bundle_export",
            "advisor_research_briefs",
            "advisor_brief_execution_context",
            "advisor_brief_evidence_context",
            "advisor_brief_triage_context",
            "advisor_brief_triage_snapshot_comparison_context",
            "tool_manifest",
            "mcp_tool_bridge_spec",
            "mcp_stdio_http_bridge",
            "mcp_bridge_policy_controls",
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
            "task_execution_controls",
            "workbench_task_board_controls",
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
            "external_novelty_refresh",
            "novelty_check_task_generation",
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
            "external_novelty_monitoring",
            "managed_mcp_server",
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
            name="get_research_profile",
            description="Read researcher goals, preferences, constraints, and ranking weights.",
            method="GET",
            path="/research/profile",
            output_model="ResearchProfileRead",
        ),
        ToolManifestItem(
            name="update_research_profile",
            description="Persist researcher goals, preferences, constraints, and ranking weights.",
            method="PUT",
            path="/research/profile",
            input_model="ResearchProfileUpdate",
            output_model="ResearchProfileRead",
            side_effect=True,
        ),
        ToolManifestItem(
            name="create_research_plan",
            description="Generate a profile-aware execution plan from ranked ideas and open tasks.",
            method="POST",
            path="/research/plans",
            input_model="ResearchPlanCreate",
            output_model="ResearchPlanDetail",
            side_effect=True,
        ),
        ToolManifestItem(
            name="create_tasks_from_research_plan",
            description="Turn a research execution plan into concrete task-board tasks.",
            method="POST",
            path="/research/plans/{plan_id}/tasks",
            input_model="ResearchTaskGenerateRequest",
            output_model="ResearchTaskGenerationResponse",
            side_effect=True,
        ),
        ToolManifestItem(
            name="get_research_plan_progress",
            description="Summarize task progress for one research execution plan.",
            method="GET",
            path="/research/plans/{plan_id}/progress",
            output_model="ResearchPlanProgressResponse",
        ),
        ToolManifestItem(
            name="get_mcp_tool_spec",
            description="Export an HTTP tool bridge spec for MCP, DeerFlow, or external planner adapters.",
            method="GET",
            path="/research/tools/mcp-spec",
            output_model="ToolBridgeSpecResponse",
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
            name="get_idea_research_packet",
            description="Load a Markdown-ready research packet for one idea.",
            method="GET",
            path="/research/ideas/{idea_id}/research-packet",
            output_model="IdeaResearchPacketResponse",
        ),
        ToolManifestItem(
            name="get_idea_timeline",
            description="Load a chronological activity timeline for one idea.",
            method="GET",
            path="/research/ideas/{idea_id}/timeline",
            output_model="IdeaTimelineResponse",
        ),
        ToolManifestItem(
            name="export_idea_bundle",
            description="Download a zip bundle with one idea's dossier, lineage, readiness, tasks, and artifact Markdown.",
            method="GET",
            path="/research/ideas/{idea_id}/export/bundle",
            output_model="application/zip",
        ),
        ToolManifestItem(
            name="export_project_bundle",
            description="Download a project-level handoff bundle with overviews, briefs, plans, and task state.",
            method="GET",
            path="/research/export/project-bundle",
            output_model="application/zip",
        ),
        ToolManifestItem(
            name="get_idea_readiness",
            description="Score whether an idea is ready for deeper execution.",
            method="GET",
            path="/research/ideas/{idea_id}/readiness",
            output_model="IdeaReadinessResponse",
        ),
        ToolManifestItem(
            name="get_idea_quality_gate",
            description="Run a go/no-go quality gate across novelty, readiness, proposal, experiments, and task health.",
            method="GET",
            path="/research/ideas/{idea_id}/quality-gate",
            output_model="IdeaQualityGateResponse",
        ),
        ToolManifestItem(
            name="create_tasks_from_idea_quality_gate",
            description="Turn quality-gate recommended actions into concrete follow-up research tasks.",
            method="POST",
            path="/research/ideas/{idea_id}/quality-gate/tasks",
            input_model="ResearchTaskGenerateRequest",
            output_model="ResearchTaskGenerationResponse",
            side_effect=True,
        ),
        ToolManifestItem(
            name="create_tasks_from_idea_readiness",
            description="Turn readiness blockers into concrete follow-up research tasks.",
            method="POST",
            path="/research/ideas/{idea_id}/readiness/tasks",
            input_model="ResearchTaskGenerateRequest",
            output_model="ResearchTaskGenerationResponse",
            side_effect=True,
        ),
        ToolManifestItem(
            name="list_research_tasks",
            description="List research tasks by idea, owner type, status, or recency.",
            method="GET",
            path="/research/tasks",
            output_model="list[ResearchTaskRead]",
        ),
        ToolManifestItem(
            name="update_research_task",
            description="Update a research task status, priority, description, or note.",
            method="PATCH",
            path="/research/tasks/{task_id}",
            input_model="ResearchTaskUpdate",
            output_model="ResearchTaskRead",
            side_effect=True,
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
            name="create_tasks_from_idea_decision_memo",
            description="Turn decision memo next commitments into research tasks.",
            method="POST",
            path="/research/ideas/{idea_id}/decision-memos/{memo_id}/tasks",
            input_model="ResearchTaskGenerateRequest",
            output_model="ResearchTaskGenerationResponse",
            side_effect=True,
        ),
        ToolManifestItem(
            name="create_idea_assumption_audit",
            description="Persist a falsifiability-focused assumption audit for one idea.",
            method="POST",
            path="/research/ideas/{idea_id}/assumption-audit",
            input_model="IdeaAssumptionAuditCreate",
            output_model="IdeaAssumptionAuditRead",
            side_effect=True,
        ),
        ToolManifestItem(
            name="create_idea_evidence_ledger",
            description="Persist a claim-level evidence ledger for one idea.",
            method="POST",
            path="/research/ideas/{idea_id}/evidence-ledger",
            input_model="IdeaEvidenceLedgerCreate",
            output_model="IdeaEvidenceLedgerRead",
            side_effect=True,
        ),
        ToolManifestItem(
            name="list_idea_evidence_ledgers",
            description="List saved claim-evidence ledgers for one idea.",
            method="GET",
            path="/research/ideas/{idea_id}/evidence-ledgers",
            output_model="list[IdeaEvidenceLedgerRead]",
        ),
        ToolManifestItem(
            name="create_tasks_from_idea_evidence_ledger",
            description="Turn evidence-ledger gaps, counterevidence, and risks into follow-up tasks.",
            method="POST",
            path="/research/ideas/{idea_id}/evidence-ledgers/{ledger_id}/tasks",
            input_model="ResearchTaskGenerateRequest",
            output_model="ResearchTaskGenerationResponse",
            side_effect=True,
        ),
        ToolManifestItem(
            name="get_idea_claim_validation_packet",
            description="Load one ledger claim with support, counterevidence, tasks, and graph summary.",
            method="GET",
            path="/research/ideas/{idea_id}/evidence-ledgers/{ledger_id}/claims/{claim_id}/validation-packet",
            output_model="IdeaClaimValidationPacketResponse",
        ),
        ToolManifestItem(
            name="get_claim_validation_queue",
            description="Rank weak ledger claims across latest evidence ledgers for validation work.",
            method="GET",
            path="/research/claims/validation-queue",
            output_model="ClaimValidationQueueResponse",
        ),
        ToolManifestItem(
            name="refresh_idea_novelty_search",
            description="Run a configurable novelty refresh using local and optional external literature search.",
            method="POST",
            path="/research/ideas/{idea_id}/novelty-refresh",
            input_model="NoveltyRefreshRequest",
            output_model="NoveltyCheckRead",
            side_effect=True,
        ),
        ToolManifestItem(
            name="create_tasks_from_idea_novelty_check",
            description="Turn novelty check recommended actions into task-board tasks.",
            method="POST",
            path="/research/ideas/{idea_id}/novelty-checks/{check_id}/tasks",
            input_model="ResearchTaskGenerateRequest",
            output_model="ResearchTaskGenerationResponse",
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
            name="get_project_triage_brief",
            description="Synthesize progress, readiness, quality gates, and opportunities into a daily research triage brief.",
            method="GET",
            path="/research/triage/brief",
            output_model="ProjectTriageBriefResponse",
        ),
        ToolManifestItem(
            name="export_project_triage_brief_markdown",
            description="Export the latest project triage brief as text/markdown.",
            method="GET",
            path="/research/triage/brief/export/markdown",
            output_model="text/markdown",
        ),
        ToolManifestItem(
            name="create_tasks_from_project_triage_brief",
            description="Turn project triage brief next actions and risks into project-level task-board tasks.",
            method="POST",
            path="/research/triage/brief/tasks",
            input_model="ProjectTriageTaskGenerateRequest",
            output_model="ResearchTaskGenerationResponse",
            side_effect=True,
        ),
        ToolManifestItem(
            name="create_project_triage_snapshot",
            description="Persist the latest project triage brief as a durable Markdown decision snapshot.",
            method="POST",
            path="/research/triage/snapshots",
            input_model="ProjectTriageSnapshotCreate",
            output_model="ProjectTriageSnapshotDetail",
            side_effect=True,
        ),
        ToolManifestItem(
            name="list_project_triage_snapshots",
            description="List saved project triage decision snapshots.",
            method="GET",
            path="/research/triage/snapshots",
            output_model="list[ProjectTriageSnapshotRead]",
        ),
        ToolManifestItem(
            name="compare_project_triage_snapshots",
            description="Compare two saved project triage snapshots for focus, risk, action, and metric changes.",
            method="POST",
            path="/research/triage/snapshots/compare",
            input_model="ProjectTriageSnapshotComparisonRequest",
            output_model="ProjectTriageSnapshotComparisonResponse",
        ),
        ToolManifestItem(
            name="export_project_triage_snapshot_comparison_markdown",
            description="Export a comparison of two saved project triage snapshots as text/markdown.",
            method="POST",
            path="/research/triage/snapshots/compare/export/markdown",
            input_model="ProjectTriageSnapshotComparisonRequest",
            output_model="text/markdown",
        ),
        ToolManifestItem(
            name="create_tasks_from_project_triage_snapshot_comparison",
            description="Turn added focus, risks, and next actions from a triage snapshot comparison into project tasks.",
            method="POST",
            path="/research/triage/snapshots/compare/tasks",
            input_model="ProjectTriageSnapshotComparisonTaskGenerateRequest",
            output_model="ResearchTaskGenerationResponse",
            side_effect=True,
        ),
        ToolManifestItem(
            name="get_project_triage_snapshot",
            description="Load one saved project triage decision snapshot.",
            method="GET",
            path="/research/triage/snapshots/{snapshot_id}",
            output_model="ProjectTriageSnapshotDetail",
        ),
        ToolManifestItem(
            name="export_project_triage_snapshot_markdown",
            description="Export one saved project triage snapshot as text/markdown.",
            method="GET",
            path="/research/triage/snapshots/{snapshot_id}/export/markdown",
            output_model="text/markdown",
        ),
        ToolManifestItem(
            name="get_project_readiness_overview",
            description="Read project-level readiness scores across recent ideas.",
            method="GET",
            path="/research/readiness/overview",
            output_model="ProjectReadinessOverviewResponse",
        ),
        ToolManifestItem(
            name="get_project_quality_gate_overview",
            description="Compare recent ideas by quality-gate decision and next de-risking action.",
            method="GET",
            path="/research/quality/overview",
            output_model="ProjectQualityGateOverviewResponse",
        ),
        ToolManifestItem(
            name="create_tasks_from_project_quality_gate",
            description="Create quality-gate follow-up tasks for portfolio-level de-risk or revision candidates.",
            method="POST",
            path="/research/quality/overview/tasks",
            input_model="ProjectQualityGateTaskGenerateRequest",
            output_model="ResearchTaskGenerationResponse",
            side_effect=True,
        ),
        ToolManifestItem(
            name="get_research_opportunity_radar",
            description="Prioritize project opportunities from ranking, readiness, tasks, and blockers.",
            method="GET",
            path="/research/opportunities/radar",
            output_model="ResearchOpportunityRadarResponse",
        ),
        ToolManifestItem(
            name="create_tasks_from_research_opportunity_radar",
            description="Turn top opportunity radar next actions into task-board tasks.",
            method="POST",
            path="/research/opportunities/radar/tasks",
            input_model="OpportunityRadarTaskGenerateRequest",
            output_model="ResearchTaskGenerationResponse",
            side_effect=True,
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


@router.get("/tools/mcp-spec", response_model=ToolBridgeSpecResponse)
def tool_bridge_spec() -> ToolBridgeSpecResponse:
    manifest = tool_manifest()
    tools = build_tool_bridge_items(manifest.tools)
    return ToolBridgeSpecResponse(
        service=settings.app_name,
        mcp_enabled=settings.mcp_enabled,
        tools=tools,
        message=f"Generated {len(tools)} HTTP tool bridge specs from the research manifest.",
    )


@router.get("/profile", response_model=ResearchProfileRead)
def get_research_profile(
    session: Session = Depends(get_session),
) -> ResearchProfileRead:
    profile = ResearchProfileService(session).get_profile()
    if profile is None:
        return _default_research_profile_response()
    return _serialize_research_profile(profile)


@router.put("/profile", response_model=ResearchProfileRead)
def update_research_profile(
    payload: ResearchProfileUpdate,
    session: Session = Depends(get_session),
) -> ResearchProfileRead:
    profile = ResearchProfileService(session).update_profile(payload)
    return _serialize_research_profile(profile)


@router.get(
    "/profile/export/markdown",
    response_class=PlainTextResponse,
)
def export_research_profile_markdown(
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    profile = ResearchProfileService(session).get_profile()
    markdown = (
        render_research_profile_markdown(profile)
        if profile
        else default_research_profile_markdown()
    )
    return PlainTextResponse(markdown, media_type="text/markdown")


def _default_research_profile_response() -> ResearchProfileRead:
    return ResearchProfileRead(markdown_export=default_research_profile_markdown())


def _serialize_research_profile(profile: ResearchProfile) -> ResearchProfileRead:
    return ResearchProfileRead(
        id=profile.id,
        name=profile.name,
        primary_domains=profile.primary_domains_json or [],
        active_questions=profile.active_questions_json or [],
        target_venues=profile.target_venues_json or [],
        methodological_preferences=profile.methodological_preferences_json or [],
        resource_constraints=profile.resource_constraints_json or [],
        risk_tolerance=profile.risk_tolerance,
        timeline_horizon=profile.timeline_horizon,
        negative_preferences=profile.negative_preferences_json or [],
        evaluation_weights=profile.evaluation_weights_json or {},
        notes=profile.notes,
        markdown_export=profile.markdown_export or render_research_profile_markdown(profile),
        created_by=profile.created_by,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
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
    by_owner_type = Counter(task.owner_type for task in tasks)
    open_tasks = [task for task in tasks if task.status in {"todo", "doing", "blocked"}]
    top_open_tasks = sorted(open_tasks, key=_progress_task_order)[:10]
    return {
        "total_recent_tasks": len(tasks),
        "open_task_count": len(open_tasks),
        "research_plan_task_count": by_owner_type.get("research_plan", 0),
        "by_status": dict(by_status),
        "by_priority": dict(by_priority),
        "by_owner_type": dict(by_owner_type),
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
        f"- Research Plan Tasks: {task_summary.get('research_plan_task_count', 0)}",
        f"- Tasks By Owner Type: {task_summary.get('by_owner_type', {})}",
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


@router.get("/triage/brief", response_model=ProjectTriageBriefResponse)
def get_project_triage_brief(
    idea_limit: int = 50,
    opportunity_limit: int = 8,
    session: Session = Depends(get_session),
) -> ProjectTriageBriefResponse:
    idea_limit = max(1, min(idea_limit, 200))
    opportunity_limit = max(1, min(opportunity_limit, 20))
    overview = get_research_progress_overview(idea_limit=idea_limit, session=session)
    readiness = get_project_readiness_overview(limit=idea_limit, session=session)
    quality = get_project_quality_gate_overview(limit=idea_limit, session=session)
    radar = get_research_opportunity_radar(limit=opportunity_limit, session=session)
    generated_at = datetime.now(timezone.utc)
    recommended_focus = _triage_recommended_focus(readiness, quality, radar)
    risk_focus = _triage_risk_focus(overview, readiness, quality)
    next_actions = _triage_next_actions(overview, quality, radar)
    markdown_export = _render_project_triage_brief_markdown(
        generated_at=generated_at,
        overview=overview,
        readiness=readiness,
        quality=quality,
        radar=radar,
        recommended_focus=recommended_focus,
        risk_focus=risk_focus,
        next_actions=next_actions,
    )
    return ProjectTriageBriefResponse(
        generated_at=generated_at,
        idea_count=overview.idea_count,
        open_task_count=overview.task_summary.get("open_task_count", 0),
        blocked_task_count=len(overview.blocked_tasks),
        average_readiness=readiness.average_readiness,
        average_quality_gate_score=quality.average_gate_score,
        opportunity_count=radar.opportunity_count,
        recommended_focus=recommended_focus,
        risk_focus=risk_focus,
        next_actions=next_actions,
        markdown_export=markdown_export,
        message=(
            "Built project triage brief from progress, readiness, "
            "quality gates, and opportunity radar."
        ),
    )


@router.get(
    "/triage/brief/export/markdown",
    response_class=PlainTextResponse,
)
def export_project_triage_brief_markdown(
    idea_limit: int = 50,
    opportunity_limit: int = 8,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    triage = get_project_triage_brief(
        idea_limit=idea_limit,
        opportunity_limit=opportunity_limit,
        session=session,
    )
    return PlainTextResponse(triage.markdown_export, media_type="text/markdown")


@router.post("/triage/brief/tasks", response_model=ResearchTaskGenerationResponse)
def create_tasks_from_project_triage_brief(
    payload: ProjectTriageTaskGenerateRequest,
    session: Session = Depends(get_session),
) -> ResearchTaskGenerationResponse:
    triage = get_project_triage_brief(session=session)
    tasks = ResearchTaskService(session).create_from_project_triage(
        next_actions=triage.next_actions,
        risk_focus=triage.risk_focus if payload.include_risks else [],
        limit=payload.limit,
        created_by=payload.created_by,
    )
    return ResearchTaskGenerationResponse(
        tasks=[_serialize_research_task(task) for task in tasks],
        message=f"Created {len(tasks)} project triage tasks from the latest triage brief.",
    )


def _serialize_project_triage_snapshot(
    snapshot: ProjectTriageSnapshot,
    *,
    include_markdown: bool = False,
) -> ProjectTriageSnapshotRead | ProjectTriageSnapshotDetail:
    payload = {
        "id": snapshot.id,
        "title": snapshot.title,
        "summary": snapshot.summary_json or {},
        "recommended_focus": snapshot.recommended_focus_json or [],
        "risk_focus": snapshot.risk_focus_json or [],
        "next_actions": snapshot.next_actions_json or [],
        "source_ids": snapshot.source_ids_json or {},
        "markdown_export_chars": len(snapshot.markdown_export or ""),
        "created_by": snapshot.created_by,
        "created_at": snapshot.created_at,
        "updated_at": snapshot.updated_at,
    }
    if include_markdown:
        return ProjectTriageSnapshotDetail(
            **payload,
            markdown_export=snapshot.markdown_export or "",
        )
    return ProjectTriageSnapshotRead(**payload)


@router.post("/triage/snapshots", response_model=ProjectTriageSnapshotDetail)
def create_project_triage_snapshot(
    payload: ProjectTriageSnapshotCreate,
    session: Session = Depends(get_session),
) -> ProjectTriageSnapshotDetail:
    triage = get_project_triage_brief(
        idea_limit=payload.idea_limit,
        opportunity_limit=payload.opportunity_limit,
        session=session,
    )
    snapshot = ProjectTriageSnapshotService(session).create_snapshot(
        triage=triage,
        title=payload.title,
        idea_limit=payload.idea_limit,
        opportunity_limit=payload.opportunity_limit,
        created_by=payload.created_by,
    )
    return _serialize_project_triage_snapshot(snapshot, include_markdown=True)


@router.get("/triage/snapshots", response_model=list[ProjectTriageSnapshotRead])
def list_project_triage_snapshots(
    limit: int = 50,
    session: Session = Depends(get_session),
) -> list[ProjectTriageSnapshotRead]:
    snapshots = ProjectTriageSnapshotService(session).list_snapshots(limit)
    return [_serialize_project_triage_snapshot(snapshot) for snapshot in snapshots]


@router.post(
    "/triage/snapshots/compare",
    response_model=ProjectTriageSnapshotComparisonResponse,
)
def compare_project_triage_snapshots(
    payload: ProjectTriageSnapshotComparisonRequest,
    session: Session = Depends(get_session),
) -> ProjectTriageSnapshotComparisonResponse:
    try:
        comparison = ProjectTriageSnapshotService(session).compare_snapshots(
            payload.baseline_snapshot_id,
            payload.candidate_snapshot_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ProjectTriageSnapshotComparisonResponse(**comparison)


@router.post(
    "/triage/snapshots/compare/export/markdown",
    response_class=PlainTextResponse,
)
def export_project_triage_snapshot_comparison_markdown(
    payload: ProjectTriageSnapshotComparisonRequest,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    comparison = compare_project_triage_snapshots(payload, session)
    return PlainTextResponse(comparison.markdown_export, media_type="text/markdown")


@router.post(
    "/triage/snapshots/compare/tasks",
    response_model=ResearchTaskGenerationResponse,
)
def create_tasks_from_project_triage_snapshot_comparison(
    payload: ProjectTriageSnapshotComparisonTaskGenerateRequest,
    session: Session = Depends(get_session),
) -> ResearchTaskGenerationResponse:
    try:
        comparison = ProjectTriageSnapshotService(session).compare_snapshots(
            payload.baseline_snapshot_id,
            payload.candidate_snapshot_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    tasks = ResearchTaskService(session).create_from_project_triage_comparison(
        comparison,
        limit=payload.limit,
        include_focus=payload.include_focus,
        include_risks=payload.include_risks,
        created_by=payload.created_by,
    )
    return ResearchTaskGenerationResponse(
        tasks=[_serialize_research_task(task) for task in tasks],
        message=(
            f"Created {len(tasks)} project triage comparison tasks from snapshots "
            f"{payload.baseline_snapshot_id} -> {payload.candidate_snapshot_id}."
        ),
    )


@router.get("/triage/snapshots/{snapshot_id}", response_model=ProjectTriageSnapshotDetail)
def get_project_triage_snapshot(
    snapshot_id: str,
    session: Session = Depends(get_session),
) -> ProjectTriageSnapshotDetail:
    snapshot = ProjectTriageSnapshotService(session).get_snapshot(snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Project triage snapshot not found")
    return _serialize_project_triage_snapshot(snapshot, include_markdown=True)


@router.get(
    "/triage/snapshots/{snapshot_id}/export/markdown",
    response_class=PlainTextResponse,
)
def export_project_triage_snapshot_markdown(
    snapshot_id: str,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    snapshot = ProjectTriageSnapshotService(session).get_snapshot(snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Project triage snapshot not found")
    return PlainTextResponse(snapshot.markdown_export or "", media_type="text/markdown")


def _triage_recommended_focus(
    readiness: ProjectReadinessOverviewResponse,
    quality: ProjectQualityGateOverviewResponse,
    radar: ResearchOpportunityRadarResponse,
) -> list[str]:
    focus = []
    for item in quality.advance_candidates[:3]:
        focus.append(f"Advance `{item.idea_id}`: {item.title} ({item.gate_score:.4f}).")
    for item in radar.top_opportunities[:3]:
        focus.append(
            f"Opportunity #{item.rank} `{item.idea_id}`: {item.title} "
            f"(radar={item.radar_score:.4f})."
        )
    for item in readiness.top_ready[:3]:
        focus.append(
            f"Ready candidate `{item.idea_id}`: {item.title} "
            f"(readiness={item.readiness_score:.4f})."
        )
    return _dedupe_strings(focus)[:8]


def _triage_risk_focus(
    overview: ResearchOverviewResponse,
    readiness: ProjectReadinessOverviewResponse,
    quality: ProjectQualityGateOverviewResponse,
) -> list[str]:
    risks = []
    for task in overview.blocked_tasks[:3]:
        risks.append(f"Blocked task `{task['id']}`: {task['title']}.")
    for item in quality.de_risk_candidates[:5]:
        risk = (
            item.top_risks[0]
            if item.top_risks
            else (item.top_actions[0] if item.top_actions else "No risk summary.")
        )
        risks.append(f"De-risk `{item.idea_id}`: {risk}")
    for item in readiness.needs_work[:3]:
        blocker = item.top_blockers[0] if item.top_blockers else "No blocker summary."
        risks.append(f"Readiness gap `{item.idea_id}`: {blocker}")
    return _dedupe_strings(risks)[:10]


def _triage_next_actions(
    overview: ResearchOverviewResponse,
    quality: ProjectQualityGateOverviewResponse,
    radar: ResearchOpportunityRadarResponse,
) -> list[str]:
    actions = [*overview.recommended_actions[:3]]
    for item in [*quality.de_risk_candidates[:3], *quality.revision_candidates[:3]]:
        if item.top_actions:
            actions.append(f"{item.title}: {item.top_actions[0]}")
    actions.extend(radar.recommended_sequence[:5])
    return _dedupe_strings(actions)[:10]


def _render_project_triage_brief_markdown(
    *,
    generated_at: datetime,
    overview: ResearchOverviewResponse,
    readiness: ProjectReadinessOverviewResponse,
    quality: ProjectQualityGateOverviewResponse,
    radar: ResearchOpportunityRadarResponse,
    recommended_focus: list[str],
    risk_focus: list[str],
    next_actions: list[str],
) -> str:
    lines = [
        "# Project Triage Brief",
        "",
        f"- Generated At: `{generated_at.isoformat()}`",
        f"- Idea Count: {overview.idea_count}",
        f"- Open Tasks: {overview.task_summary.get('open_task_count', 0)}",
        f"- Blocked Tasks: {len(overview.blocked_tasks)}",
        f"- Average Readiness: {readiness.average_readiness:.4f}",
        f"- Average Quality Gate Score: {quality.average_gate_score:.4f}",
        f"- Opportunity Count: {radar.opportunity_count}",
        "",
        "## Recommended Focus",
        "",
    ]
    if recommended_focus:
        lines.extend(f"- {item}" for item in recommended_focus)
    else:
        lines.append("- No focus candidates available yet.")
    lines.extend(["", "## Risk Focus", ""])
    if risk_focus:
        lines.extend(f"- {item}" for item in risk_focus)
    else:
        lines.append("- No major risk focus found.")
    lines.extend(["", "## Next Actions", ""])
    if next_actions:
        lines.extend(f"- {item}" for item in next_actions)
    else:
        lines.append("- Ingest papers or generate ideas to create the first action queue.")
    return "\n".join(lines).strip() + "\n"


def _dedupe_strings(items: list[str]) -> list[str]:
    unique = []
    seen = set()
    for item in items:
        clean = " ".join(str(item).split())
        key = clean.lower()
        if clean and key not in seen:
            unique.append(clean)
            seen.add(key)
    return unique


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


def _serialize_research_plan(
    plan: ResearchPlanSnapshot,
    *,
    include_markdown: bool = False,
) -> ResearchPlanRead | ResearchPlanDetail:
    payload = {
        "id": plan.id,
        "title": plan.title,
        "horizon_days": plan.horizon_days,
        "idea_ids": plan.idea_ids_json or [],
        "profile_summary": plan.profile_summary_json or {},
        "plan_items": plan.plan_items_json or [],
        "source_ids": plan.source_ids_json or {},
        "markdown_export_chars": len(plan.markdown_export or ""),
        "created_by": plan.created_by,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }
    if include_markdown:
        return ResearchPlanDetail(**payload, markdown_export=plan.markdown_export or "")
    return ResearchPlanRead(**payload)


@router.post("/plans", response_model=ResearchPlanDetail)
def create_research_plan(
    payload: ResearchPlanCreate,
    session: Session = Depends(get_session),
) -> ResearchPlanDetail:
    plan = ResearchPlanService(session).create_plan(
        title=payload.title,
        horizon_days=payload.horizon_days,
        idea_ids=payload.idea_ids,
        created_by=payload.created_by,
    )
    return _serialize_research_plan(plan, include_markdown=True)


@router.get("/plans", response_model=list[ResearchPlanRead])
def list_research_plans(
    limit: int = 50,
    session: Session = Depends(get_session),
) -> list[ResearchPlanRead]:
    plans = ResearchPlanService(session).list_plans(limit)
    return [_serialize_research_plan(plan) for plan in plans]


@router.get("/plans/{plan_id}", response_model=ResearchPlanDetail)
def get_research_plan(
    plan_id: str,
    session: Session = Depends(get_session),
) -> ResearchPlanDetail:
    plan = ResearchPlanService(session).get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Research plan not found")
    return _serialize_research_plan(plan, include_markdown=True)


@router.get(
    "/plans/{plan_id}/export/markdown",
    response_class=PlainTextResponse,
)
def export_research_plan_markdown(
    plan_id: str,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    plan = ResearchPlanService(session).get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Research plan not found")
    return PlainTextResponse(plan.markdown_export or "", media_type="text/markdown")


@router.post("/plans/{plan_id}/tasks", response_model=ResearchTaskGenerationResponse)
def create_tasks_from_research_plan(
    plan_id: str,
    payload: ResearchTaskGenerateRequest,
    session: Session = Depends(get_session),
) -> ResearchTaskGenerationResponse:
    try:
        tasks = ResearchTaskService(session).create_from_research_plan(
            plan_id,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ResearchTaskGenerationResponse(
        tasks=[_serialize_research_task(task) for task in tasks],
        message=f"Created {len(tasks)} research tasks from research plan {plan_id}.",
    )


@router.get("/plans/{plan_id}/progress", response_model=ResearchPlanProgressResponse)
def get_research_plan_progress(
    plan_id: str,
    session: Session = Depends(get_session),
) -> ResearchPlanProgressResponse:
    plan = ResearchPlanService(session).get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Research plan not found")
    tasks = (
        session.query(ResearchTask)
        .filter(
            ResearchTask.owner_type == "research_plan",
            ResearchTask.owner_id == plan.id,
        )
        .order_by(ResearchTask.created_at.desc())
        .limit(200)
        .all()
    )
    task_summary = _research_plan_task_summary(tasks)
    markdown_export = _render_research_plan_progress_markdown(
        plan=plan,
        task_summary=task_summary,
        tasks=tasks,
    )
    return ResearchPlanProgressResponse(
        plan=_serialize_research_plan(plan),
        task_summary=task_summary,
        tasks=[_serialize_research_task(task) for task in tasks],
        markdown_export=markdown_export,
        message=f"Loaded progress for research plan {plan.id}.",
    )


def _research_plan_task_summary(tasks: list[ResearchTask]) -> dict[str, Any]:
    by_status = Counter(task.status for task in tasks)
    by_priority = Counter(task.priority for task in tasks)
    by_phase = Counter((task.metadata_json or {}).get("phase", "") for task in tasks)
    open_tasks = [task for task in tasks if task.status in {"todo", "doing", "blocked"}]
    done_count = by_status.get("done", 0) + by_status.get("archived", 0)
    total_count = len(tasks)
    return {
        "task_count": total_count,
        "open_task_count": len(open_tasks),
        "blocked_task_count": by_status.get("blocked", 0),
        "done_task_count": done_count,
        "completion_ratio": round(done_count / total_count, 4) if total_count else 0.0,
        "by_status": dict(by_status),
        "by_priority": dict(by_priority),
        "by_phase": {key or "unspecified": value for key, value in by_phase.items()},
        "next_tasks": [
            {
                "id": task.id,
                "title": task.title,
                "priority": task.priority,
                "status": task.status,
                "phase": (task.metadata_json or {}).get("phase", ""),
            }
            for task in sorted(open_tasks, key=_progress_task_order)[:10]
        ],
    }


def _render_research_plan_progress_markdown(
    *,
    plan: ResearchPlanSnapshot,
    task_summary: dict[str, Any],
    tasks: list[ResearchTask],
) -> str:
    lines = [
        f"# Research Plan Progress: {plan.title}",
        "",
        f"- Plan ID: `{plan.id}`",
        f"- Horizon Days: {plan.horizon_days}",
        f"- Task Count: {task_summary.get('task_count', 0)}",
        f"- Open Tasks: {task_summary.get('open_task_count', 0)}",
        f"- Blocked Tasks: {task_summary.get('blocked_task_count', 0)}",
        f"- Completion Ratio: {task_summary.get('completion_ratio', 0.0)}",
        "",
        "## Status Breakdown",
        "",
        f"- By Status: {task_summary.get('by_status', {})}",
        f"- By Priority: {task_summary.get('by_priority', {})}",
        f"- By Phase: {task_summary.get('by_phase', {})}",
        "",
        "## Next Plan Tasks",
        "",
    ]
    next_tasks = task_summary.get("next_tasks") or []
    if next_tasks:
        for task in next_tasks:
            lines.append(
                f"- `{task['id']}` `{task['priority']}` `{task['status']}` "
                f"phase=`{task.get('phase') or 'unspecified'}` {task['title']}"
            )
    else:
        lines.append("- No open plan tasks.")
    lines.extend(["", "## All Plan Tasks", ""])
    if tasks:
        for task in sorted(tasks, key=_progress_task_order):
            phase = (task.metadata_json or {}).get("phase", "")
            lines.append(
                f"- `{task.id}` `{task.priority}` `{task.status}` "
                f"phase=`{phase or 'unspecified'}` {task.title}"
            )
    else:
        lines.append("- No tasks have been generated from this plan yet.")
    return "\n".join(lines).strip() + "\n"


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


def _serialize_idea_assumption_audit(audit: IdeaAssumptionAudit) -> IdeaAssumptionAuditRead:
    return IdeaAssumptionAuditRead(
        id=audit.id,
        idea_id=audit.idea_id,
        status=audit.status,
        assumptions=audit.assumptions_json or [],
        source_artifacts=audit.source_artifacts_json or {},
        markdown_export=audit.markdown_export or "",
        created_by=audit.created_by,
        created_at=audit.created_at,
        updated_at=audit.updated_at,
    )


def _serialize_idea_evidence_ledger(ledger: IdeaEvidenceLedger) -> IdeaEvidenceLedgerRead:
    return IdeaEvidenceLedgerRead(
        id=ledger.id,
        idea_id=ledger.idea_id,
        status=ledger.status,
        claims=ledger.claims_json or [],
        evidence_links=ledger.evidence_links_json or [],
        counterevidence=ledger.counterevidence_json or [],
        missing_evidence=ledger.missing_evidence_json or [],
        risk_register=ledger.risk_register_json or [],
        source_artifacts=ledger.source_artifacts_json or {},
        summary=ledger.summary_json or {},
        coverage_score=ledger.coverage_score,
        markdown_export=ledger.markdown_export or "",
        created_by=ledger.created_by,
        created_at=ledger.created_at,
        updated_at=ledger.updated_at,
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
    assumption_audits = (
        session.query(IdeaAssumptionAudit)
        .filter(IdeaAssumptionAudit.idea_id == idea_id)
        .order_by(IdeaAssumptionAudit.created_at.desc())
        .limit(20)
        .all()
    )
    evidence_ledgers = (
        session.query(IdeaEvidenceLedger)
        .filter(IdeaEvidenceLedger.idea_id == idea_id)
        .order_by(IdeaEvidenceLedger.created_at.desc())
        .limit(20)
        .all()
    )
    research_plans = _latest_research_plans_for_idea(session, idea_id, 20)
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
            f"{idea_id}:readiness",
            f"{idea_id}:quality_gate",
            f"{idea_id}:opportunity_radar",
            *[matrix.id for matrix in matrices],
            *[draft.id for draft in drafts],
            *[review.id for review in reviews],
            *[revision.id for revision in revisions],
            *[run.experiment_plan_id for run in experiment_runs],
            *[run.id for run in experiment_runs],
            *[analysis.id for analysis in experiment_analyses],
            *[memo.id for memo in decision_memos],
            *[audit.id for audit in assumption_audits],
            *[ledger.id for ledger in evidence_ledgers],
            *[plan.id for plan in research_plans],
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
        assumption_audits=assumption_audits,
        evidence_ledgers=evidence_ledgers,
        research_plans=research_plans,
        tasks=tasks,
        snapshots=snapshots,
        graph_edge_summary=graph_edge_summary,
    )
    return IdeaLineageResponse(
        idea=_serialize_idea(idea),
        research_plans=[_serialize_research_plan(plan) for plan in research_plans],
        related_work_matrices=[_serialize_related_work_matrix(matrix) for matrix in matrices],
        proposal_drafts=[_serialize_proposal_draft(draft) for draft in drafts],
        proposal_reviews=[_serialize_proposal_review(review) for review in reviews],
        proposal_revisions=[_serialize_proposal_revision(revision) for revision in revisions],
        experiment_runs=[_serialize_experiment_run(run) for run in experiment_runs],
        experiment_analyses=[
            _serialize_experiment_analysis(analysis) for analysis in experiment_analyses
        ],
        decision_memos=[_serialize_idea_decision_memo(memo) for memo in decision_memos],
        assumption_audits=[_serialize_idea_assumption_audit(audit) for audit in assumption_audits],
        evidence_ledgers=[_serialize_idea_evidence_ledger(ledger) for ledger in evidence_ledgers],
        research_tasks=[_serialize_research_task(task) for task in tasks],
        task_board_snapshots=[_serialize_task_board_snapshot(snapshot) for snapshot in snapshots],
        graph_edge_summary=graph_edge_summary,
        markdown_export=markdown_export,
        message=(
            f"Loaded lineage for idea {idea.id}: {len(drafts)} drafts, "
            f"{len(reviews)} reviews, {len(revisions)} revisions, "
            f"{len(experiment_runs)} experiment runs, "
            f"{len(experiment_analyses)} analyses, "
            f"{len(decision_memos)} decision memos, "
            f"{len(assumption_audits)} assumption audits, "
            f"{len(evidence_ledgers)} evidence ledgers, "
            f"{len(research_plans)} research plans, {len(tasks)} tasks."
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
    assumption_audits = _latest_for_idea(session, IdeaAssumptionAudit, idea_id, 20)
    evidence_ledgers = _latest_for_idea(session, IdeaEvidenceLedger, idea_id, 20)
    research_plans = _latest_research_plans_for_idea(session, idea_id, 20)
    tasks = _latest_for_idea(session, ResearchTask, idea_id, 200)
    snapshots = _latest_for_idea(session, TaskBoardSnapshot, idea_id, 20)

    latest_analysis = experiment_analyses[0] if experiment_analyses else None
    latest_memo = decision_memos[0] if decision_memos else None
    latest_ledger = evidence_ledgers[0] if evidence_ledgers else None
    analysis_tasks = [
        task
        for task in tasks
        if latest_analysis
        and task.owner_type == "experiment_analysis"
        and task.owner_id == latest_analysis.id
    ]
    decision_tasks = [
        task
        for task in tasks
        if latest_memo
        and task.owner_type == "idea_decision_memo"
        and task.owner_id == latest_memo.id
    ]
    evidence_tasks = [
        task
        for task in tasks
        if latest_ledger
        and task.owner_type == "idea_evidence_ledger"
        and task.owner_id == latest_ledger.id
    ]
    research_plan_tasks = [task for task in tasks if task.owner_type == "research_plan"]
    readiness_tasks = [task for task in tasks if task.owner_type == "idea_readiness"]
    quality_gate_tasks = [task for task in tasks if task.owner_type == "idea_quality_gate"]
    opportunity_tasks = [task for task in tasks if task.owner_type == "opportunity_radar"]
    novelty_tasks = [task for task in tasks if task.owner_type == "novelty_check"]
    artifact_counts = {
        "related_work_matrices": len(matrices),
        "proposal_drafts": len(drafts),
        "proposal_reviews": len(reviews),
        "proposal_revisions": len(revisions),
        "experiment_runs": len(experiment_runs),
        "experiment_analyses": len(experiment_analyses),
        "decision_memos": len(decision_memos),
        "assumption_audits": len(assumption_audits),
        "evidence_ledgers": len(evidence_ledgers),
        "research_plans": len(research_plans),
        "research_tasks": len(tasks),
        "open_tasks": len([task for task in tasks if task.status in {"todo", "doing", "blocked"}]),
        "blocked_tasks": len([task for task in tasks if task.status == "blocked"]),
        "research_plan_tasks": len(research_plan_tasks),
        "readiness_follow_up_tasks": len(readiness_tasks),
        "quality_gate_follow_up_tasks": len(quality_gate_tasks),
        "opportunity_follow_up_tasks": len(opportunity_tasks),
        "novelty_follow_up_tasks": len(novelty_tasks),
        "analysis_follow_up_tasks": len(analysis_tasks),
        "decision_follow_up_tasks": len(decision_tasks),
        "evidence_follow_up_tasks": len(evidence_tasks),
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
        assumption_audits,
        evidence_ledgers,
        research_plans,
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


def _latest_research_plans_for_idea(
    session: Session,
    idea_id: str,
    limit: int,
) -> list[ResearchPlanSnapshot]:
    scan_limit = max(limit * 5, 50)
    plans = (
        session.query(ResearchPlanSnapshot)
        .order_by(ResearchPlanSnapshot.created_at.desc())
        .limit(scan_limit)
        .all()
    )
    return [plan for plan in plans if idea_id in (plan.idea_ids_json or [])][:limit]


def _progress_latest_artifacts(
    matrices: list[RelatedWorkMatrix],
    drafts: list[ProposalDraft],
    reviews: list[ProposalReview],
    revisions: list[ProposalRevision],
    experiment_runs: list[ExperimentRun],
    experiment_analyses: list[ExperimentAnalysis],
    decision_memos: list[IdeaDecisionMemo],
    assumption_audits: list[IdeaAssumptionAudit],
    evidence_ledgers: list[IdeaEvidenceLedger],
    research_plans: list[ResearchPlanSnapshot],
    snapshots: list[TaskBoardSnapshot],
) -> dict[str, dict | None]:
    latest_run = experiment_runs[0] if experiment_runs else None
    latest_analysis = experiment_analyses[0] if experiment_analyses else None
    latest_memo = decision_memos[0] if decision_memos else None
    latest_audit = assumption_audits[0] if assumption_audits else None
    latest_ledger = evidence_ledgers[0] if evidence_ledgers else None
    latest_plan = research_plans[0] if research_plans else None
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
        "assumption_audit": {
            "id": latest_audit.id,
            "assumption_count": len(latest_audit.assumptions_json or []),
        }
        if latest_audit
        else None,
        "evidence_ledger": {
            "id": latest_ledger.id,
            "coverage_score": latest_ledger.coverage_score,
            "unsupported_claim_count": (latest_ledger.summary_json or {}).get(
                "unsupported_claim_count", 0
            ),
            "counterevidence_count": (latest_ledger.summary_json or {}).get(
                "counterevidence_count", 0
            ),
            "missing_evidence_count": (latest_ledger.summary_json or {}).get(
                "missing_evidence_count", 0
            ),
            "high_risk_count": (latest_ledger.summary_json or {}).get("high_risk_count", 0),
            "decision_hint": (latest_ledger.summary_json or {}).get("decision_hint", ""),
        }
        if latest_ledger
        else None,
        "research_plan": {
            "id": latest_plan.id,
            "title": latest_plan.title,
            "horizon_days": latest_plan.horizon_days,
            "plan_item_count": len(latest_plan.plan_items_json or []),
        }
        if latest_plan
        else None,
        "task_board_snapshot": {"id": snapshots[0].id, "title": snapshots[0].title}
        if snapshots
        else None,
    }


def _progress_task_summary(tasks: list[ResearchTask]) -> dict:
    by_status = Counter(task.status for task in tasks)
    by_priority = Counter(task.priority for task in tasks)
    by_owner_type = Counter(task.owner_type for task in tasks)
    by_due_phase = Counter(task.due_phase for task in tasks if task.due_phase)
    next_tasks = sorted(
        [task for task in tasks if task.status in {"todo", "doing", "blocked"}],
        key=_progress_task_order,
    )[:8]
    return {
        "by_status": dict(by_status),
        "by_priority": dict(by_priority),
        "by_owner_type": dict(by_owner_type),
        "by_due_phase": dict(by_due_phase),
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
    if artifact_counts["assumption_audits"] == 0:
        return "Create an assumption audit to expose what must be true before deeper execution."
    if artifact_counts["evidence_ledgers"] == 0:
        return "Create an evidence ledger to map claims, support, counterevidence, and missing evidence."
    latest_ledger = latest_artifacts.get("evidence_ledger") or {}
    if latest_ledger and artifact_counts["evidence_follow_up_tasks"] == 0:
        open_evidence_items = (
            int(latest_ledger.get("unsupported_claim_count") or 0)
            + int(latest_ledger.get("missing_evidence_count") or 0)
            + int(latest_ledger.get("counterevidence_count") or 0)
            + int(latest_ledger.get("high_risk_count") or 0)
        )
        if open_evidence_items:
            return "Generate follow-up tasks from the latest evidence ledger gaps."
    if artifact_counts["proposal_revisions"] == 0:
        return "Create a proposal revision from the latest review."
    if artifact_counts["research_tasks"] == 0:
        return "Generate a task backlog from the latest proposal revision."
    if artifact_counts["research_plans"] and artifact_counts["research_plan_tasks"] == 0:
        return "Generate concrete tasks from the latest research execution plan."
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
    if artifact_counts["decision_memos"] and artifact_counts["decision_follow_up_tasks"] == 0:
        return "Generate follow-up tasks from the latest decision memo commitments."
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
    lines.append(f"- By Owner Type: {task_summary.get('by_owner_type', {})}")
    lines.append(f"- By Due Phase: {task_summary.get('by_due_phase', {})}")
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


@router.get("/ideas/{idea_id}/research-packet", response_model=IdeaResearchPacketResponse)
def get_idea_research_packet(
    idea_id: str,
    session: Session = Depends(get_session),
) -> IdeaResearchPacketResponse:
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
    assumption_audits = _latest_for_idea(session, IdeaAssumptionAudit, idea_id, 20)
    evidence_ledgers = _latest_for_idea(session, IdeaEvidenceLedger, idea_id, 20)
    research_plans = _latest_research_plans_for_idea(session, idea_id, 20)
    tasks = _latest_for_idea(session, ResearchTask, idea_id, 200)
    open_tasks = sorted(
        [task for task in tasks if task.status in {"todo", "doing", "blocked"}],
        key=_progress_task_order,
    )[:20]
    graph_edge_summary = _graph_edge_summary(
        session,
        [
            idea_id,
            f"{idea_id}:readiness",
            f"{idea_id}:quality_gate",
            f"{idea_id}:opportunity_radar",
            *[matrix.id for matrix in matrices],
            *[draft.id for draft in drafts],
            *[review.id for review in reviews],
            *[revision.id for revision in revisions],
            *[run.experiment_plan_id for run in experiment_runs],
            *[run.id for run in experiment_runs],
            *[analysis.id for analysis in experiment_analyses],
            *[memo.id for memo in decision_memos],
            *[audit.id for audit in assumption_audits],
            *[ledger.id for ledger in evidence_ledgers],
            *[plan.id for plan in research_plans],
            *[task.id for task in open_tasks],
        ],
    )
    latest_artifacts = _research_packet_latest_artifacts(
        matrices=matrices,
        drafts=drafts,
        reviews=reviews,
        revisions=revisions,
        experiment_runs=experiment_runs,
        experiment_analyses=experiment_analyses,
        decision_memos=decision_memos,
        assumption_audits=assumption_audits,
        evidence_ledgers=evidence_ledgers,
        research_plans=research_plans,
    )
    markdown_export = _render_idea_research_packet_markdown(
        idea=idea,
        latest_artifacts=latest_artifacts,
        open_tasks=open_tasks,
        graph_edge_summary=graph_edge_summary,
    )
    return IdeaResearchPacketResponse(
        idea=_serialize_idea(idea),
        latest_artifacts=latest_artifacts,
        open_tasks=[_serialize_research_task(task) for task in open_tasks],
        graph_edge_summary=graph_edge_summary,
        markdown_export=markdown_export,
        message=f"Loaded research packet for idea {idea.id}.",
    )


def _research_packet_latest_artifacts(
    *,
    matrices: list[RelatedWorkMatrix],
    drafts: list[ProposalDraft],
    reviews: list[ProposalReview],
    revisions: list[ProposalRevision],
    experiment_runs: list[ExperimentRun],
    experiment_analyses: list[ExperimentAnalysis],
    decision_memos: list[IdeaDecisionMemo],
    assumption_audits: list[IdeaAssumptionAudit],
    evidence_ledgers: list[IdeaEvidenceLedger],
    research_plans: list[ResearchPlanSnapshot],
) -> dict[str, Any]:
    latest_analysis = experiment_analyses[0] if experiment_analyses else None
    latest_memo = decision_memos[0] if decision_memos else None
    latest_audit = assumption_audits[0] if assumption_audits else None
    latest_ledger = evidence_ledgers[0] if evidence_ledgers else None
    latest_plan = research_plans[0] if research_plans else None
    return {
        "related_work_matrix": {
            "id": matrices[0].id,
            "status": matrices[0].status,
            "item_count": len(matrices[0].items_json or []),
            "missing_search_count": len(matrices[0].missing_searches_json or []),
        }
        if matrices
        else None,
        "proposal_draft": {"id": drafts[0].id, "title": drafts[0].title} if drafts else None,
        "proposal_review": {
            "id": reviews[0].id,
            "decision": reviews[0].decision,
            "readiness_score": reviews[0].readiness_score,
            "concerns": (reviews[0].concerns_json or [])[:5],
        }
        if reviews
        else None,
        "proposal_revision": {"id": revisions[0].id, "status": revisions[0].status}
        if revisions
        else None,
        "experiment_run": {
            "id": experiment_runs[0].id,
            "status": experiment_runs[0].status,
            "title": experiment_runs[0].title,
        }
        if experiment_runs
        else None,
        "experiment_analysis": {
            "id": latest_analysis.id,
            "decision": latest_analysis.decision,
            "confidence": latest_analysis.confidence,
            "next_actions": (latest_analysis.next_actions_json or [])[:5],
        }
        if latest_analysis
        else None,
        "decision_memo": {
            "id": latest_memo.id,
            "decision": latest_memo.decision,
            "rationale": (latest_memo.rationale_json or [])[:5],
            "next_commitments": (latest_memo.next_commitments_json or [])[:5],
        }
        if latest_memo
        else None,
        "assumption_audit": {
            "id": latest_audit.id,
            "assumption_count": len(latest_audit.assumptions_json or []),
            "high_risk_assumptions": [
                item
                for item in (latest_audit.assumptions_json or [])
                if item.get("risk_level") == "high"
            ][:5],
        }
        if latest_audit
        else None,
        "evidence_ledger": {
            "id": latest_ledger.id,
            "coverage_score": latest_ledger.coverage_score,
            "decision_hint": (latest_ledger.summary_json or {}).get("decision_hint", ""),
            "unsupported_claim_count": (latest_ledger.summary_json or {}).get(
                "unsupported_claim_count", 0
            ),
            "missing_evidence": (latest_ledger.missing_evidence_json or [])[:5],
        }
        if latest_ledger
        else None,
        "research_plan": {
            "id": latest_plan.id,
            "title": latest_plan.title,
            "horizon_days": latest_plan.horizon_days,
            "plan_item_count": len(latest_plan.plan_items_json or []),
        }
        if latest_plan
        else None,
    }


def _render_idea_research_packet_markdown(
    *,
    idea: Idea,
    latest_artifacts: dict[str, Any],
    open_tasks: list[ResearchTask],
    graph_edge_summary: dict[str, int],
) -> str:
    lines = [
        f"# Idea Research Packet: {idea.title}",
        "",
        f"- Idea ID: `{idea.id}`",
        f"- Status: {idea.status}",
        "",
        "## Research Question",
        "",
        idea.research_question or "No research question recorded.",
        "",
        "## Core Hypothesis",
        "",
        idea.core_hypothesis or "No core hypothesis recorded.",
        "",
        "## Latest Artifacts",
        "",
    ]
    for key, value in latest_artifacts.items():
        lines.append(f"- {key}: {value if value else 'none'}")
    lines.extend(["", "## Open Tasks", ""])
    if open_tasks:
        for task in open_tasks:
            lines.append(f"- `{task.id}` `{task.priority}` `{task.status}` {task.title}")
    else:
        lines.append("- No open tasks.")
    lines.extend(["", "## Graph Edge Summary", ""])
    if graph_edge_summary:
        lines.extend(
            [f"- `{edge_type}`: {count}" for edge_type, count in graph_edge_summary.items()]
        )
    else:
        lines.append("- No graph edges found.")
    lines.extend(["", "## Packet Use", ""])
    lines.append(
        "Use this packet as the first context block for advisor discussion, MCP tools, "
        "or an external planning agent."
    )
    return "\n".join(lines).strip() + "\n"


@router.get("/ideas/{idea_id}/timeline", response_model=IdeaTimelineResponse)
def get_idea_timeline(
    idea_id: str,
    limit: int = 120,
    session: Session = Depends(get_session),
) -> IdeaTimelineResponse:
    idea = IdeaService(session).get_idea(idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")

    limit = max(10, min(limit, 300))
    events = _build_idea_timeline_events(session, idea, limit)
    markdown_export = _render_idea_timeline_markdown(idea=idea, events=events)
    return IdeaTimelineResponse(
        idea=_serialize_idea(idea),
        events=events,
        markdown_export=markdown_export,
        message=f"Loaded {len(events)} timeline events for idea {idea.id}.",
    )


def _build_idea_timeline_events(
    session: Session,
    idea: Idea,
    limit: int,
) -> list[IdeaTimelineEvent]:
    events: list[IdeaTimelineEvent] = [
        _timeline_event(
            event_type="idea_created",
            artifact_type="idea",
            artifact_id=idea.id,
            title=idea.title,
            status=idea.status,
            timestamp=idea.created_at,
            metadata={"version": idea.version, "parent_idea_id": idea.parent_idea_id},
        )
    ]

    for draft in _latest_for_idea(session, ProposalDraft, idea.id, 20):
        events.append(
            _timeline_event(
                event_type="proposal_draft_created",
                artifact_type="proposal_draft",
                artifact_id=draft.id,
                title=draft.title,
                status=draft.status,
                timestamp=draft.created_at,
                metadata={"experiment_plan_id": draft.experiment_plan_id},
            )
        )
    for review in _latest_for_idea(session, ProposalReview, idea.id, 20):
        events.append(
            _timeline_event(
                event_type="proposal_review_created",
                artifact_type="proposal_review",
                artifact_id=review.id,
                title=review.summary or review.decision,
                status=review.decision,
                timestamp=review.created_at,
                metadata={"readiness_score": review.readiness_score},
            )
        )
    for revision in _latest_for_idea(session, ProposalRevision, idea.id, 20):
        events.append(
            _timeline_event(
                event_type="proposal_revision_created",
                artifact_type="proposal_revision",
                artifact_id=revision.id,
                title=revision.revision_summary or revision.status,
                status=revision.status,
                timestamp=revision.created_at,
                metadata={
                    "proposal_draft_id": revision.proposal_draft_id,
                    "proposal_review_id": revision.proposal_review_id,
                },
            )
        )
    for run in _latest_for_idea(session, ExperimentRun, idea.id, 30):
        events.append(
            _timeline_event(
                event_type="experiment_run_recorded",
                artifact_type="experiment_run",
                artifact_id=run.id,
                title=run.title,
                status=run.status,
                timestamp=run.created_at,
                metadata={"task_id": run.task_id, "experiment_plan_id": run.experiment_plan_id},
            )
        )
    for analysis in _latest_for_idea(session, ExperimentAnalysis, idea.id, 30):
        events.append(
            _timeline_event(
                event_type="experiment_analysis_created",
                artifact_type="experiment_analysis",
                artifact_id=analysis.id,
                title=analysis.decision,
                status=analysis.decision,
                timestamp=analysis.created_at,
                metadata={
                    "confidence": analysis.confidence,
                    "experiment_run_id": analysis.experiment_run_id,
                    "task_id": analysis.task_id,
                },
            )
        )
    for memo in _latest_for_idea(session, IdeaDecisionMemo, idea.id, 20):
        events.append(
            _timeline_event(
                event_type="decision_memo_created",
                artifact_type="idea_decision_memo",
                artifact_id=memo.id,
                title=memo.decision,
                status=memo.decision,
                timestamp=memo.created_at,
                metadata={"commitment_count": len(memo.next_commitments_json or [])},
            )
        )
    for audit in _latest_for_idea(session, IdeaAssumptionAudit, idea.id, 20):
        events.append(
            _timeline_event(
                event_type="assumption_audit_created",
                artifact_type="idea_assumption_audit",
                artifact_id=audit.id,
                title=f"{len(audit.assumptions_json or [])} assumptions",
                status=audit.status,
                timestamp=audit.created_at,
                metadata={"assumption_count": len(audit.assumptions_json or [])},
            )
        )
    for ledger in _latest_for_idea(session, IdeaEvidenceLedger, idea.id, 20):
        summary = ledger.summary_json or {}
        events.append(
            _timeline_event(
                event_type="evidence_ledger_created",
                artifact_type="idea_evidence_ledger",
                artifact_id=ledger.id,
                title=f"coverage={ledger.coverage_score}",
                status=summary.get("decision_hint", ledger.status),
                timestamp=ledger.created_at,
                metadata={
                    "claim_count": summary.get("claim_count", 0),
                    "missing_evidence_count": summary.get("missing_evidence_count", 0),
                },
            )
        )
    for plan in _latest_research_plans_for_idea(session, idea.id, 20):
        events.append(
            _timeline_event(
                event_type="research_plan_created",
                artifact_type="research_plan",
                artifact_id=plan.id,
                title=plan.title,
                status=f"{plan.horizon_days}d",
                timestamp=plan.created_at,
                metadata={"plan_item_count": len(plan.plan_items_json or [])},
            )
        )

    task_ids = [task.id for task in _latest_for_idea(session, ResearchTask, idea.id, 200)]
    if task_ids:
        task_events = (
            session.query(ResearchTaskEvent)
            .filter(ResearchTaskEvent.task_id.in_(task_ids))
            .order_by(ResearchTaskEvent.created_at.desc())
            .limit(300)
            .all()
        )
        for event in task_events:
            events.append(
                _timeline_event(
                    event_type=f"task_{event.event_type}",
                    artifact_type="research_task_event",
                    artifact_id=event.id,
                    title=event.note or f"Task event for {event.task_id}",
                    status=event.status_to,
                    timestamp=event.created_at,
                    metadata={
                        "task_id": event.task_id,
                        "priority_to": event.priority_to,
                        **(event.metadata_json or {}),
                    },
                )
            )

    return sorted(events, key=lambda event: event.timestamp, reverse=True)[:limit]


def _timeline_event(
    *,
    event_type: str,
    artifact_type: str,
    artifact_id: str,
    title: str,
    status: str,
    timestamp: datetime,
    metadata: dict[str, Any] | None = None,
) -> IdeaTimelineEvent:
    return IdeaTimelineEvent(
        event_type=event_type,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        title=" ".join(str(title or artifact_id).split())[:180],
        status=status or "",
        timestamp=timestamp,
        metadata=metadata or {},
    )


def _render_idea_timeline_markdown(
    *,
    idea: Idea,
    events: list[IdeaTimelineEvent],
) -> str:
    lines = [
        f"# Idea Timeline: {idea.title}",
        "",
        f"- Idea ID: `{idea.id}`",
        f"- Event Count: {len(events)}",
        "",
        "## Events",
        "",
    ]
    if not events:
        lines.append("- No events recorded.")
    for event in events:
        lines.append(
            f"- `{event.timestamp.isoformat()}` `{event.event_type}` "
            f"`{event.artifact_type}` `{event.artifact_id}` {event.title}"
        )
    return "\n".join(lines).strip() + "\n"


@router.get("/ideas/{idea_id}/readiness", response_model=IdeaReadinessResponse)
def get_idea_readiness(
    idea_id: str,
    session: Session = Depends(get_session),
) -> IdeaReadinessResponse:
    idea = IdeaService(session).get_idea(idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")

    matrices = _latest_for_idea(session, RelatedWorkMatrix, idea_id, 5)
    drafts = _latest_for_idea(session, ProposalDraft, idea_id, 5)
    reviews = _latest_for_idea(session, ProposalReview, idea_id, 5)
    experiment_plans = _latest_for_idea(session, ExperimentPlan, idea_id, 5)
    experiment_runs = _latest_for_idea(session, ExperimentRun, idea_id, 5)
    experiment_analyses = _latest_for_idea(session, ExperimentAnalysis, idea_id, 5)
    decision_memos = _latest_for_idea(session, IdeaDecisionMemo, idea_id, 5)
    assumption_audits = _latest_for_idea(session, IdeaAssumptionAudit, idea_id, 5)
    novelty_checks = _latest_for_idea(session, NoveltyCheck, idea_id, 5)
    tasks = _latest_for_idea(session, ResearchTask, idea_id, 200)

    latest_matrix = matrices[0] if matrices else None
    latest_review = reviews[0] if reviews else None
    latest_analysis = experiment_analyses[0] if experiment_analyses else None
    latest_memo = decision_memos[0] if decision_memos else None
    latest_audit = assumption_audits[0] if assumption_audits else None
    latest_novelty = novelty_checks[0] if novelty_checks else None

    evidence_count = len(idea.evidence_ids_json or [])
    missing_search_count = len(latest_matrix.missing_searches_json or []) if latest_matrix else 0
    high_risk_assumptions = [
        item
        for item in (latest_audit.assumptions_json if latest_audit else [])
        if item.get("risk_level") == "high"
    ]
    open_tasks = [task for task in tasks if task.status in {"todo", "doing", "blocked"}]
    blocked_tasks = [task for task in tasks if task.status == "blocked"]

    breakdown = {
        "evidence": {
            "score": _clamp(evidence_count / 3),
            "signal": f"{evidence_count} linked evidence records",
            "weight": 0.15,
        },
        "novelty": {
            "score": _readiness_novelty_score(latest_matrix, latest_novelty),
            "signal": _readiness_novelty_signal(latest_matrix, latest_novelty),
            "weight": 0.15,
        },
        "proposal": {
            "score": latest_review.readiness_score if latest_review else (0.45 if drafts else 0.1),
            "signal": latest_review.decision if latest_review else "no proposal review",
            "weight": 0.18,
        },
        "experiment": {
            "score": latest_analysis.confidence
            if latest_analysis
            else (0.45 if experiment_runs else (0.3 if experiment_plans else 0.1)),
            "signal": latest_analysis.decision if latest_analysis else "no experiment analysis",
            "weight": 0.18,
        },
        "decision": {
            "score": _readiness_decision_score(latest_memo),
            "signal": latest_memo.decision if latest_memo else "no decision memo",
            "weight": 0.14,
        },
        "assumptions": {
            "score": _readiness_assumption_score(latest_audit),
            "signal": f"{len(high_risk_assumptions)} high-risk assumptions",
            "weight": 0.12,
        },
        "task_health": {
            "score": _readiness_task_score(open_tasks, blocked_tasks),
            "signal": f"{len(blocked_tasks)} blocked of {len(open_tasks)} open tasks",
            "weight": 0.08,
        },
    }
    readiness_score = round(
        sum(item["score"] * item["weight"] for item in breakdown.values()),
        4,
    )
    blockers = _readiness_blockers(
        latest_matrix=latest_matrix,
        latest_review=latest_review,
        latest_analysis=latest_analysis,
        latest_memo=latest_memo,
        latest_audit=latest_audit,
        blocked_tasks=blocked_tasks,
        missing_search_count=missing_search_count,
        high_risk_assumptions=high_risk_assumptions,
    )
    decision = _readiness_decision(readiness_score, latest_memo, blockers)
    markdown_export = _render_idea_readiness_markdown(
        idea=idea,
        readiness_score=readiness_score,
        decision=decision,
        breakdown=breakdown,
        blockers=blockers,
    )
    return IdeaReadinessResponse(
        idea=_serialize_idea(idea),
        readiness_score=readiness_score,
        decision=decision,
        score_breakdown=breakdown,
        blockers=blockers,
        markdown_export=markdown_export,
        message=f"Scored readiness for idea {idea.id}.",
    )


@router.post("/ideas/{idea_id}/readiness/tasks", response_model=ResearchTaskGenerationResponse)
def create_tasks_from_idea_readiness(
    idea_id: str,
    payload: ResearchTaskGenerateRequest,
    session: Session = Depends(get_session),
) -> ResearchTaskGenerationResponse:
    readiness = get_idea_readiness(idea_id, session=session)
    try:
        tasks = ResearchTaskService(session).create_from_idea_readiness(
            idea_id,
            blockers=readiness.blockers,
            readiness_score=readiness.readiness_score,
            decision=readiness.decision,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ResearchTaskGenerationResponse(
        tasks=[_serialize_research_task(task) for task in tasks],
        message=f"Created {len(tasks)} readiness follow-up tasks for idea {idea_id}.",
    )


def _clamp(value: float) -> float:
    return round(max(0.0, min(float(value), 1.0)), 4)


def _readiness_novelty_score(
    matrix: RelatedWorkMatrix | None,
    novelty: NoveltyCheck | None,
) -> float:
    if matrix is None and novelty is None:
        return 0.15
    score = 0.75
    if matrix:
        score += 0.2
        score -= min(len(matrix.missing_searches_json or []) * 0.04, 0.35)
    if novelty:
        risk_penalty = {"low": 0.0, "medium": 0.15, "high": 0.35, "unknown": 0.2}
        score -= risk_penalty.get(novelty.risk_level, 0.15)
    return _clamp(score)


def _readiness_novelty_signal(
    matrix: RelatedWorkMatrix | None,
    novelty: NoveltyCheck | None,
) -> str:
    pieces = []
    if matrix:
        pieces.append(
            f"{len(matrix.items_json or [])} related rows; "
            f"{len(matrix.missing_searches_json or [])} missing searches"
        )
    if novelty:
        pieces.append(f"novelty risk={novelty.risk_level}")
    return "; ".join(pieces) if pieces else "no novelty screen"


def _readiness_decision_score(memo: IdeaDecisionMemo | None) -> float:
    if memo is None:
        return 0.25
    return {"pursue": 1.0, "revise": 0.65, "park": 0.25, "reject": 0.0}.get(
        memo.decision,
        0.5,
    )


def _readiness_assumption_score(audit: IdeaAssumptionAudit | None) -> float:
    if audit is None:
        return 0.25
    assumptions = audit.assumptions_json or []
    if not assumptions:
        return 0.35
    high = len([item for item in assumptions if item.get("risk_level") == "high"])
    medium = len([item for item in assumptions if item.get("risk_level") == "medium"])
    penalty = min((high * 0.16) + (medium * 0.04), 0.8)
    return _clamp(1.0 - penalty)


def _readiness_task_score(
    open_tasks: list[ResearchTask],
    blocked_tasks: list[ResearchTask],
) -> float:
    if not open_tasks:
        return 0.45
    return _clamp(1.0 - (len(blocked_tasks) / len(open_tasks)))


def _readiness_blockers(
    *,
    latest_matrix: RelatedWorkMatrix | None,
    latest_review: ProposalReview | None,
    latest_analysis: ExperimentAnalysis | None,
    latest_memo: IdeaDecisionMemo | None,
    latest_audit: IdeaAssumptionAudit | None,
    blocked_tasks: list[ResearchTask],
    missing_search_count: int,
    high_risk_assumptions: list[dict],
) -> list[str]:
    blockers = []
    if latest_matrix is None:
        blockers.append("No related-work matrix has been generated.")
    elif missing_search_count:
        blockers.append(f"{missing_search_count} related-work searches are still missing.")
    if latest_review is None:
        blockers.append("No proposal readiness review has been recorded.")
    if latest_analysis is None:
        blockers.append("No experiment analysis has tested the latest execution signal.")
    if latest_memo is None:
        blockers.append("No decision memo records whether to pursue, revise, park, or reject.")
    elif latest_memo.decision in {"park", "reject"}:
        blockers.append(f"Latest decision memo says to {latest_memo.decision}.")
    if latest_audit is None:
        blockers.append("No assumption audit has exposed falsification conditions.")
    if high_risk_assumptions:
        blockers.append(f"{len(high_risk_assumptions)} high-risk assumptions remain open.")
    for task in blocked_tasks[:5]:
        blockers.append(f"Blocked task: {task.title}")
    return blockers[:12]


def _readiness_decision(
    readiness_score: float,
    memo: IdeaDecisionMemo | None,
    blockers: list[str],
) -> str:
    if memo and memo.decision in {"reject", "park"}:
        return memo.decision
    if readiness_score >= 0.75 and len(blockers) <= 2:
        return "ready_for_execution"
    if readiness_score >= 0.55:
        return "needs_targeted_work"
    return "needs_work"


def _render_idea_readiness_markdown(
    *,
    idea: Idea,
    readiness_score: float,
    decision: str,
    breakdown: dict[str, Any],
    blockers: list[str],
) -> str:
    lines = [
        f"# Idea Readiness: {idea.title}",
        "",
        f"- Idea ID: `{idea.id}`",
        f"- Readiness Score: {readiness_score:.4f}",
        f"- Decision: `{decision}`",
        "",
        "## Score Breakdown",
        "",
    ]
    for key, item in breakdown.items():
        lines.append(
            f"- {key}: score={item['score']:.4f} weight={item['weight']} signal={item['signal']}"
        )
    lines.extend(["", "## Blockers", ""])
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- No blocking readiness gaps found.")
    return "\n".join(lines).strip() + "\n"


@router.get("/ideas/{idea_id}/quality-gate", response_model=IdeaQualityGateResponse)
def get_idea_quality_gate(
    idea_id: str,
    session: Session = Depends(get_session),
) -> IdeaQualityGateResponse:
    idea = IdeaService(session).get_idea(idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")

    readiness = get_idea_readiness(idea_id, session=session)
    progress = get_idea_progress(idea_id, session=session)
    novelty_checks = _latest_for_idea(session, NoveltyCheck, idea_id, 5)
    reviews = _latest_for_idea(session, ProposalReview, idea_id, 5)
    experiment_analyses = _latest_for_idea(session, ExperimentAnalysis, idea_id, 5)
    decision_memos = _latest_for_idea(session, IdeaDecisionMemo, idea_id, 5)
    assumption_audits = _latest_for_idea(session, IdeaAssumptionAudit, idea_id, 5)
    tasks = _latest_for_idea(session, ResearchTask, idea_id, 200)

    latest_novelty = novelty_checks[0] if novelty_checks else None
    latest_review = reviews[0] if reviews else None
    latest_analysis = experiment_analyses[0] if experiment_analyses else None
    latest_memo = decision_memos[0] if decision_memos else None
    latest_audit = assumption_audits[0] if assumption_audits else None
    open_tasks = [task for task in tasks if task.status in {"todo", "doing", "blocked"}]
    blocked_tasks = [task for task in tasks if task.status == "blocked"]
    high_risk_assumptions = [
        item
        for item in (latest_audit.assumptions_json if latest_audit else [])
        if item.get("risk_level") == "high"
    ]

    score_breakdown = _quality_gate_breakdown(
        readiness=readiness,
        latest_novelty=latest_novelty,
        latest_review=latest_review,
        latest_analysis=latest_analysis,
        latest_memo=latest_memo,
        open_tasks=open_tasks,
        blocked_tasks=blocked_tasks,
    )
    gate_score = round(
        sum(item["score"] * item["weight"] for item in score_breakdown.values()),
        4,
    )
    required_evidence = _quality_gate_required_evidence(
        latest_novelty=latest_novelty,
        latest_review=latest_review,
        latest_analysis=latest_analysis,
        latest_memo=latest_memo,
        latest_audit=latest_audit,
    )
    blocking_risks = _quality_gate_blocking_risks(
        readiness=readiness,
        latest_novelty=latest_novelty,
        latest_memo=latest_memo,
        high_risk_assumptions=high_risk_assumptions,
        blocked_tasks=blocked_tasks,
        required_evidence=required_evidence,
    )
    decision = _quality_gate_decision(
        gate_score=gate_score,
        latest_novelty=latest_novelty,
        latest_memo=latest_memo,
        blocking_risks=blocking_risks,
    )
    recommended_actions = _quality_gate_recommended_actions(
        decision=decision,
        readiness=readiness,
        latest_novelty=latest_novelty,
        required_evidence=required_evidence,
        blocked_tasks=blocked_tasks,
    )
    latest_artifacts = {
        "novelty_check": _quality_artifact(latest_novelty, ["status", "risk_level"]),
        "proposal_review": _quality_artifact(latest_review, ["decision", "readiness_score"]),
        "experiment_analysis": _quality_artifact(latest_analysis, ["decision", "confidence"]),
        "decision_memo": _quality_artifact(latest_memo, ["decision"]),
        "assumption_audit": _quality_artifact(latest_audit, ["status"]),
        "progress": {
            "recommended_next_step": progress.recommended_next_step,
            "open_tasks": progress.artifact_counts.get("open_tasks", 0),
            "blocked_tasks": progress.artifact_counts.get("blocked_tasks", 0),
        },
    }
    markdown_export = _render_idea_quality_gate_markdown(
        idea=idea,
        gate_score=gate_score,
        decision=decision,
        score_breakdown=score_breakdown,
        required_evidence=required_evidence,
        blocking_risks=blocking_risks,
        recommended_actions=recommended_actions,
        latest_artifacts=latest_artifacts,
    )
    return IdeaQualityGateResponse(
        idea=_serialize_idea(idea),
        gate_score=gate_score,
        decision=decision,
        score_breakdown=score_breakdown,
        required_evidence=required_evidence,
        blocking_risks=blocking_risks,
        recommended_actions=recommended_actions,
        latest_artifacts=latest_artifacts,
        markdown_export=markdown_export,
        message=f"Ran idea quality gate for idea {idea.id}.",
    )


@router.post("/ideas/{idea_id}/quality-gate/tasks", response_model=ResearchTaskGenerationResponse)
def create_tasks_from_idea_quality_gate(
    idea_id: str,
    payload: ResearchTaskGenerateRequest,
    session: Session = Depends(get_session),
) -> ResearchTaskGenerationResponse:
    quality_gate = get_idea_quality_gate(idea_id, session=session)
    missing_evidence_count = len(
        [item for item in quality_gate.required_evidence if not item.get("satisfied")]
    )
    try:
        tasks = ResearchTaskService(session).create_from_idea_quality_gate(
            idea_id,
            gate_score=quality_gate.gate_score,
            decision=quality_gate.decision,
            recommended_actions=quality_gate.recommended_actions,
            blocking_risks=quality_gate.blocking_risks,
            missing_evidence_count=missing_evidence_count,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ResearchTaskGenerationResponse(
        tasks=[_serialize_research_task(task) for task in tasks],
        message=f"Created {len(tasks)} quality-gate follow-up tasks for idea {idea_id}.",
    )


def _quality_gate_breakdown(
    *,
    readiness: IdeaReadinessResponse,
    latest_novelty: NoveltyCheck | None,
    latest_review: ProposalReview | None,
    latest_analysis: ExperimentAnalysis | None,
    latest_memo: IdeaDecisionMemo | None,
    open_tasks: list[ResearchTask],
    blocked_tasks: list[ResearchTask],
) -> dict[str, dict[str, Any]]:
    return {
        "readiness": {
            "score": readiness.readiness_score,
            "weight": 0.32,
            "signal": readiness.decision,
        },
        "novelty": {
            "score": _quality_novelty_score(latest_novelty),
            "weight": 0.2,
            "signal": latest_novelty.risk_level if latest_novelty else "no novelty check",
        },
        "proposal": {
            "score": latest_review.readiness_score if latest_review else 0.15,
            "weight": 0.16,
            "signal": latest_review.decision if latest_review else "no proposal review",
        },
        "experiment": {
            "score": latest_analysis.confidence if latest_analysis else 0.2,
            "weight": 0.14,
            "signal": latest_analysis.decision if latest_analysis else "no experiment analysis",
        },
        "decision": {
            "score": _readiness_decision_score(latest_memo),
            "weight": 0.1,
            "signal": latest_memo.decision if latest_memo else "no decision memo",
        },
        "task_health": {
            "score": _readiness_task_score(open_tasks, blocked_tasks),
            "weight": 0.08,
            "signal": f"{len(blocked_tasks)} blocked of {len(open_tasks)} open tasks",
        },
    }


def _quality_novelty_score(novelty: NoveltyCheck | None) -> float:
    if novelty is None:
        return 0.15
    base = {"low": 0.95, "medium": 0.55, "high": 0.2, "unknown": 0.35}.get(
        novelty.risk_level,
        0.35,
    )
    if novelty.status == "completed_external_novelty_refresh":
        base += 0.05
    if novelty.missing_searches_json:
        base -= min(len(novelty.missing_searches_json) * 0.03, 0.18)
    return _clamp(base)


def _quality_gate_required_evidence(
    *,
    latest_novelty: NoveltyCheck | None,
    latest_review: ProposalReview | None,
    latest_analysis: ExperimentAnalysis | None,
    latest_memo: IdeaDecisionMemo | None,
    latest_audit: IdeaAssumptionAudit | None,
) -> list[dict[str, Any]]:
    checks = [
        ("novelty_refresh", latest_novelty is not None, "Refresh novelty/collision signals."),
        ("proposal_review", latest_review is not None, "Run proposal readiness review."),
        (
            "experiment_analysis",
            latest_analysis is not None,
            "Analyze at least one experiment run.",
        ),
        ("decision_memo", latest_memo is not None, "Record pursue/revise/park/reject decision."),
        ("assumption_audit", latest_audit is not None, "Audit falsifiable assumptions."),
    ]
    return [
        {"name": name, "satisfied": satisfied, "action": action}
        for name, satisfied, action in checks
    ]


def _quality_gate_blocking_risks(
    *,
    readiness: IdeaReadinessResponse,
    latest_novelty: NoveltyCheck | None,
    latest_memo: IdeaDecisionMemo | None,
    high_risk_assumptions: list[dict],
    blocked_tasks: list[ResearchTask],
    required_evidence: list[dict[str, Any]],
) -> list[str]:
    risks = []
    if latest_novelty is None:
        risks.append("No novelty refresh or collision screen is available.")
    elif latest_novelty.risk_level == "high":
        risks.append("Latest novelty screen reports high collision risk.")
    elif latest_novelty.missing_searches_json:
        risks.append(
            f"{len(latest_novelty.missing_searches_json)} novelty searches remain missing."
        )
    if latest_memo and latest_memo.decision in {"park", "reject"}:
        risks.append(f"Latest decision memo says to {latest_memo.decision}.")
    if high_risk_assumptions:
        risks.append(f"{len(high_risk_assumptions)} high-risk assumptions remain open.")
    for blocker in readiness.blockers[:3]:
        risks.append(blocker)
    for task in blocked_tasks[:3]:
        risks.append(f"Blocked task: {task.title}")
    for item in required_evidence:
        if not item["satisfied"]:
            risks.append(f"Missing gate evidence: {item['name']}.")
    return list(dict.fromkeys(risks))[:12]


def _quality_gate_decision(
    *,
    gate_score: float,
    latest_novelty: NoveltyCheck | None,
    latest_memo: IdeaDecisionMemo | None,
    blocking_risks: list[str],
) -> str:
    if latest_memo and latest_memo.decision in {"reject", "park"}:
        return latest_memo.decision
    if latest_novelty and latest_novelty.risk_level == "high":
        return "de_risk_novelty"
    if gate_score >= 0.76 and len(blocking_risks) <= 2:
        return "advance_to_execution"
    if gate_score >= 0.58:
        return "needs_targeted_revision"
    return "revise_before_investment"


def _quality_gate_recommended_actions(
    *,
    decision: str,
    readiness: IdeaReadinessResponse,
    latest_novelty: NoveltyCheck | None,
    required_evidence: list[dict[str, Any]],
    blocked_tasks: list[ResearchTask],
) -> list[str]:
    actions = []
    for item in required_evidence:
        if not item["satisfied"]:
            actions.append(item["action"])
    if latest_novelty and latest_novelty.risk_level in {"medium", "high", "unknown"}:
        actions.extend(latest_novelty.recommended_actions_json[:3])
    actions.extend(f"Clear readiness blocker: {blocker}" for blocker in readiness.blockers[:3])
    actions.extend(f"Unblock task `{task.id}`: {task.title}" for task in blocked_tasks[:3])
    if decision == "advance_to_execution":
        actions.insert(0, "Create or refresh a 14-day execution plan for this idea.")
    if not actions:
        actions.append("Create an advisor brief and lock the next experimental commitment.")
    return list(dict.fromkeys(actions))[:8]


def _quality_artifact(artifact: Any, fields: list[str]) -> dict[str, Any] | None:
    if artifact is None:
        return None
    payload = {"id": artifact.id}
    for field in fields:
        payload[field] = getattr(artifact, field, None)
    return payload


def _render_idea_quality_gate_markdown(
    *,
    idea: Idea,
    gate_score: float,
    decision: str,
    score_breakdown: dict[str, Any],
    required_evidence: list[dict[str, Any]],
    blocking_risks: list[str],
    recommended_actions: list[str],
    latest_artifacts: dict[str, Any],
) -> str:
    lines = [
        f"# Idea Quality Gate: {idea.title}",
        "",
        f"- Idea ID: `{idea.id}`",
        f"- Gate Score: {gate_score:.4f}",
        f"- Decision: `{decision}`",
        "",
        "## Score Breakdown",
        "",
    ]
    for name, item in score_breakdown.items():
        lines.append(
            f"- {name}: score={item['score']:.4f} weight={item['weight']} signal={item['signal']}"
        )
    lines.extend(["", "## Required Evidence", ""])
    for item in required_evidence:
        mark = "yes" if item["satisfied"] else "no"
        lines.append(f"- `{mark}` {item['name']}: {item['action']}")
    lines.extend(["", "## Blocking Risks", ""])
    if blocking_risks:
        lines.extend(f"- {risk}" for risk in blocking_risks)
    else:
        lines.append("- No blocking risks detected by the gate.")
    lines.extend(["", "## Recommended Actions", ""])
    lines.extend(f"- {action}" for action in recommended_actions)
    lines.extend(["", "## Latest Artifacts", ""])
    for name, artifact in latest_artifacts.items():
        lines.append(f"- {name}: `{artifact or 'missing'}`")
    return "\n".join(lines).strip() + "\n"


@router.get("/quality/overview", response_model=ProjectQualityGateOverviewResponse)
def get_project_quality_gate_overview(
    limit: int = 50,
    session: Session = Depends(get_session),
) -> ProjectQualityGateOverviewResponse:
    limit = max(1, min(limit, 200))
    ideas = session.query(Idea).order_by(Idea.updated_at.desc()).limit(limit).all()
    summaries = [_quality_gate_summary_for_idea(session, idea) for idea in ideas]
    average_gate_score = (
        round(sum(item.gate_score for item in summaries) / len(summaries), 4) if summaries else 0.0
    )
    decision_counts = dict(Counter(item.decision for item in summaries))
    advance_candidates = _quality_gate_candidates(
        summaries,
        decisions={"advance_to_execution"},
        reverse=True,
    )
    de_risk_candidates = _quality_gate_candidates(
        summaries,
        decisions={"de_risk_novelty"},
        reverse=False,
    )
    revision_candidates = _quality_gate_candidates(
        summaries,
        decisions={"needs_targeted_revision", "revise_before_investment"},
        reverse=False,
    )
    parked_or_rejected = _quality_gate_candidates(
        summaries,
        decisions={"park", "reject"},
        reverse=False,
    )
    markdown_export = _render_project_quality_gate_overview_markdown(
        idea_count=len(summaries),
        average_gate_score=average_gate_score,
        decision_counts=decision_counts,
        advance_candidates=advance_candidates,
        de_risk_candidates=de_risk_candidates,
        revision_candidates=revision_candidates,
        parked_or_rejected=parked_or_rejected,
    )
    return ProjectQualityGateOverviewResponse(
        idea_count=len(summaries),
        average_gate_score=average_gate_score,
        decision_counts=decision_counts,
        advance_candidates=advance_candidates,
        de_risk_candidates=de_risk_candidates,
        revision_candidates=revision_candidates,
        parked_or_rejected=parked_or_rejected,
        markdown_export=markdown_export,
        message=f"Ran project quality gate overview for {len(summaries)} ideas.",
    )


@router.post("/quality/overview/tasks", response_model=ResearchTaskGenerationResponse)
def create_tasks_from_project_quality_gate(
    payload: ProjectQualityGateTaskGenerateRequest,
    session: Session = Depends(get_session),
) -> ResearchTaskGenerationResponse:
    overview_limit = max(payload.limit * 5, payload.limit)
    overview = get_project_quality_gate_overview(limit=overview_limit, session=session)
    target_decisions = set(
        payload.decisions
        or [
            "de_risk_novelty",
            "needs_targeted_revision",
            "revise_before_investment",
        ]
    )
    candidates = _project_quality_gate_task_candidates(overview, target_decisions, payload.limit)
    service = ResearchTaskService(session)
    tasks: list[ResearchTask] = []
    for candidate in candidates:
        quality_gate = get_idea_quality_gate(candidate.idea_id, session=session)
        missing_evidence_count = len(
            [item for item in quality_gate.required_evidence if not item.get("satisfied")]
        )
        tasks.extend(
            service.create_from_idea_quality_gate(
                candidate.idea_id,
                gate_score=quality_gate.gate_score,
                decision=quality_gate.decision,
                recommended_actions=quality_gate.recommended_actions[: payload.actions_per_idea],
                blocking_risks=quality_gate.blocking_risks,
                missing_evidence_count=missing_evidence_count,
                created_by=payload.created_by,
            )
        )
    return ResearchTaskGenerationResponse(
        tasks=[_serialize_research_task(task) for task in tasks],
        message=(
            f"Created {len(tasks)} quality-gate follow-up tasks "
            f"from {len(candidates)} project candidates."
        ),
    )


def _project_quality_gate_task_candidates(
    overview: ProjectQualityGateOverviewResponse,
    target_decisions: set[str],
    limit: int,
) -> list[IdeaQualityGateSummary]:
    ordered = [
        *overview.de_risk_candidates,
        *overview.revision_candidates,
        *overview.parked_or_rejected,
        *overview.advance_candidates,
    ]
    candidates: list[IdeaQualityGateSummary] = []
    seen: set[str] = set()
    for item in ordered:
        if item.idea_id in seen or item.decision not in target_decisions:
            continue
        candidates.append(item)
        seen.add(item.idea_id)
        if len(candidates) >= limit:
            break
    return candidates


def _quality_gate_summary_for_idea(session: Session, idea: Idea) -> IdeaQualityGateSummary:
    quality_gate = get_idea_quality_gate(idea.id, session=session)
    missing_evidence = [
        item for item in quality_gate.required_evidence if not item.get("satisfied")
    ]
    return IdeaQualityGateSummary(
        idea_id=idea.id,
        title=idea.title,
        status=idea.status,
        gate_score=quality_gate.gate_score,
        decision=quality_gate.decision,
        missing_evidence_count=len(missing_evidence),
        blocking_risk_count=len(quality_gate.blocking_risks),
        top_risks=quality_gate.blocking_risks[:3],
        top_actions=quality_gate.recommended_actions[:3],
    )


def _quality_gate_candidates(
    summaries: list[IdeaQualityGateSummary],
    *,
    decisions: set[str],
    reverse: bool,
) -> list[IdeaQualityGateSummary]:
    items = [item for item in summaries if item.decision in decisions]
    return sorted(
        items,
        key=lambda item: (item.gate_score, -item.blocking_risk_count),
        reverse=reverse,
    )[:10]


def _render_project_quality_gate_overview_markdown(
    *,
    idea_count: int,
    average_gate_score: float,
    decision_counts: dict[str, int],
    advance_candidates: list[IdeaQualityGateSummary],
    de_risk_candidates: list[IdeaQualityGateSummary],
    revision_candidates: list[IdeaQualityGateSummary],
    parked_or_rejected: list[IdeaQualityGateSummary],
) -> str:
    lines = [
        "# Project Quality Gate Overview",
        "",
        f"- Idea Count: {idea_count}",
        f"- Average Gate Score: {average_gate_score:.4f}",
        f"- Decision Counts: {decision_counts}",
        "",
    ]
    _append_quality_gate_section(lines, "Advance Candidates", advance_candidates)
    _append_quality_gate_section(lines, "De-risk Candidates", de_risk_candidates)
    _append_quality_gate_section(lines, "Revision Candidates", revision_candidates)
    _append_quality_gate_section(lines, "Parked Or Rejected", parked_or_rejected)
    return "\n".join(lines).strip() + "\n"


def _append_quality_gate_section(
    lines: list[str],
    title: str,
    items: list[IdeaQualityGateSummary],
) -> None:
    lines.extend([f"## {title}", ""])
    if not items:
        lines.append("- No ideas in this bucket.")
    for item in items:
        top_action = item.top_actions[0] if item.top_actions else "No action generated."
        lines.append(
            f"- `{item.idea_id}` score={item.gate_score:.4f} `{item.decision}` "
            f"missing={item.missing_evidence_count} risks={item.blocking_risk_count} "
            f"{item.title} - {top_action}"
        )
    lines.append("")


@router.get("/readiness/overview", response_model=ProjectReadinessOverviewResponse)
def get_project_readiness_overview(
    limit: int = 50,
    session: Session = Depends(get_session),
) -> ProjectReadinessOverviewResponse:
    limit = max(1, min(limit, 200))
    ideas = session.query(Idea).order_by(Idea.updated_at.desc()).limit(limit).all()
    summaries = [_readiness_summary_for_idea(session, idea) for idea in ideas]
    average_readiness = (
        round(sum(item.readiness_score for item in summaries) / len(summaries), 4)
        if summaries
        else 0.0
    )
    decision_counts = dict(Counter(item.decision for item in summaries))
    top_ready = sorted(summaries, key=lambda item: item.readiness_score, reverse=True)[:10]
    needs_work = sorted(
        [
            item
            for item in summaries
            if item.decision in {"needs_work", "needs_targeted_work", "park", "reject"}
        ],
        key=lambda item: (item.readiness_score, -item.blocker_count),
    )[:10]
    markdown_export = _render_project_readiness_overview_markdown(
        idea_count=len(summaries),
        average_readiness=average_readiness,
        decision_counts=decision_counts,
        top_ready=top_ready,
        needs_work=needs_work,
    )
    return ProjectReadinessOverviewResponse(
        idea_count=len(summaries),
        average_readiness=average_readiness,
        decision_counts=decision_counts,
        top_ready=top_ready,
        needs_work=needs_work,
        markdown_export=markdown_export,
        message=f"Scored readiness for {len(summaries)} ideas.",
    )


def _readiness_summary_for_idea(session: Session, idea: Idea) -> IdeaReadinessSummary:
    matrices = _latest_for_idea(session, RelatedWorkMatrix, idea.id, 1)
    drafts = _latest_for_idea(session, ProposalDraft, idea.id, 1)
    reviews = _latest_for_idea(session, ProposalReview, idea.id, 1)
    experiment_plans = _latest_for_idea(session, ExperimentPlan, idea.id, 1)
    experiment_runs = _latest_for_idea(session, ExperimentRun, idea.id, 1)
    experiment_analyses = _latest_for_idea(session, ExperimentAnalysis, idea.id, 1)
    decision_memos = _latest_for_idea(session, IdeaDecisionMemo, idea.id, 1)
    assumption_audits = _latest_for_idea(session, IdeaAssumptionAudit, idea.id, 1)
    novelty_checks = _latest_for_idea(session, NoveltyCheck, idea.id, 1)
    tasks = _latest_for_idea(session, ResearchTask, idea.id, 200)

    latest_matrix = matrices[0] if matrices else None
    latest_review = reviews[0] if reviews else None
    latest_analysis = experiment_analyses[0] if experiment_analyses else None
    latest_memo = decision_memos[0] if decision_memos else None
    latest_audit = assumption_audits[0] if assumption_audits else None
    latest_novelty = novelty_checks[0] if novelty_checks else None
    open_tasks = [task for task in tasks if task.status in {"todo", "doing", "blocked"}]
    blocked_tasks = [task for task in tasks if task.status == "blocked"]
    missing_search_count = len(latest_matrix.missing_searches_json or []) if latest_matrix else 0
    high_risk_assumptions = [
        item
        for item in (latest_audit.assumptions_json if latest_audit else [])
        if item.get("risk_level") == "high"
    ]
    breakdown = {
        "evidence": {"score": _clamp(len(idea.evidence_ids_json or []) / 3), "weight": 0.15},
        "novelty": {
            "score": _readiness_novelty_score(latest_matrix, latest_novelty),
            "weight": 0.15,
        },
        "proposal": {
            "score": latest_review.readiness_score if latest_review else (0.45 if drafts else 0.1),
            "weight": 0.18,
        },
        "experiment": {
            "score": latest_analysis.confidence
            if latest_analysis
            else (0.45 if experiment_runs else (0.3 if experiment_plans else 0.1)),
            "weight": 0.18,
        },
        "decision": {"score": _readiness_decision_score(latest_memo), "weight": 0.14},
        "assumptions": {"score": _readiness_assumption_score(latest_audit), "weight": 0.12},
        "task_health": {
            "score": _readiness_task_score(open_tasks, blocked_tasks),
            "weight": 0.08,
        },
    }
    readiness_score = round(
        sum(item["score"] * item["weight"] for item in breakdown.values()),
        4,
    )
    blockers = _readiness_blockers(
        latest_matrix=latest_matrix,
        latest_review=latest_review,
        latest_analysis=latest_analysis,
        latest_memo=latest_memo,
        latest_audit=latest_audit,
        blocked_tasks=blocked_tasks,
        missing_search_count=missing_search_count,
        high_risk_assumptions=high_risk_assumptions,
    )
    return IdeaReadinessSummary(
        idea_id=idea.id,
        title=idea.title,
        status=idea.status,
        readiness_score=readiness_score,
        decision=_readiness_decision(readiness_score, latest_memo, blockers),
        blocker_count=len(blockers),
        top_blockers=blockers[:3],
    )


def _render_project_readiness_overview_markdown(
    *,
    idea_count: int,
    average_readiness: float,
    decision_counts: dict[str, int],
    top_ready: list[IdeaReadinessSummary],
    needs_work: list[IdeaReadinessSummary],
) -> str:
    lines = [
        "# Project Readiness Overview",
        "",
        f"- Idea Count: {idea_count}",
        f"- Average Readiness: {average_readiness:.4f}",
        f"- Decision Counts: {decision_counts}",
        "",
        "## Top Ready Ideas",
        "",
    ]
    if top_ready:
        for item in top_ready:
            lines.append(
                f"- `{item.idea_id}` score={item.readiness_score:.4f} "
                f"`{item.decision}` {item.title}"
            )
    else:
        lines.append("- No ideas scored.")
    lines.extend(["", "## Needs Work", ""])
    if needs_work:
        for item in needs_work:
            blocker = item.top_blockers[0] if item.top_blockers else "No blocker summary."
            lines.append(
                f"- `{item.idea_id}` score={item.readiness_score:.4f} "
                f"`{item.decision}` {item.title} - {blocker}"
            )
    else:
        lines.append("- No needs-work ideas found.")
    return "\n".join(lines).strip() + "\n"


@router.get("/opportunities/radar", response_model=ResearchOpportunityRadarResponse)
def get_research_opportunity_radar(
    limit: int = 10,
    session: Session = Depends(get_session),
) -> ResearchOpportunityRadarResponse:
    limit = max(1, min(limit, 50))
    profile = ResearchProfileService(session).get_profile()
    ranked = IdeaRankingService(session).rank_ideas(
        limit=max(limit * 2, limit),
        deduplicate_lineage=True,
    )
    items = []
    for ranked_item in ranked:
        readiness = _readiness_summary_for_idea(session, ranked_item.idea)
        task_signals = _radar_task_signals(session, ranked_item.idea.id)
        items.append(_build_research_opportunity_item(ranked_item, readiness, task_signals))

    items.sort(key=lambda item: item.radar_score, reverse=True)
    top_opportunities = items[:limit]
    risk_watchlist = [
        item
        for item in top_opportunities
        if item.blocking_risks
        or item.readiness_decision in {"needs_work", "park", "reject"}
        or item.task_signals.get("blocked_count", 0) > 0
    ][:limit]
    recommended_sequence = _radar_recommended_sequence(top_opportunities)
    profile_name = profile.name if profile else "Default Research Profile"
    markdown_export = _render_research_opportunity_radar_markdown(
        profile_name=profile_name,
        top_opportunities=top_opportunities,
        risk_watchlist=risk_watchlist,
        recommended_sequence=recommended_sequence,
    )
    return ResearchOpportunityRadarResponse(
        profile_name=profile_name,
        idea_count=len(ranked),
        opportunity_count=len(top_opportunities),
        top_opportunities=top_opportunities,
        risk_watchlist=risk_watchlist,
        recommended_sequence=recommended_sequence,
        markdown_export=markdown_export,
        message=(
            f"Built research opportunity radar for {len(top_opportunities)} "
            f"opportunities from {len(ranked)} ranked ideas."
        ),
    )


@router.post("/opportunities/radar/tasks", response_model=ResearchTaskGenerationResponse)
def create_tasks_from_research_opportunity_radar(
    payload: OpportunityRadarTaskGenerateRequest,
    session: Session = Depends(get_session),
) -> ResearchTaskGenerationResponse:
    radar = get_research_opportunity_radar(limit=payload.limit, session=session)
    tasks = ResearchTaskService(session).create_from_opportunity_radar(
        [item.model_dump() for item in radar.top_opportunities],
        actions_per_opportunity=payload.actions_per_opportunity,
        created_by=payload.created_by,
    )
    return ResearchTaskGenerationResponse(
        tasks=[_serialize_research_task(task) for task in tasks],
        message=(
            f"Created {len(tasks)} task-board tasks from "
            f"{len(radar.top_opportunities)} opportunity radar items."
        ),
    )


def _build_research_opportunity_item(
    ranked_item: Any,
    readiness: IdeaReadinessSummary,
    task_signals: dict[str, Any],
) -> ResearchOpportunityItem:
    blocker_count = readiness.blocker_count
    task_health = _radar_task_health(task_signals)
    radar_score = round(
        _clamp(
            (_clamp(ranked_item.weighted_score / 5.0) * 0.55)
            + (readiness.readiness_score * 0.35)
            + (task_health * 0.10)
            - min(blocker_count * 0.025, 0.2)
        ),
        4,
    )
    next_actions = _radar_next_actions(readiness, task_signals)
    return ResearchOpportunityItem(
        idea_id=ranked_item.idea.id,
        title=ranked_item.idea.title,
        status=ranked_item.idea.status,
        rank=ranked_item.rank,
        opportunity_type=_radar_opportunity_type(ranked_item.weighted_score, readiness),
        priority=_radar_priority(radar_score, readiness),
        radar_score=radar_score,
        weighted_score=round(ranked_item.weighted_score, 4),
        readiness_score=readiness.readiness_score,
        readiness_decision=readiness.decision,
        why_now=_radar_why_now(ranked_item, readiness),
        blocking_risks=readiness.top_blockers,
        next_actions=next_actions,
        evidence_signals=_radar_evidence_signals(ranked_item),
        task_signals=task_signals,
    )


def _radar_task_signals(session: Session, idea_id: str) -> dict[str, Any]:
    tasks = (
        session.query(ResearchTask)
        .filter(ResearchTask.idea_id == idea_id)
        .order_by(ResearchTask.created_at.desc())
        .limit(200)
        .all()
    )
    counts = Counter(task.status for task in tasks)
    open_tasks = [task for task in tasks if task.status in {"todo", "doing", "blocked"}]
    top_open_task = sorted(open_tasks, key=_progress_task_order)[:1]
    return {
        "total_task_count": len(tasks),
        "open_count": len(open_tasks),
        "doing_count": counts.get("doing", 0),
        "blocked_count": counts.get("blocked", 0),
        "done_count": counts.get("done", 0),
        "top_open_task": _task_signal_payload(top_open_task[0]) if top_open_task else {},
    }


def _task_signal_payload(task: ResearchTask) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status,
        "priority": task.priority,
        "owner_type": task.owner_type,
    }


def _radar_task_health(task_signals: dict[str, Any]) -> float:
    open_count = int(task_signals.get("open_count") or 0)
    blocked_count = int(task_signals.get("blocked_count") or 0)
    if open_count == 0:
        return 0.45
    return _clamp(1.0 - (blocked_count / open_count))


def _radar_opportunity_type(
    weighted_score: float,
    readiness: IdeaReadinessSummary,
) -> str:
    if readiness.decision == "ready_for_execution":
        return "ready_to_execute"
    if readiness.decision == "needs_targeted_work":
        return "targeted_validation"
    if readiness.decision in {"park", "reject"}:
        return "risk_watch"
    if weighted_score >= 3.0:
        return "high_potential_needs_de_risking"
    return "incubate"


def _radar_priority(radar_score: float, readiness: IdeaReadinessSummary) -> str:
    if readiness.decision == "ready_for_execution" and radar_score >= 0.7:
        return "critical"
    if radar_score >= 0.62:
        return "high"
    if radar_score >= 0.45:
        return "medium"
    return "low"


def _radar_why_now(ranked_item: Any, readiness: IdeaReadinessSummary) -> str:
    rationale = (
        ranked_item.rationale[0] if ranked_item.rationale else "Portfolio score is available."
    )
    blocker = (
        f" Top blocker: {readiness.top_blockers[0]}"
        if readiness.top_blockers
        else " No top blocker remains."
    )
    return (
        f"Rank #{ranked_item.rank} with portfolio score {ranked_item.weighted_score:.4f}; "
        f"readiness {readiness.readiness_score:.4f} ({readiness.decision}). "
        f"{rationale}{blocker}"
    )


def _radar_evidence_signals(ranked_item: Any) -> list[str]:
    idea = ranked_item.idea
    signals = [
        f"{len(idea.evidence_ids_json or [])} evidence ids",
        f"{len(idea.related_paper_ids_json or [])} related papers",
    ]
    if idea.datasets_json:
        signals.append(f"datasets: {', '.join(idea.datasets_json[:3])}")
    if idea.metrics_json:
        signals.append(f"metrics: {', '.join(idea.metrics_json[:3])}")
    if ranked_item.score_breakdown:
        top_dimensions = sorted(
            ranked_item.score_breakdown.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:3]
        signals.append(
            "score strengths: " + ", ".join(f"{name}={score:.3f}" for name, score in top_dimensions)
        )
    return signals


def _radar_next_actions(
    readiness: IdeaReadinessSummary,
    task_signals: dict[str, Any],
) -> list[str]:
    actions = []
    top_task = task_signals.get("top_open_task") or {}
    if top_task:
        actions.append(f"Work task `{top_task['id']}`: {top_task['title']}")
    for blocker in readiness.top_blockers[:2]:
        actions.append(f"Clear blocker: {blocker}")
    if readiness.decision == "ready_for_execution":
        actions.append("Create or refresh a 14-day research execution plan.")
    elif not top_task and readiness.top_blockers:
        actions.append("Generate follow-up tasks from readiness blockers.")
    elif not top_task:
        actions.append("Create an advisor brief or decision memo to lock the next commitment.")
    return actions[:4]


def _radar_recommended_sequence(items: list[ResearchOpportunityItem]) -> list[str]:
    if not items:
        return ["Ingest literature and run the literature-to-ideas workflow."]
    sequence = []
    for item in items[:5]:
        action = item.next_actions[0] if item.next_actions else "Review idea progress."
        sequence.append(f"{item.priority}: {item.title} -> {action}")
    return sequence


def _render_research_opportunity_radar_markdown(
    *,
    profile_name: str,
    top_opportunities: list[ResearchOpportunityItem],
    risk_watchlist: list[ResearchOpportunityItem],
    recommended_sequence: list[str],
) -> str:
    lines = [
        "# Research Opportunity Radar",
        "",
        f"- Profile: {profile_name}",
        f"- Opportunity Count: {len(top_opportunities)}",
        f"- Risk Watchlist Count: {len(risk_watchlist)}",
        "",
        "## Top Opportunities",
        "",
    ]
    if top_opportunities:
        for item in top_opportunities:
            lines.extend(
                [
                    f"### {item.rank}. {item.title}",
                    "",
                    f"- Idea ID: `{item.idea_id}`",
                    f"- Priority: `{item.priority}`",
                    f"- Type: `{item.opportunity_type}`",
                    f"- Radar Score: {item.radar_score:.4f}",
                    f"- Readiness: {item.readiness_score:.4f} `{item.readiness_decision}`",
                    f"- Why Now: {item.why_now}",
                    f"- Evidence Signals: {'; '.join(item.evidence_signals)}",
                    "",
                    "Next actions:",
                    *[f"- {action}" for action in item.next_actions],
                    "",
                ]
            )
    else:
        lines.append("- No ranked opportunities yet.")

    lines.extend(["", "## Risk Watchlist", ""])
    if risk_watchlist:
        for item in risk_watchlist:
            risks = "; ".join(item.blocking_risks) if item.blocking_risks else "No blocker text."
            lines.append(f"- `{item.idea_id}` {item.title}: {risks}")
    else:
        lines.append("- No high-priority risks detected.")

    lines.extend(["", "## Recommended Sequence", ""])
    lines.extend(f"- {action}" for action in recommended_sequence)
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


@router.post(
    "/ideas/{idea_id}/decision-memos/{memo_id}/tasks",
    response_model=ResearchTaskGenerationResponse,
)
def create_tasks_from_idea_decision_memo(
    idea_id: str,
    memo_id: str,
    payload: ResearchTaskGenerateRequest,
    session: Session = Depends(get_session),
) -> ResearchTaskGenerationResponse:
    memo = IdeaDecisionMemoService(session).get_memo(idea_id, memo_id)
    if memo is None:
        raise HTTPException(status_code=404, detail="Idea decision memo not found")
    tasks = ResearchTaskService(session).create_from_idea_decision_memo(
        memo.id,
        created_by=payload.created_by,
    )
    return ResearchTaskGenerationResponse(
        tasks=[_serialize_research_task(task) for task in tasks],
        message=f"Created {len(tasks)} research tasks from idea decision memo {memo.id}.",
    )


@router.post("/ideas/{idea_id}/assumption-audit", response_model=IdeaAssumptionAuditRead)
def create_idea_assumption_audit(
    idea_id: str,
    payload: IdeaAssumptionAuditCreate,
    session: Session = Depends(get_session),
) -> IdeaAssumptionAuditRead:
    try:
        audit = IdeaAssumptionAuditService(session).create_audit(
            idea_id,
            assumptions=payload.assumptions,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize_idea_assumption_audit(audit)


@router.get("/ideas/{idea_id}/assumption-audits", response_model=list[IdeaAssumptionAuditRead])
def list_idea_assumption_audits(
    idea_id: str,
    limit: int = 20,
    session: Session = Depends(get_session),
) -> list[IdeaAssumptionAuditRead]:
    try:
        audits = IdeaAssumptionAuditService(session).list_for_idea(idea_id, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_serialize_idea_assumption_audit(audit) for audit in audits]


@router.get("/ideas/{idea_id}/assumption-audits/{audit_id}", response_model=IdeaAssumptionAuditRead)
def get_idea_assumption_audit(
    idea_id: str,
    audit_id: str,
    session: Session = Depends(get_session),
) -> IdeaAssumptionAuditRead:
    audit = IdeaAssumptionAuditService(session).get_audit(idea_id, audit_id)
    if audit is None:
        raise HTTPException(status_code=404, detail="Idea assumption audit not found")
    return _serialize_idea_assumption_audit(audit)


@router.get(
    "/ideas/{idea_id}/assumption-audits/{audit_id}/export/markdown",
    response_class=PlainTextResponse,
)
def export_idea_assumption_audit_markdown(
    idea_id: str,
    audit_id: str,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    audit = IdeaAssumptionAuditService(session).get_audit(idea_id, audit_id)
    if audit is None:
        raise HTTPException(status_code=404, detail="Idea assumption audit not found")
    return PlainTextResponse(audit.markdown_export or "", media_type="text/markdown")


@router.post("/ideas/{idea_id}/evidence-ledger", response_model=IdeaEvidenceLedgerRead)
def create_idea_evidence_ledger(
    idea_id: str,
    payload: IdeaEvidenceLedgerCreate,
    session: Session = Depends(get_session),
) -> IdeaEvidenceLedgerRead:
    try:
        ledger = IdeaEvidenceLedgerService(session).create_ledger(
            idea_id,
            claims=payload.claims,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize_idea_evidence_ledger(ledger)


@router.get("/ideas/{idea_id}/evidence-ledgers", response_model=list[IdeaEvidenceLedgerRead])
def list_idea_evidence_ledgers(
    idea_id: str,
    limit: int = 20,
    session: Session = Depends(get_session),
) -> list[IdeaEvidenceLedgerRead]:
    try:
        ledgers = IdeaEvidenceLedgerService(session).list_for_idea(idea_id, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_serialize_idea_evidence_ledger(ledger) for ledger in ledgers]


@router.get(
    "/ideas/{idea_id}/evidence-ledgers/{ledger_id}",
    response_model=IdeaEvidenceLedgerRead,
)
def get_idea_evidence_ledger(
    idea_id: str,
    ledger_id: str,
    session: Session = Depends(get_session),
) -> IdeaEvidenceLedgerRead:
    ledger = IdeaEvidenceLedgerService(session).get_ledger(idea_id, ledger_id)
    if ledger is None:
        raise HTTPException(status_code=404, detail="Idea evidence ledger not found")
    return _serialize_idea_evidence_ledger(ledger)


@router.get(
    "/ideas/{idea_id}/evidence-ledgers/{ledger_id}/export/markdown",
    response_class=PlainTextResponse,
)
def export_idea_evidence_ledger_markdown(
    idea_id: str,
    ledger_id: str,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    ledger = IdeaEvidenceLedgerService(session).get_ledger(idea_id, ledger_id)
    if ledger is None:
        raise HTTPException(status_code=404, detail="Idea evidence ledger not found")
    return PlainTextResponse(ledger.markdown_export or "", media_type="text/markdown")


@router.post(
    "/ideas/{idea_id}/evidence-ledgers/{ledger_id}/tasks",
    response_model=ResearchTaskGenerationResponse,
)
def create_tasks_from_idea_evidence_ledger(
    idea_id: str,
    ledger_id: str,
    payload: ResearchTaskGenerateRequest,
    session: Session = Depends(get_session),
) -> ResearchTaskGenerationResponse:
    ledger = IdeaEvidenceLedgerService(session).get_ledger(idea_id, ledger_id)
    if ledger is None:
        raise HTTPException(status_code=404, detail="Idea evidence ledger not found")
    try:
        tasks = ResearchTaskService(session).create_from_idea_evidence_ledger(
            ledger.id,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ResearchTaskGenerationResponse(
        tasks=[_serialize_research_task(task) for task in tasks],
        message=f"Created {len(tasks)} evidence follow-up tasks from ledger {ledger.id}.",
    )


@router.get(
    "/ideas/{idea_id}/evidence-ledgers/{ledger_id}/claims/{claim_id}/validation-packet",
    response_model=IdeaClaimValidationPacketResponse,
)
def get_idea_claim_validation_packet(
    idea_id: str,
    ledger_id: str,
    claim_id: str,
    session: Session = Depends(get_session),
) -> IdeaClaimValidationPacketResponse:
    idea = IdeaService(session).get_idea(idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")
    ledger = IdeaEvidenceLedgerService(session).get_ledger(idea_id, ledger_id)
    if ledger is None:
        raise HTTPException(status_code=404, detail="Idea evidence ledger not found")
    claim = _find_ledger_claim(ledger, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="Evidence ledger claim not found")

    support_ids = [str(evidence_id) for evidence_id in claim.get("supporting_evidence_ids") or []]
    evidence_records = _load_evidences_by_id(session, support_ids)
    evidence_links = [
        link
        for link in ledger.evidence_links_json or []
        if claim.get("claim_id") in (link.get("linked_claim_ids") or [])
        or str(link.get("evidence_id") or "") in support_ids
    ]
    counterevidence = _claim_packet_counterevidence(ledger, claim)
    missing_evidence = _claim_packet_missing_evidence(ledger, claim)
    related_tasks = _claim_packet_related_tasks(session, ledger, claim)
    graph_edge_summary = _graph_edge_summary(
        session,
        [
            idea.id,
            ledger.id,
            f"{ledger.id}:{claim.get('claim_id', claim_id)}",
            *support_ids,
            *[task.id for task in related_tasks],
        ],
    )
    validation_actions = _claim_validation_actions(
        claim=claim,
        supporting_evidence=evidence_records,
        counterevidence=counterevidence,
        missing_evidence=missing_evidence,
        related_tasks=related_tasks,
    )
    markdown_export = _render_claim_validation_packet_markdown(
        idea=idea,
        ledger=ledger,
        claim=claim,
        supporting_evidence=evidence_records,
        evidence_links=evidence_links,
        counterevidence=counterevidence,
        missing_evidence=missing_evidence,
        related_tasks=related_tasks,
        validation_actions=validation_actions,
        graph_edge_summary=graph_edge_summary,
    )
    return IdeaClaimValidationPacketResponse(
        idea=_serialize_idea(idea),
        ledger=_serialize_idea_evidence_ledger(ledger),
        claim=claim,
        supporting_evidence=[_serialize_evidence(evidence) for evidence in evidence_records],
        evidence_links=evidence_links,
        counterevidence=counterevidence,
        missing_evidence=missing_evidence,
        related_tasks=[_serialize_research_task(task) for task in related_tasks],
        validation_actions=validation_actions,
        graph_edge_summary=graph_edge_summary,
        markdown_export=markdown_export,
        message=(
            f"Loaded validation packet for claim {claim.get('claim_id', claim_id)} "
            f"from ledger {ledger.id}."
        ),
    )


@router.get("/claims/validation-queue", response_model=ClaimValidationQueueResponse)
def get_claim_validation_queue(
    idea_id: str | None = None,
    limit: int = 20,
    session: Session = Depends(get_session),
) -> ClaimValidationQueueResponse:
    limit = max(1, min(limit, 100))
    ledgers = _latest_evidence_ledgers_for_queue(session, idea_id=idea_id, limit=limit)
    idea_ids = [ledger.idea_id for ledger in ledgers]
    ideas = session.query(Idea).filter(Idea.id.in_(idea_ids)).all() if idea_ids else []
    ideas_by_id = {idea.id: idea for idea in ideas}

    items: list[ClaimValidationQueueItem] = []
    for ledger in ledgers:
        idea = ideas_by_id.get(ledger.idea_id)
        if idea is None:
            continue
        for claim in ledger.claims_json or []:
            item = _claim_validation_queue_item(session, idea=idea, ledger=ledger, claim=claim)
            items.append(item)
    items = sorted(
        items,
        key=lambda item: (
            -item.urgency_score,
            item.priority,
            item.ledger_created_at,
            item.idea.id,
            item.claim_id,
        ),
    )[:limit]
    summary = _claim_validation_queue_summary(items)
    markdown_export = _render_claim_validation_queue_markdown(items=items, summary=summary)
    return ClaimValidationQueueResponse(
        items=items,
        summary=summary,
        markdown_export=markdown_export,
        message=f"Loaded {len(items)} claim validation queue items.",
    )


def _latest_evidence_ledgers_for_queue(
    session: Session,
    *,
    idea_id: str | None,
    limit: int,
) -> list[IdeaEvidenceLedger]:
    scan_limit = max(limit * 10, 100)
    query = session.query(IdeaEvidenceLedger).order_by(IdeaEvidenceLedger.created_at.desc())
    if idea_id:
        query = query.filter(IdeaEvidenceLedger.idea_id == idea_id)
    ledgers = query.limit(scan_limit).all()
    latest_by_idea: dict[str, IdeaEvidenceLedger] = {}
    for ledger in ledgers:
        if ledger.idea_id not in latest_by_idea:
            latest_by_idea[ledger.idea_id] = ledger
    return list(latest_by_idea.values())


def _claim_validation_queue_item(
    session: Session,
    *,
    idea: Idea,
    ledger: IdeaEvidenceLedger,
    claim: dict,
) -> ClaimValidationQueueItem:
    claim_id = str(claim.get("claim_id") or "")
    support_ids = [str(evidence_id) for evidence_id in claim.get("supporting_evidence_ids") or []]
    missing = _claim_packet_missing_evidence(ledger, claim)
    related_tasks = _claim_packet_related_tasks(session, ledger, claim)
    counter_count = len(claim.get("challenge_signals") or [])
    if claim.get("support_level") in {"unsupported", "partially_supported", "challenged"}:
        counter_count += len(ledger.counterevidence_json or [])
    urgency_score = _claim_validation_urgency_score(
        support_level=str(claim.get("support_level") or ""),
        supporting_evidence_count=len(support_ids),
        missing_evidence_count=len(missing),
        counterevidence_count=counter_count,
        related_task_count=len([task for task in related_tasks if task.status != "done"]),
    )
    priority = _claim_validation_priority(urgency_score)
    next_validation = str(claim.get("next_validation") or "")
    recommended_action = _claim_queue_recommended_action(
        claim=claim,
        missing_evidence_count=len(missing),
        related_tasks=related_tasks,
    )
    return ClaimValidationQueueItem(
        idea=_serialize_idea(idea),
        ledger_id=ledger.id,
        ledger_created_at=ledger.created_at,
        claim_id=claim_id,
        claim=str(claim.get("claim") or ""),
        claim_type=str(claim.get("claim_type") or ""),
        support_level=str(claim.get("support_level") or ""),
        priority=priority,
        urgency_score=urgency_score,
        supporting_evidence_count=len(support_ids),
        missing_evidence_count=len(missing),
        counterevidence_count=counter_count,
        related_task_count=len(related_tasks),
        next_validation=next_validation,
        recommended_action=recommended_action,
    )


def _claim_validation_urgency_score(
    *,
    support_level: str,
    supporting_evidence_count: int,
    missing_evidence_count: int,
    counterevidence_count: int,
    related_task_count: int,
) -> float:
    base = {
        "challenged": 0.95,
        "unsupported": 0.9,
        "partially_supported": 0.7,
        "supported": 0.35,
    }.get(support_level, 0.55)
    score = (
        base
        + min(missing_evidence_count, 4) * 0.08
        + min(counterevidence_count, 4) * 0.06
        + min(related_task_count, 4) * 0.03
        - min(supporting_evidence_count, 4) * 0.04
    )
    return round(max(0.0, min(1.0, score)), 4)


def _claim_validation_priority(urgency_score: float) -> str:
    if urgency_score >= 0.85:
        return "critical"
    if urgency_score >= 0.65:
        return "high"
    if urgency_score >= 0.4:
        return "medium"
    return "low"


def _claim_queue_recommended_action(
    *,
    claim: dict,
    missing_evidence_count: int,
    related_tasks: list[ResearchTask],
) -> str:
    open_tasks = [task for task in related_tasks if task.status in {"todo", "doing", "blocked"}]
    if open_tasks:
        task = sorted(open_tasks, key=_progress_task_order)[0]
        return f"Work linked task `{task.id}`: {task.title}"
    if missing_evidence_count:
        return f"Collect missing evidence for claim {claim.get('claim_id', '')}."
    next_validation = str(claim.get("next_validation") or "").strip()
    if next_validation:
        return next_validation
    return "Review this claim with the latest evidence ledger before advancing the idea."


def _claim_validation_queue_summary(items: list[ClaimValidationQueueItem]) -> dict[str, Any]:
    priorities = Counter(item.priority for item in items)
    support_levels = Counter(item.support_level for item in items)
    idea_count = len({item.idea.id for item in items})
    return {
        "item_count": len(items),
        "idea_count": idea_count,
        "by_priority": dict(priorities),
        "by_support_level": dict(support_levels),
        "critical_count": priorities.get("critical", 0),
        "high_count": priorities.get("high", 0),
    }


def _render_claim_validation_queue_markdown(
    *,
    items: list[ClaimValidationQueueItem],
    summary: dict[str, Any],
) -> str:
    lines = [
        "# Claim Validation Queue",
        "",
        f"- Item Count: {summary.get('item_count', 0)}",
        f"- Idea Count: {summary.get('idea_count', 0)}",
        f"- By Priority: {summary.get('by_priority', {})}",
        f"- By Support Level: {summary.get('by_support_level', {})}",
        "",
        "## Queue",
        "",
    ]
    if not items:
        lines.append("- No evidence-ledger claims found.")
    for item in items:
        lines.append(
            f"- `{item.priority}` score={item.urgency_score} idea=`{item.idea.id}` "
            f"ledger=`{item.ledger_id}` claim=`{item.claim_id}` "
            f"support=`{item.support_level}`: {item.claim}"
        )
        lines.append(f"  - action: {item.recommended_action}")
        lines.append(
            "  - counts: "
            f"support={item.supporting_evidence_count}, "
            f"missing={item.missing_evidence_count}, "
            f"counter={item.counterevidence_count}, "
            f"tasks={item.related_task_count}"
        )
    return "\n".join(lines).strip() + "\n"


def _find_ledger_claim(ledger: IdeaEvidenceLedger, claim_id: str) -> dict | None:
    normalized = str(claim_id).strip().lower()
    for claim in ledger.claims_json or []:
        if str(claim.get("claim_id") or "").strip().lower() == normalized:
            return claim
    return None


def _load_evidences_by_id(session: Session, evidence_ids: list[str]) -> list[Evidence]:
    if not evidence_ids:
        return []
    records = session.query(Evidence).filter(Evidence.id.in_(evidence_ids)).limit(100).all()
    by_id = {record.id: record for record in records}
    return [by_id[evidence_id] for evidence_id in evidence_ids if evidence_id in by_id]


def _claim_packet_counterevidence(
    ledger: IdeaEvidenceLedger,
    claim: dict,
) -> list[dict[str, Any]]:
    items = [
        {
            "source_type": "claim_challenge",
            "source_id": claim.get("claim_id", ""),
            "signal": signal,
            "severity": "medium",
        }
        for signal in claim.get("challenge_signals") or []
    ]
    items.extend((ledger.counterevidence_json or [])[:8])
    return _dedupe_packet_items(items, key="signal")[:12]


def _claim_packet_missing_evidence(
    ledger: IdeaEvidenceLedger,
    claim: dict,
) -> list[dict[str, Any]]:
    claim_id = str(claim.get("claim_id") or "")
    direct = [
        item
        for item in ledger.missing_evidence_json or []
        if str(item.get("source_id") or "") == claim_id
    ]
    if direct:
        return direct[:12]
    if not claim.get("supporting_evidence_ids"):
        return [
            {
                "gap": f"No direct evidence is linked to claim {claim_id}.",
                "source_type": "claim_coverage",
                "source_id": claim_id,
                "priority": "high",
            }
        ]
    return []


def _claim_packet_related_tasks(
    session: Session,
    ledger: IdeaEvidenceLedger,
    claim: dict,
) -> list[ResearchTask]:
    claim_id = str(claim.get("claim_id") or "")
    tasks = (
        session.query(ResearchTask)
        .filter(
            ResearchTask.owner_type == "idea_evidence_ledger",
            ResearchTask.owner_id == ledger.id,
        )
        .order_by(ResearchTask.created_at.desc())
        .limit(100)
        .all()
    )
    related = []
    for task in tasks:
        metadata = task.metadata_json or {}
        ledger_item = metadata.get("ledger_item") or {}
        if (
            task.source_id == claim_id
            or str(metadata.get("claim_id") or "") == claim_id
            or str(ledger_item.get("source_id") or "") == claim_id
        ):
            related.append(task)
    return related[:20]


def _claim_validation_actions(
    *,
    claim: dict,
    supporting_evidence: list[Evidence],
    counterevidence: list[dict],
    missing_evidence: list[dict],
    related_tasks: list[ResearchTask],
) -> list[str]:
    actions = []
    next_validation = str(claim.get("next_validation") or "").strip()
    if next_validation:
        actions.append(next_validation)
    if not supporting_evidence:
        actions.append("Collect at least one direct evidence record for this claim.")
    actions.extend(str(item.get("gap") or "") for item in missing_evidence[:4])
    actions.extend(f"Resolve challenge: {item.get('signal', '')}" for item in counterevidence[:4])
    actions.extend(
        f"Work task `{task.id}` ({task.priority}/{task.status}): {task.title}"
        for task in related_tasks[:4]
        if task.status in {"todo", "doing", "blocked"}
    )
    return _dedupe_strings(actions)[:10]


def _render_claim_validation_packet_markdown(
    *,
    idea: Idea,
    ledger: IdeaEvidenceLedger,
    claim: dict,
    supporting_evidence: list[Evidence],
    evidence_links: list[dict],
    counterevidence: list[dict],
    missing_evidence: list[dict],
    related_tasks: list[ResearchTask],
    validation_actions: list[str],
    graph_edge_summary: dict[str, int],
) -> str:
    lines = [
        f"# Claim Validation Packet: {claim.get('claim_id', '')}",
        "",
        f"- Idea ID: `{idea.id}`",
        f"- Ledger ID: `{ledger.id}`",
        f"- Claim ID: `{claim.get('claim_id', '')}`",
        f"- Support Level: `{claim.get('support_level', '')}`",
        f"- Claim Type: `{claim.get('claim_type', '')}`",
        f"- Coverage Score: {ledger.coverage_score}",
        "",
        "## Claim",
        "",
        str(claim.get("claim") or ""),
        "",
        "## Supporting Evidence",
        "",
    ]
    if supporting_evidence:
        for evidence in supporting_evidence:
            lines.append(
                f"- `{evidence.id}` `{evidence.evidence_type}` confidence={evidence.confidence}: "
                f"{evidence.summary or evidence.supports or evidence.text}"
            )
    else:
        lines.append("- No supporting evidence is linked to this claim.")

    lines.extend(["", "## Evidence Links", ""])
    if evidence_links:
        for link in evidence_links:
            lines.append(
                f"- `{link.get('evidence_id', '')}` `{link.get('support_role', '')}`: "
                f"{link.get('summary', '')}"
            )
    else:
        lines.append("- No evidence-link records matched this claim.")

    lines.extend(["", "## Counterevidence", ""])
    if counterevidence:
        lines.extend(f"- {item.get('signal', item)}" for item in counterevidence)
    else:
        lines.append("- No counterevidence is linked to this claim.")

    lines.extend(["", "## Missing Evidence", ""])
    if missing_evidence:
        lines.extend(f"- {item.get('gap', item)}" for item in missing_evidence)
    else:
        lines.append("- No claim-specific missing evidence is recorded.")

    lines.extend(["", "## Related Tasks", ""])
    if related_tasks:
        for task in related_tasks:
            lines.append(
                f"- `{task.id}` `{task.priority}` `{task.status}` `{task.due_phase}` {task.title}"
            )
    else:
        lines.append("- No claim-specific follow-up tasks are linked yet.")

    lines.extend(["", "## Validation Actions", ""])
    if validation_actions:
        lines.extend(f"- {action}" for action in validation_actions)
    else:
        lines.append("- No validation actions generated.")

    lines.extend(["", "## Graph Edge Summary", ""])
    if graph_edge_summary:
        lines.extend(f"- `{edge}`: {count}" for edge, count in graph_edge_summary.items())
    else:
        lines.append("- No graph edges found for this claim packet.")
    return "\n".join(lines).strip() + "\n"


def _dedupe_packet_items(items: list[dict], *, key: str) -> list[dict]:
    unique = []
    seen = set()
    for item in items:
        value = " ".join(str(item.get(key) or item).split())
        lowered = value.lower()
        if value and lowered not in seen:
            unique.append(item)
            seen.add(lowered)
    return unique


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
        "idea_has_novelty_check",
        "novelty_check_creates_task",
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
        "decision_memo_creates_task",
        "idea_has_assumption_audit",
        "idea_has_evidence_ledger",
        "evidence_ledger_tracks_claim",
        "evidence_supports_claim",
        "evidence_ledger_creates_task",
        "research_plan_creates_task",
        "idea_has_readiness_assessment",
        "idea_readiness_creates_task",
        "idea_has_quality_gate",
        "quality_gate_creates_task",
        "project_triage_creates_task",
        "idea_has_opportunity_radar",
        "opportunity_radar_creates_task",
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
    assumption_audits: list[IdeaAssumptionAudit],
    evidence_ledgers: list[IdeaEvidenceLedger],
    research_plans: list[ResearchPlanSnapshot],
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
        f"- Assumption Audits: {len(assumption_audits)}",
        f"- Evidence Ledgers: {len(evidence_ledgers)}",
        f"- Research Plans: {len(research_plans)}",
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

    lines.extend(["", "## Assumption Audits", ""])
    if assumption_audits:
        for audit in assumption_audits[:5]:
            lines.append(
                f"- `{audit.id}` `{audit.status}` assumptions={len(audit.assumptions_json or [])}"
            )
    else:
        lines.append("- No assumption audits recorded yet.")

    lines.extend(["", "## Evidence Ledgers", ""])
    if evidence_ledgers:
        for ledger in evidence_ledgers[:5]:
            summary = ledger.summary_json or {}
            lines.append(
                f"- `{ledger.id}` coverage={ledger.coverage_score} "
                f"claims={summary.get('claim_count', 0)} "
                f"missing={summary.get('missing_evidence_count', 0)}"
            )
    else:
        lines.append("- No evidence ledger recorded yet.")

    lines.extend(["", "## Research Plans", ""])
    if research_plans:
        for plan in research_plans[:5]:
            lines.append(
                f"- `{plan.id}` {plan.title} horizon={plan.horizon_days}d "
                f"items={len(plan.plan_items_json or [])}"
            )
    else:
        lines.append("- No research execution plans include this idea.")

    lines.extend(["", "## Next Tasks", ""])
    next_tasks = [task for task in tasks if task.status in {"todo", "doing", "blocked"}][:20]
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


@router.post("/ideas/{idea_id}/novelty-refresh", response_model=NoveltyCheckRead)
def refresh_idea_novelty_search(
    idea_id: str,
    payload: NoveltyRefreshRequest,
    session: Session = Depends(get_session),
) -> NoveltyCheckRead:
    try:
        check = NoveltyService(session).create_check(
            idea_id,
            include_external_literature=payload.include_external,
            limit=payload.limit,
            query_override=payload.query_override,
            mode="external_refresh",
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize_novelty_check(check)


@router.post(
    "/ideas/{idea_id}/novelty-checks/{check_id}/tasks",
    response_model=ResearchTaskGenerationResponse,
)
def create_tasks_from_idea_novelty_check(
    idea_id: str,
    check_id: str,
    payload: ResearchTaskGenerateRequest,
    session: Session = Depends(get_session),
) -> ResearchTaskGenerationResponse:
    check = session.get(NoveltyCheck, check_id)
    if check is None or check.idea_id != idea_id:
        raise HTTPException(status_code=404, detail="Novelty check not found")
    try:
        tasks = ResearchTaskService(session).create_from_novelty_check(
            check_id,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ResearchTaskGenerationResponse(
        tasks=[_serialize_research_task(task) for task in tasks],
        message=f"Created {len(tasks)} novelty follow-up tasks from novelty check {check_id}.",
    )


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


@router.get("/ideas/{idea_id}/export/bundle")
def export_idea_bundle(
    idea_id: str,
    session: Session = Depends(get_session),
) -> Response:
    try:
        content = _build_idea_bundle_zip(session, idea_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(
        content=content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="idea-{idea_id}-research-bundle.zip"'
        },
    )


@router.get("/export/project-bundle")
def export_project_bundle(
    session: Session = Depends(get_session),
) -> Response:
    content = _build_project_bundle_zip(session)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="research-project-bundle.zip"'},
    )


def _build_idea_bundle_zip(session: Session, idea_id: str) -> bytes:
    idea = IdeaService(session).get_idea(idea_id)
    if idea is None:
        raise ValueError("Idea not found")

    idea_markdown = ExportService(session).render_idea_markdown(idea_id)
    lineage = get_idea_lineage(idea_id, session=session)
    progress = get_idea_progress(idea_id, session=session)
    research_packet = get_idea_research_packet(idea_id, session=session)
    timeline = get_idea_timeline(idea_id, session=session)
    readiness = get_idea_readiness(idea_id, session=session)
    manifest = _idea_bundle_manifest(
        idea_id=idea_id,
        title=idea.title,
        lineage=lineage,
        readiness=readiness,
        progress=progress,
        research_packet=research_packet,
        timeline=timeline,
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.md", _render_idea_bundle_readme(manifest))
        archive.writestr("metadata/manifest.json", _json_dump(manifest))
        archive.writestr("metadata/lineage.json", _json_dump(lineage))
        archive.writestr("metadata/progress.json", _json_dump(progress))
        archive.writestr("metadata/research-packet.json", _json_dump(research_packet))
        archive.writestr("metadata/timeline.json", _json_dump(timeline))
        archive.writestr("metadata/readiness.json", _json_dump(readiness))
        _write_markdown(archive, "01-idea-dossier.md", idea_markdown)
        _write_markdown(archive, "02-lineage.md", lineage.markdown_export)
        _write_markdown(archive, "03-progress.md", progress.markdown_export)
        _write_markdown(archive, "04-research-packet.md", research_packet.markdown_export)
        _write_markdown(archive, "05-readiness.md", readiness.markdown_export)
        _write_markdown(archive, "06-timeline.md", timeline.markdown_export)
        _write_artifact_markdowns(
            archive,
            "artifacts/related-work",
            "related-work-matrix",
            lineage.related_work_matrices,
        )
        _write_artifact_markdowns(
            archive,
            "artifacts/proposals/drafts",
            "proposal-draft",
            lineage.proposal_drafts,
        )
        _write_artifact_markdowns(
            archive,
            "artifacts/proposals/reviews",
            "proposal-review",
            lineage.proposal_reviews,
        )
        _write_artifact_markdowns(
            archive,
            "artifacts/proposals/revisions",
            "proposal-revision",
            lineage.proposal_revisions,
        )
        _write_artifact_markdowns(
            archive,
            "artifacts/experiments/runs",
            "experiment-run",
            lineage.experiment_runs,
        )
        _write_artifact_markdowns(
            archive,
            "artifacts/experiments/analyses",
            "experiment-analysis",
            lineage.experiment_analyses,
        )
        _write_artifact_markdowns(
            archive,
            "artifacts/decisions",
            "decision-memo",
            lineage.decision_memos,
        )
        _write_artifact_markdowns(
            archive,
            "artifacts/assumptions",
            "assumption-audit",
            lineage.assumption_audits,
        )
        _write_artifact_markdowns(
            archive,
            "artifacts/evidence-ledgers",
            "evidence-ledger",
            lineage.evidence_ledgers,
        )
        for snapshot in lineage.task_board_snapshots:
            persisted = session.get(TaskBoardSnapshot, snapshot.id)
            if persisted and persisted.markdown_export:
                _write_markdown(
                    archive,
                    f"artifacts/tasks/task-board-snapshot-{snapshot.id}.md",
                    persisted.markdown_export,
                )
        for plan in lineage.research_plans:
            persisted = session.get(ResearchPlanSnapshot, plan.id)
            if persisted and persisted.markdown_export:
                _write_markdown(
                    archive,
                    f"artifacts/plans/research-plan-{plan.id}.md",
                    persisted.markdown_export,
                )
    return buffer.getvalue()


def _build_project_bundle_zip(session: Session) -> bytes:
    overview = get_research_progress_overview(session=session)
    readiness_overview = get_project_readiness_overview(session=session)
    quality_overview = get_project_quality_gate_overview(session=session)
    opportunity_radar = get_research_opportunity_radar(session=session)
    triage_brief = get_project_triage_brief(session=session)
    triage_snapshot_service = ProjectTriageSnapshotService(session)
    triage_snapshots = triage_snapshot_service.list_snapshots(limit=12)
    triage_snapshot_comparison = (
        triage_snapshot_service.compare_snapshots(triage_snapshots[1].id, triage_snapshots[0].id)
        if len(triage_snapshots) >= 2
        else None
    )
    briefs = ResearchBriefService(session).list_briefs(limit=12)
    plans = ResearchPlanService(session).list_plans(limit=12)
    tasks = ResearchTaskService(session).list_tasks(limit=200)
    plan_progress_items = [get_research_plan_progress(plan.id, session=session) for plan in plans]
    manifest = _project_bundle_manifest(
        overview=overview,
        readiness_overview=readiness_overview,
        quality_overview=quality_overview,
        opportunity_radar=opportunity_radar,
        triage_brief=triage_brief,
        triage_snapshots=triage_snapshots,
        triage_snapshot_comparison=triage_snapshot_comparison,
        briefs=briefs,
        plans=plans,
        tasks=tasks,
        plan_progress_items=plan_progress_items,
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.md", _render_project_bundle_readme(manifest))
        archive.writestr("metadata/manifest.json", _json_dump(manifest))
        archive.writestr("metadata/progress-overview.json", _json_dump(overview))
        archive.writestr("metadata/readiness-overview.json", _json_dump(readiness_overview))
        archive.writestr("metadata/quality-gate-overview.json", _json_dump(quality_overview))
        archive.writestr("metadata/opportunity-radar.json", _json_dump(opportunity_radar))
        archive.writestr("metadata/triage-brief.json", _json_dump(triage_brief))
        archive.writestr(
            "metadata/triage-snapshots.json",
            _json_dump(
                [_serialize_project_triage_snapshot(snapshot) for snapshot in triage_snapshots]
            ),
        )
        if triage_snapshot_comparison:
            archive.writestr(
                "metadata/triage-snapshot-comparison.json",
                _json_dump(triage_snapshot_comparison),
            )
        _write_markdown(archive, "00-project-triage-brief.md", triage_brief.markdown_export)
        _write_markdown(archive, "01-progress-overview.md", overview.markdown_export)
        _write_markdown(archive, "02-readiness-overview.md", readiness_overview.markdown_export)
        _write_markdown(archive, "03-task-board.md", _render_project_task_board_markdown(tasks))
        _write_markdown(archive, "04-opportunity-radar.md", opportunity_radar.markdown_export)
        _write_markdown(archive, "05-quality-gate-overview.md", quality_overview.markdown_export)
        for snapshot in triage_snapshots:
            if snapshot.markdown_export:
                _write_markdown(
                    archive,
                    f"artifacts/triage/project-triage-snapshot-{snapshot.id}.md",
                    snapshot.markdown_export,
                )
        if triage_snapshot_comparison:
            _write_markdown(
                archive,
                "artifacts/triage/latest-triage-snapshot-comparison.md",
                triage_snapshot_comparison["markdown_export"],
            )
        for brief in briefs:
            if brief.markdown_export:
                _write_markdown(
                    archive,
                    f"artifacts/briefs/research-brief-{brief.id}.md",
                    brief.markdown_export,
                )
        for plan in plans:
            if plan.markdown_export:
                _write_markdown(
                    archive,
                    f"artifacts/plans/research-plan-{plan.id}.md",
                    plan.markdown_export,
                )
        for plan_progress in plan_progress_items:
            _write_markdown(
                archive,
                f"artifacts/plans/research-plan-progress-{plan_progress.plan.id}.md",
                plan_progress.markdown_export,
            )
    return buffer.getvalue()


def _project_bundle_manifest(
    *,
    overview: ResearchOverviewResponse,
    readiness_overview: ProjectReadinessOverviewResponse,
    quality_overview: ProjectQualityGateOverviewResponse,
    opportunity_radar: ResearchOpportunityRadarResponse,
    triage_brief: ProjectTriageBriefResponse,
    triage_snapshots: list[ProjectTriageSnapshot],
    triage_snapshot_comparison: dict | None,
    briefs: list[ResearchBrief],
    plans: list[ResearchPlanSnapshot],
    tasks: list[ResearchTask],
    plan_progress_items: list[ResearchPlanProgressResponse],
) -> dict[str, Any]:
    return {
        "bundle_type": "research_project_bundle",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "idea_count": overview.idea_count,
        "open_task_count": overview.task_summary.get("open_task_count", 0),
        "blocked_task_count": len(overview.blocked_tasks),
        "average_readiness": readiness_overview.average_readiness,
        "quality_gate_idea_count": quality_overview.idea_count,
        "average_quality_gate_score": quality_overview.average_gate_score,
        "quality_gate_decision_counts": quality_overview.decision_counts,
        "triage_next_action_count": len(triage_brief.next_actions),
        "triage_risk_focus_count": len(triage_brief.risk_focus),
        "triage_snapshot_count": len(triage_snapshots),
        "latest_triage_snapshot_id": triage_snapshots[0].id if triage_snapshots else "",
        "triage_snapshot_comparison_available": triage_snapshot_comparison is not None,
        "latest_triage_snapshot_comparison_baseline_id": (
            triage_snapshot_comparison["baseline_snapshot_id"] if triage_snapshot_comparison else ""
        ),
        "latest_triage_snapshot_comparison_candidate_id": (
            triage_snapshot_comparison["candidate_snapshot_id"]
            if triage_snapshot_comparison
            else ""
        ),
        "latest_triage_snapshot_comparison_added_focus_count": (
            len(triage_snapshot_comparison["added_focus"]) if triage_snapshot_comparison else 0
        ),
        "latest_triage_snapshot_comparison_added_risk_count": (
            len(triage_snapshot_comparison["added_risks"]) if triage_snapshot_comparison else 0
        ),
        "latest_triage_snapshot_comparison_added_next_action_count": (
            len(triage_snapshot_comparison["added_next_actions"])
            if triage_snapshot_comparison
            else 0
        ),
        "opportunity_count": opportunity_radar.opportunity_count,
        "top_opportunity_score": (
            opportunity_radar.top_opportunities[0].radar_score
            if opportunity_radar.top_opportunities
            else 0.0
        ),
        "brief_count": len(briefs),
        "research_plan_count": len(plans),
        "recent_task_count": len(tasks),
        "plan_progress": [
            {
                "plan_id": item.plan.id,
                "title": item.plan.title,
                "task_count": item.task_summary.get("task_count", 0),
                "open_task_count": item.task_summary.get("open_task_count", 0),
                "completion_ratio": item.task_summary.get("completion_ratio", 0.0),
            }
            for item in plan_progress_items
        ],
    }


def _render_project_bundle_readme(manifest: dict[str, Any]) -> str:
    lines = [
        "# Research Project Bundle",
        "",
        f"- Generated At: `{manifest['generated_at']}`",
        f"- Idea Count: {manifest['idea_count']}",
        f"- Open Tasks: {manifest['open_task_count']}",
        f"- Blocked Tasks: {manifest['blocked_task_count']}",
        f"- Average Readiness: {manifest['average_readiness']}",
        f"- Opportunities: {manifest['opportunity_count']}",
        f"- Research Plans: {manifest['research_plan_count']}",
        f"- Briefs: {manifest['brief_count']}",
        "",
        "## Start Here",
        "",
        "- `00-project-triage-brief.md`: daily decision view across progress, readiness, quality gates, and opportunity radar.",
        "- `01-progress-overview.md`: project-level task and experiment overview.",
        "- `02-readiness-overview.md`: project-level readiness comparison.",
        "- `03-task-board.md`: recent task board state.",
        "- `04-opportunity-radar.md`: ranked next opportunities and risk watchlist.",
        "- `05-quality-gate-overview.md`: go/no-go quality gate comparison across ideas.",
    ]
    if manifest.get("triage_snapshot_comparison_available"):
        lines.append(
            "- `artifacts/triage/latest-triage-snapshot-comparison.md`: latest saved triage change report."
        )
    lines.extend(
        [
            "- `artifacts/triage/`: persisted project triage decision snapshots.",
            "- `artifacts/briefs/`: persisted advisor or group-meeting briefs.",
            "- `artifacts/plans/`: execution plans and plan progress reports.",
            "- `metadata/`: JSON payloads for downstream tools or backup.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_project_task_board_markdown(tasks: list[ResearchTask]) -> str:
    lines = [
        "# Project Task Board",
        "",
        f"- Recent Task Count: {len(tasks)}",
        "",
        "## Tasks",
        "",
    ]
    if not tasks:
        lines.append("- No recent tasks.")
    for task in sorted(tasks, key=_progress_task_order)[:200]:
        lines.append(
            f"- `{task.id}` `{task.priority}` `{task.status}` "
            f"idea=`{task.idea_id or 'none'}` owner=`{task.owner_type}` {task.title}"
        )
    return "\n".join(lines).strip() + "\n"


def _idea_bundle_manifest(
    *,
    idea_id: str,
    title: str,
    lineage: IdeaLineageResponse,
    readiness: IdeaReadinessResponse,
    progress: IdeaProgressResponse,
    research_packet: IdeaResearchPacketResponse,
    timeline: IdeaTimelineResponse,
) -> dict[str, Any]:
    return {
        "bundle_type": "idea_research_bundle",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "idea_id": idea_id,
        "title": title,
        "readiness": {
            "score": readiness.readiness_score,
            "decision": readiness.decision,
            "blocker_count": len(readiness.blockers),
        },
        "recommended_next_step": progress.recommended_next_step,
        "open_task_count": len(research_packet.open_tasks),
        "timeline_event_count": len(timeline.events),
        "artifact_counts": {
            "related_work_matrices": len(lineage.related_work_matrices),
            "proposal_drafts": len(lineage.proposal_drafts),
            "proposal_reviews": len(lineage.proposal_reviews),
            "proposal_revisions": len(lineage.proposal_revisions),
            "experiment_runs": len(lineage.experiment_runs),
            "experiment_analyses": len(lineage.experiment_analyses),
            "decision_memos": len(lineage.decision_memos),
            "assumption_audits": len(lineage.assumption_audits),
            "evidence_ledgers": len(lineage.evidence_ledgers),
            "research_plans": len(lineage.research_plans),
            "research_tasks": len(lineage.research_tasks),
            "task_board_snapshots": len(lineage.task_board_snapshots),
        },
        "graph_edge_summary": lineage.graph_edge_summary,
    }


def _render_idea_bundle_readme(manifest: dict[str, Any]) -> str:
    lines = [
        f"# Research Bundle: {manifest['title']}",
        "",
        f"- Idea ID: `{manifest['idea_id']}`",
        f"- Generated At: `{manifest['generated_at']}`",
        f"- Readiness: `{manifest['readiness']['decision']}` ({manifest['readiness']['score']})",
        f"- Open Tasks In Packet: {manifest['open_task_count']}",
        "",
        "## Start Here",
        "",
        "- `01-idea-dossier.md`: full idea dossier with evidence, novelty, review, and experiment plan.",
        "- `02-lineage.md`: artifact lineage and graph edge summary.",
        "- `03-progress.md`: open work, blockers, and recommended next step.",
        "- `04-research-packet.md`: concise advisor/MCP context packet.",
        "- `05-readiness.md`: readiness score, blockers, and decision.",
        "- `06-timeline.md`: chronological activity log for handoff and retrospection.",
        "",
        "## Artifact Folders",
        "",
        "- `artifacts/`: Markdown exports for proposal, experiment, decision, audit, and task artifacts.",
        "- `artifacts/evidence-ledgers/`: claim-level evidence ledgers for this idea.",
        "- `artifacts/plans/`: execution plans that include this idea.",
        "- `metadata/`: JSON payloads for rebuilding or passing the bundle into external tools.",
        "",
        "## Recommended Next Step",
        "",
        manifest.get("recommended_next_step") or "No recommended next step recorded.",
        "",
    ]
    return "\n".join(lines)


def _write_artifact_markdowns(
    archive: zipfile.ZipFile,
    folder: str,
    prefix: str,
    artifacts: list[Any],
) -> None:
    for artifact in artifacts:
        markdown = getattr(artifact, "markdown_export", "")
        if markdown:
            _write_markdown(archive, f"{folder}/{prefix}-{artifact.id}.md", markdown)


def _write_markdown(archive: zipfile.ZipFile, path: str, content: str) -> None:
    archive.writestr(path, (content or "").strip() + "\n")


def _json_dump(payload: Any) -> str:
    return json.dumps(jsonable_encoder(payload), ensure_ascii=False, indent=2, sort_keys=True)


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
