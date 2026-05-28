from typing import Any

from sqlalchemy.orm import Session

from backend.research.models import (
    Evidence,
    ExperimentPlan,
    Idea,
    NoveltyCheck,
    Paper,
    PaperCard,
    ResearchGap,
    Review,
)


CARD_FIELDS = [
    ("Problem", "problem_json"),
    ("Motivation", "motivation_json"),
    ("Contributions", "contributions_json"),
    ("Method", "method_json"),
    ("Datasets", "datasets_json"),
    ("Metrics", "metrics_json"),
    ("Baselines", "baselines_json"),
    ("Results", "results_json"),
    ("Limitations", "limitations_json"),
    ("Future Work", "future_work_json"),
    ("Open Questions", "open_questions_json"),
]


class ExportService:
    def __init__(self, session: Session):
        self.session = session

    def render_paper_card_markdown(self, paper_id: str) -> str:
        paper = self.session.get(Paper, paper_id)
        if paper is None:
            raise ValueError("Paper not found")

        card = (
            self.session.query(PaperCard)
            .filter(PaperCard.paper_id == paper_id)
            .order_by(PaperCard.updated_at.desc())
            .first()
        )
        if card is None:
            raise ValueError("Paper card not found")

        lines = [
            f"# Paper Card: {self._clean(paper.title or paper.filename or paper.id)}",
            "",
            f"- Paper ID: `{paper.id}`",
            f"- Status: `{paper.status}`",
            f"- Extraction: `{card.extraction_status}` via `{card.extraction_model or 'unknown'}`",
        ]
        if paper.authors_json:
            lines.append(f"- Authors: {', '.join(self._clean(author) for author in paper.authors_json)}")
        if paper.year:
            lines.append(f"- Year: {paper.year}")
        if paper.venue:
            lines.append(f"- Venue: {self._clean(paper.venue)}")

        keywords = self._items(card.keywords_json)
        if keywords:
            lines.extend(["", "## Keywords", "", ", ".join(f"`{self._clean(item)}`" for item in keywords)])

        for title, attr in CARD_FIELDS:
            lines.extend(["", f"## {title}", ""])
            lines.extend(self._render_card_items(getattr(card, attr, None)))

        return self._finish(lines)

    def render_idea_markdown(self, idea_id: str) -> str:
        idea = self.session.get(Idea, idea_id)
        if idea is None:
            raise ValueError("Idea not found")

        gaps = self._load_gaps(idea.related_gap_ids_json or [])
        evidence = self._load_evidence(idea.evidence_ids_json or [])
        reviews = self._load_reviews(idea.id)
        novelty_checks = self._load_novelty_checks(idea.id)
        plans = self._load_experiment_plans(idea.id)

        lines = [
            f"# Research Idea Dossier: {self._clean(idea.title)}",
            "",
            f"- Idea ID: `{idea.id}`",
            f"- Status: `{idea.status}`",
            f"- Version: {idea.version}",
            f"- Related Gap IDs: {self._inline_ids(idea.related_gap_ids_json or [])}",
            f"- Related Paper IDs: {self._inline_ids(idea.related_paper_ids_json or [])}",
            f"- Evidence IDs: {self._inline_ids(idea.evidence_ids_json or [])}",
            "",
            "## Research Question",
            "",
            self._clean(idea.research_question),
            "",
            "## Core Hypothesis",
            "",
            self._clean(idea.core_hypothesis),
            "",
            "## Motivation",
            "",
            self._clean(idea.motivation),
            "",
            "## Method Sketch",
            "",
            self._clean(idea.method_sketch),
            "",
            "## Expected Contribution",
            "",
            self._clean(idea.expected_contribution),
            "",
            "## Novelty Argument",
            "",
            self._clean(idea.novelty_argument),
        ]

        lines.extend(self._render_simple_list("Datasets", idea.datasets_json or []))
        lines.extend(self._render_simple_list("Baselines", idea.baselines_json or []))
        lines.extend(self._render_simple_list("Metrics", idea.metrics_json or []))
        lines.extend(self._render_simple_list("Risks", idea.risks_json or []))
        lines.extend(self._render_score(idea.score_json or {}))
        lines.extend(self._render_gaps(gaps))
        lines.extend(self._render_evidence(evidence))
        lines.extend(self._render_novelty_checks(novelty_checks))
        lines.extend(self._render_reviews(reviews))
        lines.extend(self._render_experiment_plans(plans))

        return self._finish(lines)

    def _load_gaps(self, gap_ids: list[str]) -> list[ResearchGap]:
        if not gap_ids:
            return []
        return (
            self.session.query(ResearchGap)
            .filter(ResearchGap.id.in_(gap_ids))
            .order_by(ResearchGap.created_at.asc())
            .all()
        )

    def _load_evidence(self, evidence_ids: list[str]) -> list[Evidence]:
        if not evidence_ids:
            return []
        return (
            self.session.query(Evidence)
            .filter(Evidence.id.in_(evidence_ids))
            .order_by(Evidence.created_at.asc())
            .all()
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

    def _render_card_items(self, field_json: dict | None) -> list[str]:
        items = self._items(field_json)
        if not items:
            return ["No extracted items yet."]

        lines = []
        for item in items:
            if isinstance(item, dict):
                text = self._clean(str(item.get("text") or ""))
                evidence_ids = item.get("evidence_ids") or []
                confidence = item.get("confidence")
                suffix_parts = []
                if evidence_ids:
                    suffix_parts.append(f"evidence: {self._inline_ids(evidence_ids)}")
                if confidence is not None:
                    suffix_parts.append(f"confidence: {confidence}")
                suffix = f" ({'; '.join(suffix_parts)})" if suffix_parts else ""
                lines.append(f"- {text}{suffix}")
            else:
                lines.append(f"- {self._clean(str(item))}")
        return lines

    def _render_simple_list(self, title: str, items: list[Any]) -> list[str]:
        lines = ["", f"## {title}", ""]
        if not items:
            return lines + ["Not specified."]
        return lines + [f"- {self._clean(str(item))}" for item in items]

    def _render_score(self, score: dict[str, Any]) -> list[str]:
        lines = ["", "## Idea Score", ""]
        if not score:
            return lines + ["No score yet."]

        preferred_keys = [
            "overall_score",
            "novelty",
            "feasibility",
            "impact",
            "evidence_support",
            "experimental_verifiability",
            "resource_cost",
            "publication_potential",
        ]
        for key in preferred_keys:
            if score.get(key) is not None:
                lines.append(f"- {key}: {score[key]}")
        if score.get("rationale"):
            lines.extend(["", self._clean(str(score["rationale"]))])
        return lines

    def _render_gaps(self, gaps: list[ResearchGap]) -> list[str]:
        lines = ["", "## Related Research Gaps", ""]
        if not gaps:
            return lines + ["No related gaps are attached."]

        for gap in gaps:
            lines.extend(
                [
                    f"### {self._clean(gap.title)}",
                    "",
                    f"- Gap ID: `{gap.id}`",
                    f"- Type: `{gap.gap_type}`",
                    f"- Evidence IDs: {self._inline_ids(gap.evidence_ids_json or [])}",
                    "",
                    self._clean(gap.description),
                    "",
                    f"Why important: {self._clean(gap.why_important)}",
                    "",
                    f"Why unsolved: {self._clean(gap.why_unsolved)}",
                ]
            )
            lines.extend(self._render_simple_list("Possible Approaches", gap.possible_approaches_json or []))
        return lines

    def _render_evidence(self, evidence: list[Evidence]) -> list[str]:
        lines = ["", "## Evidence", ""]
        if not evidence:
            return lines + ["No evidence records are attached."]

        for item in evidence:
            lines.extend(
                [
                    f"### `{item.id}`",
                    "",
                    f"- Type: `{item.evidence_type}`",
                    f"- Paper ID: `{item.paper_id}`",
                    f"- Confidence: {item.confidence}",
                    "",
                    self._clean(item.summary or item.text),
                ]
            )
        return lines

    def _render_novelty_checks(self, novelty_checks: list[NoveltyCheck]) -> list[str]:
        lines = ["", "## Novelty Check", ""]
        if not novelty_checks:
            return lines + ["No novelty check has been generated."]

        latest = novelty_checks[0]
        lines.extend(
            [
                f"- Novelty Check ID: `{latest.id}`",
                f"- Risk Level: `{latest.risk_level}`",
                f"- Local Overlap Score: {latest.local_overlap_score}",
                "",
                self._clean(latest.summary),
            ]
        )
        lines.extend(self._render_simple_list("Recommended Actions", latest.recommended_actions_json or []))

        signals = latest.collision_signals_json or []
        lines.extend(["", "### Collision Signals", ""])
        if not signals:
            lines.append("No local collision signals found.")
        for signal in signals:
            label = self._clean(str(signal.get("label") or "Untitled signal"))
            source_type = self._clean(str(signal.get("source_type") or "source"))
            source_id = self._clean(str(signal.get("source_id") or "unknown"))
            score = signal.get("score")
            lines.append(f"- `{source_type}` `{source_id}` score={score}: {label}")

        lines.extend(self._render_simple_list("Missing Searches", latest.missing_searches_json or []))
        return lines

    def _render_reviews(self, reviews: list[Review]) -> list[str]:
        lines = ["", "## Reviewer Simulation", ""]
        if not reviews:
            return lines + ["No reviewer simulation has been generated."]

        latest = reviews[0]
        lines.extend(
            [
                f"- Review ID: `{latest.id}`",
                f"- Reviewer: `{latest.reviewer_type}`",
                f"- Decision: `{latest.decision}`",
                "",
                self._clean(latest.summary),
            ]
        )
        lines.extend(self._render_simple_list("Major Concerns", latest.major_concerns_json or []))
        lines.extend(self._render_simple_list("Required Experiments", latest.required_experiments_json or []))
        lines.extend(self._render_simple_list("Action Items", latest.action_items_json or []))
        return lines

    def _render_experiment_plans(self, plans: list[ExperimentPlan]) -> list[str]:
        lines = ["", "## Experiment Plan", ""]
        if not plans:
            return lines + ["No experiment plan has been generated."]

        latest = plans[0]
        lines.extend(
            [
                f"- Plan ID: `{latest.id}`",
                "",
                "### Objective",
                "",
                self._clean(latest.objective),
                "",
                "### Hypothesis",
                "",
                self._clean(latest.hypothesis),
            ]
        )
        lines.extend(self._render_simple_list("Datasets", latest.datasets_json or []))
        lines.extend(self._render_simple_list("Baselines", latest.baselines_json or []))
        lines.extend(self._render_simple_list("Metrics", latest.metrics_json or []))

        main = latest.main_experiment_json or {}
        lines.extend(["", "### Main Experiment", ""])
        if main:
            for key, value in main.items():
                lines.append(f"- {self._clean(str(key))}: {self._clean(str(value))}")
        else:
            lines.append("Not specified.")

        lines.extend(self._render_named_dicts("Ablation Studies", latest.ablation_studies_json or []))
        lines.extend(self._render_named_dicts("Robustness Tests", latest.robustness_tests_json or []))
        lines.extend(self._render_named_dicts("Expected Tables", latest.expected_tables_json or []))
        lines.extend(self._render_simple_list("Failure Modes", latest.failure_modes_json or []))
        lines.extend(["", "### Fallback Plan", "", self._clean(latest.fallback_plan)])
        lines.extend(["", "### Compute Requirements", "", self._clean(latest.compute_requirements)])
        lines.extend(["", "### Timeline", ""])
        for key, value in (latest.timeline_json or {}).items():
            lines.append(f"- {self._clean(str(key))}: {self._clean(str(value))}")
        return lines

    def _render_named_dicts(self, title: str, items: list[dict[str, Any]]) -> list[str]:
        lines = ["", f"### {title}", ""]
        if not items:
            return lines + ["Not specified."]

        for item in items:
            name = self._clean(str(item.get("name") or item.get("title") or "Item"))
            lines.append(f"- {name}")
            for key, value in item.items():
                if key in {"name", "title"}:
                    continue
                if isinstance(value, list):
                    value_text = ", ".join(self._clean(str(part)) for part in value)
                else:
                    value_text = self._clean(str(value))
                lines.append(f"  - {self._clean(str(key))}: {value_text}")
        return lines

    def _items(self, value: dict | None) -> list[Any]:
        if not value:
            return []
        items = value.get("items", value)
        return items if isinstance(items, list) else []

    def _inline_ids(self, ids: list[str]) -> str:
        if not ids:
            return "`none`"
        return ", ".join(f"`{self._clean(str(item_id))}`" for item_id in ids)

    def _clean(self, text: str) -> str:
        return " ".join((text or "").split()) or "Not specified."

    def _finish(self, lines: list[str]) -> str:
        return "\n".join(lines).strip() + "\n"
