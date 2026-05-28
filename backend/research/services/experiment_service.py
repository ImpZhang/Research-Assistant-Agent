from sqlalchemy.orm import Session

from backend.research.models import ExperimentPlan, Idea


class ExperimentService:
    def __init__(self, session: Session):
        self.session = session

    def list_plans_for_idea(self, idea_id: str) -> list[ExperimentPlan]:
        return (
            self.session.query(ExperimentPlan)
            .filter(ExperimentPlan.idea_id == idea_id)
            .order_by(ExperimentPlan.created_at.desc())
            .all()
        )

    def create_plan(self, idea_id: str) -> ExperimentPlan:
        idea = self.session.get(Idea, idea_id)
        if idea is None:
            raise ValueError("Idea not found")

        plan = ExperimentPlan(
            idea_id=idea.id,
            objective=f"Test whether the idea can answer: {idea.research_question}",
            hypothesis=idea.core_hypothesis,
            datasets_json=idea.datasets_json or [],
            baselines_json=idea.baselines_json or [],
            metrics_json=idea.metrics_json or [],
            main_experiment_json={
                "name": "MVP gap-targeted experiment",
                "setup": idea.method_sketch,
                "success_criterion": "Improves the gap-specific diagnostic metric without degrading the main task metric.",
            },
            ablation_studies_json=[
                {
                    "name": "Remove gap-targeted component",
                    "purpose": "Verify that the proposed component directly contributes to the gap improvement.",
                },
                {
                    "name": "Evidence-free variant",
                    "purpose": "Check whether evidence grounding is actually useful for the method design.",
                },
            ],
            robustness_tests_json=[
                {
                    "name": "Out-of-domain split",
                    "purpose": "Estimate whether the idea generalizes beyond the narrow gap slice.",
                }
            ],
            expected_tables_json=[
                {
                    "title": "Main result",
                    "columns": ["Method", "Main metric", "Gap diagnostic metric", "Cost"],
                },
                {
                    "title": "Ablation",
                    "columns": ["Variant", "Main metric", "Gap diagnostic metric"],
                },
            ],
            failure_modes_json=[
                "The diagnostic metric improves but the main task metric drops.",
                "The baseline already solves the gap after stronger tuning.",
                "The effect is too narrow to support a full-paper claim.",
            ],
            fallback_plan=(
                "If the method does not improve results, convert the contribution into an evaluation "
                "or diagnostic benchmark paper around the documented gap."
            ),
            compute_requirements=idea.resource_requirements,
            timeline_json={
                "week_1": "Build dataset slice and baseline harness.",
                "week_2": "Run baseline and proposed MVP.",
                "week_3": "Run ablations and robustness checks.",
            },
        )
        self.session.add(plan)
        idea.status = "experiment_planned"
        self.session.commit()
        self.session.refresh(plan)
        return plan
