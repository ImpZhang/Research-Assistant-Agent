from collections import Counter
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from backend.research.models import (
    ExperimentPlan,
    Idea,
    IdeaEvidenceLedger,
    IdeaFeedback,
    NoveltyCheck,
    ResearchProfile,
    ResearchTaskEvent,
    Review,
)


DEFAULT_WEIGHTS = {
    "novelty": 0.22,
    "feasibility": 0.18,
    "impact": 0.2,
    "evidence_support": 0.14,
    "experimental_verifiability": 0.16,
    "publication_potential": 0.14,
    "resource_efficiency": 0.1,
}


@dataclass
class RankedIdea:
    rank: int
    idea: Idea
    weighted_score: float
    score_breakdown: dict[str, float]
    rationale: list[str]


class IdeaRankingService:
    def __init__(self, session: Session):
        self.session = session

    def rank_ideas(
        self,
        *,
        idea_ids: list[str] | None = None,
        gap_ids: list[str] | None = None,
        paper_ids: list[str] | None = None,
        limit: int = 10,
        weights: dict[str, float] | None = None,
        include_refined: bool = True,
        deduplicate_lineage: bool = True,
    ) -> list[RankedIdea]:
        ideas = self._load_candidates(idea_ids or [], include_refined)
        ideas = self._filter_by_links(ideas, gap_ids or [], paper_ids or [])
        if deduplicate_lineage:
            ideas = self._deduplicate_lineage(ideas)

        profile = self.session.get(ResearchProfile, "default")
        normalized_weights = self._weights(weights or {}, profile)
        ranked = [self._score_idea(idea, normalized_weights, profile) for idea in ideas]
        ranked.sort(key=lambda item: item.weighted_score, reverse=True)
        ranked = ranked[: max(1, min(limit, 100))]
        for index, item in enumerate(ranked, start=1):
            item.rank = index
        return ranked

    def _load_candidates(self, idea_ids: list[str], include_refined: bool) -> list[Idea]:
        query = self.session.query(Idea).order_by(Idea.created_at.desc())
        if idea_ids:
            query = query.filter(Idea.id.in_(idea_ids))
        ideas = query.all()
        if include_refined:
            return ideas
        return [idea for idea in ideas if idea.parent_idea_id is None]

    def _filter_by_links(
        self,
        ideas: list[Idea],
        gap_ids: list[str],
        paper_ids: list[str],
    ) -> list[Idea]:
        if not gap_ids and not paper_ids:
            return ideas

        gap_set = set(gap_ids)
        paper_set = set(paper_ids)
        filtered = []
        for idea in ideas:
            idea_gap_ids = set(idea.related_gap_ids_json or [])
            idea_paper_ids = set(idea.related_paper_ids_json or [])
            gap_match = not gap_set or bool(gap_set & idea_gap_ids)
            paper_match = not paper_set or bool(paper_set & idea_paper_ids)
            if gap_match and paper_match:
                filtered.append(idea)
        return filtered

    def _deduplicate_lineage(self, ideas: list[Idea]) -> list[Idea]:
        parent_ids = {idea.parent_idea_id for idea in ideas if idea.parent_idea_id}
        return [idea for idea in ideas if idea.id not in parent_ids]

    def _score_idea(
        self,
        idea: Idea,
        weights: dict[str, float],
        profile: ResearchProfile | None,
    ) -> RankedIdea:
        score = idea.score_json or {}
        components = {
            "novelty": self._score_value(score.get("novelty")),
            "feasibility": self._score_value(score.get("feasibility")),
            "impact": self._score_value(score.get("impact")),
            "evidence_support": self._score_value(score.get("evidence_support")),
            "experimental_verifiability": self._score_value(
                score.get("experimental_verifiability")
            ),
            "publication_potential": self._score_value(score.get("publication_potential")),
            "resource_efficiency": self._resource_efficiency(score.get("resource_cost")),
        }
        weighted = sum(components[key] * weights[key] for key in weights)
        weighted = weighted / sum(weights.values())

        adjustment, rationale, adjustment_breakdown = self._adjustments(idea, profile)
        weighted_score = round(max(0.0, min(5.0, weighted + adjustment)), 3)
        breakdown = {key: round(value, 3) for key, value in components.items()}
        breakdown.update(adjustment_breakdown)
        breakdown["adjustment"] = round(adjustment, 3)
        return RankedIdea(
            rank=0,
            idea=idea,
            weighted_score=weighted_score,
            score_breakdown=breakdown,
            rationale=rationale,
        )

    def _adjustments(
        self,
        idea: Idea,
        profile: ResearchProfile | None,
    ) -> tuple[float, list[str], dict[str, float]]:
        adjustment = 0.0
        rationale = []
        adjustment_breakdown: dict[str, float] = {}
        check = self._latest_for_idea_or_parent(NoveltyCheck, idea)
        review = self._latest_for_idea_or_parent(Review, idea)
        plan = self._latest_for_idea_or_parent(ExperimentPlan, idea)
        feedback_items = self._feedback_for_idea_or_parent(idea)
        (
            claim_adjustment,
            claim_rationale,
            claim_breakdown,
        ) = self._claim_validation_adjustment(idea)

        if idea.parent_idea_id:
            adjustment += 0.15
            rationale.append("Refined idea with parent lineage.")
        if idea.evidence_ids_json:
            evidence_bonus = min(len(idea.evidence_ids_json), 5) * 0.03
            adjustment += evidence_bonus
            rationale.append(f"Grounded by {len(idea.evidence_ids_json)} evidence records.")
        if plan:
            adjustment += 0.2
            rationale.append("Experiment plan exists, so first validation path is clearer.")
        if review:
            if review.decision == "revise":
                adjustment -= 0.05
                rationale.append("Reviewer decision is revise; ranking keeps this as a caution.")
            if review.required_experiments_json:
                rationale.append("Reviewer supplied concrete required experiments.")
        if check:
            if check.risk_level == "high":
                adjustment -= 0.45
                rationale.append("High novelty collision risk lowers the portfolio score.")
            elif check.risk_level == "medium":
                adjustment -= 0.2
                rationale.append("Medium novelty collision risk needs related-work follow-up.")
            elif check.risk_level == "low":
                adjustment += 0.05
                rationale.append("Low novelty collision risk gives a small confidence bonus.")
            else:
                adjustment -= 0.05
                rationale.append("Unknown novelty risk needs more literature search.")
        adjustment += claim_adjustment
        rationale.extend(claim_rationale)
        adjustment_breakdown.update(claim_breakdown)
        if feedback_items:
            feedback_adjustment, feedback_rationale = self._feedback_adjustment(feedback_items)
            adjustment += feedback_adjustment
            rationale.extend(feedback_rationale)
        if profile:
            profile_adjustment, profile_rationale = self._profile_adjustment(idea, profile)
            adjustment += profile_adjustment
            rationale.extend(profile_rationale)
        if not rationale:
            rationale.append(
                "Ranked from intrinsic idea score only; add review and novelty checks."
            )
        return adjustment, rationale, adjustment_breakdown

    def _profile_adjustment(
        self,
        idea: Idea,
        profile: ResearchProfile,
    ) -> tuple[float, list[str]]:
        adjustment = 0.0
        rationale = []
        idea_text = " ".join(
            [
                idea.title,
                idea.research_question,
                idea.core_hypothesis,
                idea.method_sketch,
                idea.expected_contribution,
                idea.novelty_argument,
                " ".join(str(item) for item in (idea.datasets_json or [])),
                " ".join(str(item) for item in (idea.metrics_json or [])),
                " ".join(str(item) for item in (idea.risks_json or [])),
                idea.resource_requirements,
            ]
        ).lower()

        positive_terms = [
            *profile.primary_domains_json,
            *profile.active_questions_json,
            *profile.methodological_preferences_json,
        ]
        matches = [term for term in positive_terms if term and term.lower() in idea_text]
        if matches:
            adjustment += min(len(matches), 4) * 0.04
            rationale.append(
                "Matches research profile terms: " + ", ".join(dict.fromkeys(matches[:4])) + "."
            )

        venue_overlap = set(profile.target_venues_json or []) & set(idea.target_venues_json or [])
        if venue_overlap:
            adjustment += 0.08
            rationale.append("Matches target venue preference.")

        negative_matches = [
            term for term in profile.negative_preferences_json if term and term.lower() in idea_text
        ]
        if negative_matches:
            adjustment -= 0.25
            rationale.append(
                "Conflicts with negative profile preferences: "
                + ", ".join(dict.fromkeys(negative_matches[:3]))
                + "."
            )

        resource_text = " ".join(
            [idea.resource_requirements, " ".join(profile.resource_constraints_json or [])]
        ).lower()
        if profile.risk_tolerance == "low" and any(
            token in resource_text for token in ["gpu", "large", "expensive", "costly"]
        ):
            adjustment -= 0.12
            rationale.append("Low risk tolerance penalizes compute-heavy requirements.")
        elif profile.risk_tolerance == "high":
            adjustment += 0.05
            rationale.append("High risk tolerance allows more speculative ideas.")
        return adjustment, rationale

    def _claim_validation_adjustment(
        self,
        idea: Idea,
    ) -> tuple[float, list[str], dict[str, float]]:
        idea_ids = self._idea_and_parent_ids(idea)
        latest_ledger = (
            self.session.query(IdeaEvidenceLedger)
            .filter(IdeaEvidenceLedger.idea_id.in_(idea_ids))
            .order_by(IdeaEvidenceLedger.created_at.desc())
            .first()
        )
        events = (
            self.session.query(ResearchTaskEvent)
            .filter(
                ResearchTaskEvent.idea_id.in_(idea_ids),
                ResearchTaskEvent.event_type == "claim_validation_result",
            )
            .order_by(ResearchTaskEvent.created_at.desc())
            .limit(50)
            .all()
        )
        by_status = Counter(
            str((event.metadata_json or {}).get("validation_status") or "unknown")
            for event in events
        )
        adjustment = 0.0
        rationale: list[str] = []
        if latest_ledger and latest_ledger.claims_json and not events:
            adjustment -= 0.12
            rationale.append(
                "Evidence ledger claims have no recorded claim validation results yet."
            )
        if by_status.get("supported", 0):
            adjustment += min(by_status["supported"], 3) * 0.08
            rationale.append(
                f"Claim validation supports {by_status['supported']} evidence-ledger claims."
            )
        if by_status.get("needs_more_evidence", 0):
            adjustment -= min(by_status["needs_more_evidence"], 3) * 0.12
            rationale.append(
                "Claim validation found evidence gaps for "
                f"{by_status['needs_more_evidence']} claims."
            )
        if by_status.get("challenged", 0):
            adjustment -= min(by_status["challenged"], 3) * 0.28
            rationale.append(f"Claim validation challenged {by_status['challenged']} claims.")
        if by_status.get("inconclusive", 0):
            adjustment -= min(by_status["inconclusive"], 3) * 0.05
            rationale.append(
                f"Claim validation is inconclusive for {by_status['inconclusive']} claims."
            )
        return (
            adjustment,
            rationale,
            {
                "claim_validation_adjustment": round(adjustment, 3),
                "claim_validation_result_count": float(len(events)),
                "claim_validation_supported": float(by_status.get("supported", 0)),
                "claim_validation_needs_more_evidence": float(
                    by_status.get("needs_more_evidence", 0)
                ),
                "claim_validation_challenged": float(by_status.get("challenged", 0)),
                "claim_validation_inconclusive": float(by_status.get("inconclusive", 0)),
            },
        )

    def _idea_and_parent_ids(self, idea: Idea) -> list[str]:
        idea_ids = [idea.id]
        if idea.parent_idea_id:
            idea_ids.append(idea.parent_idea_id)
        return idea_ids

    def _latest_for_idea_or_parent(self, model, idea: Idea):
        idea_ids = self._idea_and_parent_ids(idea)
        return (
            self.session.query(model)
            .filter(model.idea_id.in_(idea_ids))
            .order_by(model.created_at.desc())
            .first()
        )

    def _feedback_for_idea_or_parent(self, idea: Idea) -> list[IdeaFeedback]:
        idea_ids = self._idea_and_parent_ids(idea)
        return (
            self.session.query(IdeaFeedback)
            .filter(IdeaFeedback.idea_id.in_(idea_ids))
            .order_by(IdeaFeedback.created_at.desc())
            .all()
        )

    def _feedback_adjustment(self, feedback_items: list[IdeaFeedback]) -> tuple[float, list[str]]:
        latest = feedback_items[0]
        decision_adjustments = {
            "accept": 0.45,
            "shortlist": 0.3,
            "revise": 0.05,
            "archive": -0.3,
            "reject": -0.6,
        }
        adjustment = decision_adjustments.get(latest.decision, 0.0)
        rationale = [f"Human feedback decision is {latest.decision}."]
        ratings = [item.rating for item in feedback_items if item.rating is not None]
        if ratings:
            average = sum(ratings) / len(ratings)
            adjustment += (average - 3.0) * 0.12
            rationale.append(
                f"Average human rating is {average:.2f}/5 across {len(ratings)} ratings."
            )
        if latest.tags_json:
            rationale.append(f"Feedback tags: {', '.join(latest.tags_json[:4])}.")
        return adjustment, rationale

    def _weights(
        self,
        weights: dict[str, float],
        profile: ResearchProfile | None,
    ) -> dict[str, float]:
        merged = dict(DEFAULT_WEIGHTS)
        if profile:
            for key, value in (profile.evaluation_weights_json or {}).items():
                if key in merged and value > 0:
                    merged[key] = float(value)
        for key, value in weights.items():
            if key in merged and value > 0:
                merged[key] = float(value)
        return merged

    def _score_value(self, value: Any) -> float:
        try:
            return max(0.0, min(5.0, float(value)))
        except (TypeError, ValueError):
            return 2.5

    def _resource_efficiency(self, resource_cost: Any) -> float:
        cost = self._score_value(resource_cost)
        return max(0.0, min(5.0, 5.0 - cost + 1.0))
