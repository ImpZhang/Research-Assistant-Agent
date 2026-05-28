from typing import Any

from sqlalchemy.orm import Session

from backend.research.models import ExperimentPlan, Idea, ProposalDraft, RelatedWorkMatrix
from backend.research.services.artifact_graph_service import ArtifactGraphService
from backend.research.services.graph_service import GraphService


class ProposalDraftService:
    def __init__(self, session: Session):
        self.session = session

    def create_draft(
        self,
        idea_id: str,
        *,
        related_work_matrix_id: str | None = None,
        experiment_plan_id: str | None = None,
        include_latest_related_work: bool = True,
        include_latest_experiment_plan: bool = True,
        created_by: str = "system",
    ) -> ProposalDraft:
        idea = self.session.get(Idea, idea_id)
        if idea is None:
            raise ValueError("Idea not found")

        matrix = self._select_related_work_matrix(
            idea.id,
            related_work_matrix_id,
            include_latest_related_work,
        )
        plan = self._select_experiment_plan(
            idea.id,
            experiment_plan_id,
            include_latest_experiment_plan,
        )

        milestone_plan = self._milestone_plan(idea, matrix, plan)
        draft = ProposalDraft(
            idea_id=idea.id,
            status="draft",
            title=self._title(idea),
            abstract=self._abstract(idea, matrix, plan),
            problem_statement=self._problem_statement(idea),
            novelty_statement=self._novelty_statement(idea, matrix),
            related_work_summary=self._related_work_summary(matrix),
            method_summary=self._method_summary(idea),
            experiment_summary=self._experiment_summary(idea, plan),
            risk_mitigation=self._risk_mitigation(idea, matrix, plan),
            milestone_plan_json=milestone_plan,
            evidence_ids_json=idea.evidence_ids_json or [],
            related_work_matrix_id=matrix.id if matrix else None,
            experiment_plan_id=plan.id if plan else None,
            created_by=created_by or "system",
        )
        draft.markdown_export = self._render_markdown(draft)
        self.session.add(draft)
        self.session.commit()
        self.session.refresh(draft)
        ArtifactGraphService(GraphService(self.session)).link_proposal_draft(draft)
        self.session.commit()
        return draft

    def list_for_idea(self, idea_id: str, limit: int = 20) -> list[ProposalDraft]:
        if self.session.get(Idea, idea_id) is None:
            raise ValueError("Idea not found")
        limit = max(1, min(limit, 100))
        return (
            self.session.query(ProposalDraft)
            .filter(ProposalDraft.idea_id == idea_id)
            .order_by(ProposalDraft.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_draft(self, idea_id: str, draft_id: str) -> ProposalDraft | None:
        return (
            self.session.query(ProposalDraft)
            .filter(ProposalDraft.id == draft_id, ProposalDraft.idea_id == idea_id)
            .first()
        )

    def _select_related_work_matrix(
        self,
        idea_id: str,
        matrix_id: str | None,
        include_latest: bool,
    ) -> RelatedWorkMatrix | None:
        if matrix_id:
            matrix = self.session.get(RelatedWorkMatrix, matrix_id)
            if matrix is None or matrix.idea_id != idea_id:
                raise ValueError("Related work matrix not found for idea")
            return matrix
        if not include_latest:
            return None
        return (
            self.session.query(RelatedWorkMatrix)
            .filter(RelatedWorkMatrix.idea_id == idea_id)
            .order_by(RelatedWorkMatrix.created_at.desc())
            .first()
        )

    def _select_experiment_plan(
        self,
        idea_id: str,
        plan_id: str | None,
        include_latest: bool,
    ) -> ExperimentPlan | None:
        if plan_id:
            plan = self.session.get(ExperimentPlan, plan_id)
            if plan is None or plan.idea_id != idea_id:
                raise ValueError("Experiment plan not found for idea")
            return plan
        if not include_latest:
            return None
        return (
            self.session.query(ExperimentPlan)
            .filter(ExperimentPlan.idea_id == idea_id)
            .order_by(ExperimentPlan.created_at.desc())
            .first()
        )

    def _title(self, idea: Idea) -> str:
        return f"Proposal Draft: {self._clean(idea.title)}"

    def _abstract(
        self,
        idea: Idea,
        matrix: RelatedWorkMatrix | None,
        plan: ExperimentPlan | None,
    ) -> str:
        pieces = [
            f"This proposal studies whether {self._clean(idea.core_hypothesis).lower()}",
            f"It targets the research question: {self._clean(idea.research_question)}",
            f"The method sketch is: {self._clean(idea.method_sketch)}",
        ]
        if matrix:
            pieces.append(
                "Related-work screening found "
                f"{len(matrix.items_json or [])} overlap rows and frames the contribution "
                "as a differentiated, still-to-verify novelty claim."
            )
        if plan:
            pieces.append(
                "The first experiment will test the claim with "
                f"{self._clean(plan.main_experiment_json.get('success_criterion', 'a measurable success criterion'))}"
            )
        return " ".join(pieces)

    def _problem_statement(self, idea: Idea) -> str:
        return " ".join(
            [
                f"Research question: {self._clean(idea.research_question)}",
                f"Motivation: {self._clean(idea.motivation)}",
                f"Expected contribution: {self._clean(idea.expected_contribution)}",
            ]
        )

    def _novelty_statement(self, idea: Idea, matrix: RelatedWorkMatrix | None) -> str:
        statements = [self._clean(idea.novelty_argument)]
        if matrix and matrix.differentiators_json:
            statements.append(
                "Differentiation checkpoints: "
                + "; ".join(self._clean(item) for item in matrix.differentiators_json[:3])
            )
        return " ".join(statement for statement in statements if statement)

    def _related_work_summary(self, matrix: RelatedWorkMatrix | None) -> str:
        if matrix is None:
            return (
                "No related-work matrix is attached yet. Generate one before treating this "
                "proposal as ready for external review."
            )

        rows = matrix.items_json or []
        top_rows = []
        for row in rows[:4]:
            top_rows.append(
                f"{row.get('source_type', 'source')}:{row.get('title', 'Untitled')} "
                f"(score={row.get('overlap_score', 0)})"
            )
        return " ".join(
            [
                self._clean(matrix.summary),
                "Nearest rows: " + "; ".join(self._clean(item) for item in top_rows),
            ]
        )

    def _method_summary(self, idea: Idea) -> str:
        parts = [self._clean(idea.method_sketch)]
        if idea.datasets_json:
            parts.append("Datasets: " + ", ".join(self._clean(item) for item in idea.datasets_json))
        if idea.baselines_json:
            parts.append(
                "Baselines: " + ", ".join(self._clean(item) for item in idea.baselines_json)
            )
        if idea.metrics_json:
            parts.append("Metrics: " + ", ".join(self._clean(item) for item in idea.metrics_json))
        return " ".join(parts)

    def _experiment_summary(self, idea: Idea, plan: ExperimentPlan | None) -> str:
        if plan is None:
            return (
                "No experiment plan is attached yet. Minimum next step: define the dataset slice, "
                "baseline, metric, and failure criterion."
            )
        main = plan.main_experiment_json or {}
        return " ".join(
            [
                f"Objective: {self._clean(plan.objective)}",
                f"Hypothesis: {self._clean(plan.hypothesis or idea.core_hypothesis)}",
                f"Main experiment: {self._clean(str(main.get('name') or 'MVP experiment'))}",
                f"Success criterion: {self._clean(str(main.get('success_criterion') or 'Not specified.'))}",
            ]
        )

    def _risk_mitigation(
        self,
        idea: Idea,
        matrix: RelatedWorkMatrix | None,
        plan: ExperimentPlan | None,
    ) -> str:
        risks = [self._clean(item) for item in (idea.risks_json or [])]
        if matrix and matrix.missing_searches_json:
            risks.append(
                "Novelty is incomplete until missing searches are resolved: "
                + ", ".join(matrix.missing_searches_json[:4])
            )
        if plan and plan.failure_modes_json:
            risks.extend(self._clean(item) for item in plan.failure_modes_json[:3])
        if not risks:
            risks.append("Main risk: the proposal has not yet exposed its failure modes.")
        return " ".join(f"- {risk}" for risk in risks)

    def _milestone_plan(
        self,
        idea: Idea,
        matrix: RelatedWorkMatrix | None,
        plan: ExperimentPlan | None,
    ) -> list[dict[str, Any]]:
        related_work_task = (
            "Resolve missing related-work searches and rewrite differentiators."
            if matrix
            else "Generate related-work matrix and inspect nearest overlap rows."
        )
        experiment_task = (
            self._clean(plan.timeline_json.get("week_1", "Build baseline harness."))
            if plan
            else "Create first experiment plan with dataset, baseline, metric, and failure mode."
        )
        validation_task = (
            self._clean(plan.timeline_json.get("week_2", "Run MVP experiment."))
            if plan
            else "Run an MVP experiment that can falsify the core hypothesis."
        )
        return [
            {
                "window": "0-30 days",
                "goal": "Novelty validation and experiment harness",
                "deliverable": related_work_task,
            },
            {
                "window": "31-60 days",
                "goal": "MVP evidence",
                "deliverable": experiment_task,
            },
            {
                "window": "61-90 days",
                "goal": "Ablation and proposal decision",
                "deliverable": validation_task,
            },
            {
                "window": "Decision checkpoint",
                "goal": "Continue, narrow, or archive",
                "deliverable": (
                    "Decide whether the idea deserves paper-track investment based on "
                    f"evidence IDs {', '.join(idea.evidence_ids_json or ['none'])}."
                ),
            },
        ]

    def _render_markdown(self, draft: ProposalDraft) -> str:
        lines = [
            f"# {self._clean(draft.title)}",
            "",
            f"- Proposal Draft ID: `{draft.id}`",
            f"- Idea ID: `{draft.idea_id}`",
            f"- Related Work Matrix ID: `{draft.related_work_matrix_id or 'none'}`",
            f"- Experiment Plan ID: `{draft.experiment_plan_id or 'none'}`",
            f"- Status: `{draft.status}`",
            "",
            "## Abstract",
            "",
            self._clean(draft.abstract),
            "",
            "## Problem Statement",
            "",
            self._clean(draft.problem_statement),
            "",
            "## Novelty Claim",
            "",
            self._clean(draft.novelty_statement),
            "",
            "## Related Work Positioning",
            "",
            self._clean(draft.related_work_summary),
            "",
            "## Method",
            "",
            self._clean(draft.method_summary),
            "",
            "## Experiment Plan",
            "",
            self._clean(draft.experiment_summary),
            "",
            "## Risks And Mitigation",
            "",
            draft.risk_mitigation or "- Not specified.",
            "",
            "## Milestones",
            "",
        ]
        for item in draft.milestone_plan_json or []:
            lines.append(
                f"- {self._clean(item.get('window', 'Window'))}: "
                f"{self._clean(item.get('goal', 'Goal'))} - "
                f"{self._clean(item.get('deliverable', 'Deliverable'))}"
            )
        lines.extend(["", "## Evidence IDs", ""])
        evidence_ids = draft.evidence_ids_json or []
        lines.append(
            ", ".join(f"`{item_id}`" for item_id in evidence_ids) if evidence_ids else "`none`"
        )
        return "\n".join(lines).strip() + "\n"

    def _clean(self, text: str) -> str:
        return " ".join((text or "").split()) or "Not specified."
