from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from backend.research.models import ExperimentPlan, Idea, NoveltyCheck, ResearchGap, Review
from backend.research.services.graph_service import GraphService


@dataclass
class IdeaRefinementResult:
    source_idea: Idea
    refined_idea: Idea
    applied_actions: list[str]


class IdeaRefinementService:
    def __init__(self, session: Session):
        self.session = session

    def refine_idea(
        self,
        idea_id: str,
        *,
        focus: str = "",
        preserve_evidence: bool = True,
    ) -> IdeaRefinementResult:
        idea = self.session.get(Idea, idea_id)
        if idea is None:
            raise ValueError("Idea not found")

        reviews = self._load_reviews(idea.id)
        novelty_checks = self._load_novelty_checks(idea.id)
        plans = self._load_experiment_plans(idea.id)
        gaps = self._load_gaps(idea.related_gap_ids_json or [])
        applied_actions = self._applied_actions(focus, reviews, novelty_checks, plans)
        refined = self._build_refined_idea(
            idea=idea,
            focus=focus,
            preserve_evidence=preserve_evidence,
            reviews=reviews,
            novelty_checks=novelty_checks,
            plans=plans,
            gaps=gaps,
            applied_actions=applied_actions,
        )

        self.session.add(refined)
        self.session.flush()
        self._link_refinement(refined, idea, gaps, applied_actions, focus)
        self.session.commit()
        self.session.refresh(idea)
        self.session.refresh(refined)
        return IdeaRefinementResult(
            source_idea=idea,
            refined_idea=refined,
            applied_actions=applied_actions,
        )

    def _build_refined_idea(
        self,
        *,
        idea: Idea,
        focus: str,
        preserve_evidence: bool,
        reviews: list[Review],
        novelty_checks: list[NoveltyCheck],
        plans: list[ExperimentPlan],
        gaps: list[ResearchGap],
        applied_actions: list[str],
    ) -> Idea:
        latest_review = reviews[0] if reviews else None
        latest_check = novelty_checks[0] if novelty_checks else None
        latest_plan = plans[0] if plans else None
        gap_summary = "; ".join(gap.title for gap in gaps[:2]) or "the attached evidence-backed gap"
        focus_text = (
            self._clean(focus)
            if focus
            else "review concerns, novelty risk, and the first executable experiment"
        )

        return Idea(
            title=self._refined_title(idea.title, focus),
            research_question=(
                f"{idea.research_question} Revision focus: can the idea address {gap_summary} "
                f"while making the claim testable around {focus_text}?"
            ),
            core_hypothesis=(
                f"{idea.core_hypothesis} The revised hypothesis is that a narrower, "
                "gap-targeted setup can produce a measurable effect before scaling the idea."
            ),
            motivation=self._refined_motivation(idea, latest_review, latest_check),
            related_gap_ids_json=idea.related_gap_ids_json or [],
            related_paper_ids_json=idea.related_paper_ids_json or [],
            evidence_ids_json=idea.evidence_ids_json if preserve_evidence else [],
            method_sketch=self._refined_method(idea, latest_review, latest_check, latest_plan),
            expected_contribution=(
                "A revised, proposal-ready contribution that separates the novelty claim, the "
                "first falsifiable experiment, and the fallback diagnostic contribution."
            ),
            novelty_argument=self._refined_novelty_argument(idea, latest_check),
            datasets_json=self._refined_datasets(idea, latest_plan),
            baselines_json=self._refined_baselines(idea, latest_review, latest_plan),
            metrics_json=self._refined_metrics(idea, latest_plan),
            risks_json=self._refined_risks(idea, latest_review, latest_check),
            resource_requirements=self._refined_resources(idea, latest_plan),
            target_venues_json=idea.target_venues_json or [],
            score_json=self._refined_score(idea.score_json or {}, latest_check, latest_plan),
            status="refined",
            version=idea.version + 1,
            parent_idea_id=idea.id,
        )

    def _load_reviews(self, idea_id: str) -> list[Review]:
        return (
            self.session.query(Review)
            .filter(Review.idea_id == idea_id)
            .order_by(Review.created_at.desc())
            .all()
        )

    def _load_novelty_checks(self, idea_id: str) -> list[NoveltyCheck]:
        return (
            self.session.query(NoveltyCheck)
            .filter(NoveltyCheck.idea_id == idea_id)
            .order_by(NoveltyCheck.created_at.desc())
            .all()
        )

    def _load_experiment_plans(self, idea_id: str) -> list[ExperimentPlan]:
        return (
            self.session.query(ExperimentPlan)
            .filter(ExperimentPlan.idea_id == idea_id)
            .order_by(ExperimentPlan.created_at.desc())
            .all()
        )

    def _load_gaps(self, gap_ids: list[str]) -> list[ResearchGap]:
        if not gap_ids:
            return []
        gaps = self.session.query(ResearchGap).filter(ResearchGap.id.in_(gap_ids)).all()
        by_id = {gap.id: gap for gap in gaps}
        return [by_id[gap_id] for gap_id in gap_ids if gap_id in by_id]

    def _applied_actions(
        self,
        focus: str,
        reviews: list[Review],
        novelty_checks: list[NoveltyCheck],
        plans: list[ExperimentPlan],
    ) -> list[str]:
        actions = []
        if focus:
            actions.append(f"Use revision focus: {self._clean(focus)}")
        if reviews:
            actions.extend(reviews[0].action_items_json or [])
            actions.extend(reviews[0].required_experiments_json or [])
        if novelty_checks:
            actions.extend(novelty_checks[0].recommended_actions_json or [])
        if plans:
            main = plans[0].main_experiment_json or {}
            if main.get("success_criterion"):
                actions.append(f"Make success criterion explicit: {main['success_criterion']}")
        if not actions:
            actions.append("Narrow the idea into one falsifiable MVP experiment.")
        return self._unique(actions)[:10]

    def _refined_title(self, title: str, focus: str) -> str:
        base = self._clean(title)
        if focus:
            return f"Refined {self._shorten(focus, 42)}: {self._shorten(base, 74)}"
        if base.lower().startswith("refined"):
            return base
        return f"Refined: {base}"

    def _refined_motivation(
        self,
        idea: Idea,
        review: Review | None,
        check: NoveltyCheck | None,
    ) -> str:
        parts = [idea.motivation]
        if review:
            parts.append(f"Reviewer pressure: {review.summary}")
        if check:
            parts.append(
                f"Novelty screening reports {check.risk_level} risk, so the revision must "
                "state what is different from the nearest collision signals."
            )
        return " ".join(self._clean(part) for part in parts if part)

    def _refined_method(
        self,
        idea: Idea,
        review: Review | None,
        check: NoveltyCheck | None,
        plan: ExperimentPlan | None,
    ) -> str:
        steps = [f"Start from the original method: {self._clean(idea.method_sketch)}"]
        if plan:
            main = plan.main_experiment_json or {}
            if main.get("setup"):
                steps.append(f"Use the planned MVP setup: {self._clean(str(main['setup']))}")
            if main.get("success_criterion"):
                steps.append(
                    f"Declare the first pass/fail criterion: {self._clean(str(main['success_criterion']))}"
                )
        if review and review.required_experiments_json:
            steps.append(
                "Run reviewer-required checks: "
                + "; ".join(self._clean(item) for item in review.required_experiments_json[:3])
            )
        if check and check.collision_signals_json:
            nearest = check.collision_signals_json[0]
            steps.append(
                "Compare against nearest collision signal "
                f"{nearest.get('source_type', 'source')}:{nearest.get('source_id', 'unknown')} "
                f"before claiming novelty."
            )
        return " ".join(steps)

    def _refined_novelty_argument(self, idea: Idea, check: NoveltyCheck | None) -> str:
        if check is None:
            return (
                f"Refined novelty claim: {self._clean(idea.novelty_argument)} The claim must be "
                "verified against recent external literature before submission."
            )

        signal_text = "no specific collision signal"
        if check.collision_signals_json:
            signal = check.collision_signals_json[0]
            signal_text = (
                f"{signal.get('source_type', 'source')} `{signal.get('source_id', 'unknown')}`"
            )
        return (
            f"Refined novelty claim: the idea is not merely another instance of {signal_text}; "
            "it is differentiated by a gap-specific diagnostic target, an explicit failure "
            f"criterion, and a narrowed MVP experiment. Current screening risk is {check.risk_level}."
        )

    def _refined_datasets(self, idea: Idea, plan: ExperimentPlan | None) -> list[str]:
        items = list(idea.datasets_json or [])
        if plan:
            items.extend(plan.datasets_json or [])
        items.append("Gap-targeted diagnostic slice from the source-paper setting.")
        return self._unique(items)

    def _refined_baselines(
        self,
        idea: Idea,
        review: Review | None,
        plan: ExperimentPlan | None,
    ) -> list[str]:
        items = list(idea.baselines_json or [])
        if plan:
            items.extend(plan.baselines_json or [])
        if review:
            items.append("Reviewer-requested source-paper baseline.")
        items.append("Nearest local collision signal baseline.")
        return self._unique(items)

    def _refined_metrics(self, idea: Idea, plan: ExperimentPlan | None) -> list[str]:
        items = list(idea.metrics_json or [])
        if plan:
            items.extend(plan.metrics_json or [])
        items.extend(["First-experiment pass/fail indicator", "Novelty collision distance"])
        return self._unique(items)

    def _refined_risks(
        self,
        idea: Idea,
        review: Review | None,
        check: NoveltyCheck | None,
    ) -> list[str]:
        risks = list(idea.risks_json or [])
        if review:
            risks.extend(review.major_concerns_json or [])
        if check:
            risks.append(f"Novelty screening risk remains {check.risk_level}.")
            risks.extend(check.missing_searches_json or [])
        risks.append(
            "The refined scope may become too narrow unless the diagnostic result is strong."
        )
        return self._unique(risks)

    def _refined_resources(self, idea: Idea, plan: ExperimentPlan | None) -> str:
        parts = [idea.resource_requirements]
        if plan and plan.compute_requirements:
            parts.append(f"Planned MVP compute: {plan.compute_requirements}")
        parts.append("Prioritize a one-week feasibility slice before scaling.")
        return " ".join(self._clean(part) for part in parts if part)

    def _refined_score(
        self,
        score: dict[str, Any],
        check: NoveltyCheck | None,
        plan: ExperimentPlan | None,
    ) -> dict[str, Any]:
        novelty = self._float_score(score.get("novelty"), 3.0)
        feasibility = self._float_score(score.get("feasibility"), 3.0)
        impact = self._float_score(score.get("impact"), 3.0)
        evidence_support = self._float_score(score.get("evidence_support"), 3.0)
        experimental = self._float_score(score.get("experimental_verifiability"), 3.0)
        resource_cost = self._float_score(score.get("resource_cost"), 3.0)
        publication = self._float_score(score.get("publication_potential"), 3.0)

        if check:
            if check.risk_level == "high":
                novelty = max(1.5, novelty - 0.8)
                publication = max(1.5, publication - 0.4)
            elif check.risk_level == "medium":
                novelty = max(2.0, novelty - 0.4)
            elif check.risk_level == "low":
                evidence_support = min(5.0, evidence_support + 0.2)
        if plan:
            feasibility = min(5.0, feasibility + 0.3)
            experimental = min(5.0, experimental + 0.4)

        overall = round(
            (novelty + feasibility + impact + evidence_support + experimental + publication) / 6,
            2,
        )
        return {
            "novelty": round(novelty, 2),
            "feasibility": round(feasibility, 2),
            "impact": round(impact, 2),
            "evidence_support": round(evidence_support, 2),
            "experimental_verifiability": round(experimental, 2),
            "resource_cost": round(resource_cost, 2),
            "publication_potential": round(publication, 2),
            "overall_score": overall,
            "rationale": (
                "Refined score after incorporating reviewer actions, novelty screening risk, "
                "and experiment-plan readiness."
            ),
        }

    def _link_refinement(
        self,
        refined: Idea,
        source: Idea,
        gaps: list[ResearchGap],
        applied_actions: list[str],
        focus: str,
    ) -> None:
        graph = GraphService(self.session)
        refined_node = graph.get_or_create_node(
            node_type="idea",
            label=refined.title,
            canonical_key=refined.id,
            payload={
                "status": refined.status,
                "version": refined.version,
                "parent_idea_id": source.id,
            },
        )
        source_node = graph.get_or_create_node(
            node_type="idea",
            label=source.title,
            canonical_key=source.id,
            payload={"status": source.status, "version": source.version},
        )
        graph.create_edge(
            source_node=refined_node,
            target_node=source_node,
            edge_type="idea_refines_idea",
            evidence_ids=refined.evidence_ids_json or [],
            payload={"focus": focus, "applied_actions": applied_actions},
        )
        for gap in gaps:
            gap_node = graph.get_or_create_node(
                node_type="gap",
                label=gap.title,
                canonical_key=gap.id,
                payload={"gap_type": gap.gap_type, "status": gap.status},
            )
            graph.create_edge(
                source_node=refined_node,
                target_node=gap_node,
                edge_type="idea_addresses_gap",
                evidence_ids=gap.evidence_ids_json or [],
                payload={"source": "idea_refinement"},
            )

    def _float_score(self, value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _unique(self, items: list[str]) -> list[str]:
        seen = set()
        result = []
        for item in items:
            cleaned = self._clean(str(item))
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                result.append(cleaned)
        return result

    def _clean(self, text: str) -> str:
        return " ".join((text or "").split())

    def _shorten(self, text: str, max_len: int) -> str:
        compact = self._clean(text)
        if len(compact) <= max_len:
            return compact
        return compact[: max_len - 3].rstrip() + "..."
