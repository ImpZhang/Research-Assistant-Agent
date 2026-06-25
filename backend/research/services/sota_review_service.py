from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from backend.research.models import Idea, ResearchBrief
from backend.research.services.novelty_service import NoveltyService
from backend.research.services.related_work_service import RelatedWorkService


class SotaReviewPackageService:
    def __init__(self, session: Session):
        self.session = session

    def create_package(
        self,
        idea_id: str,
        *,
        include_external: bool = False,
        limit: int = 8,
        created_by: str = "researcher",
    ) -> ResearchBrief:
        idea = self.session.get(Idea, idea_id)
        if idea is None:
            raise ValueError("Idea not found")

        limit = max(1, min(limit, 20))
        novelty = NoveltyService(self.session).create_check(
            idea_id,
            include_external_literature=include_external,
            limit=limit,
            mode="manual_sota_review_package",
        )
        matrix = RelatedWorkService(self.session).create_matrix(
            idea_id,
            include_external=include_external,
            limit=limit,
            created_by=created_by,
        )
        review_queries = self._review_queries(idea, matrix.query)
        missing_searches = _unique(
            list(novelty.missing_searches_json or []) + list(matrix.missing_searches_json or [])
        )
        checklist = self._manual_checklist(include_external, missing_searches)
        summary = {
            "idea_id": idea.id,
            "idea_title": idea.title,
            "review_status": self._review_status(novelty.risk_level, missing_searches),
            "novelty_check_id": novelty.id,
            "related_work_matrix_id": matrix.id,
            "novelty_risk_level": novelty.risk_level,
            "local_overlap_score": novelty.local_overlap_score,
            "external_overlap_score": novelty.external_overlap_score,
            "include_external": include_external,
            "review_queries": review_queries,
            "missing_searches": missing_searches,
            "manual_checklist": checklist,
            "collision_signal_count": len(novelty.collision_signals_json or []),
            "related_work_item_count": len(matrix.items_json or []),
        }
        brief = ResearchBrief(
            title=f"SOTA Review Package - {idea.title[:160]}",
            scope="sota_review_package",
            idea_ids_json=[idea.id],
            summary_json=summary,
            markdown_export=self._render_markdown(
                idea=idea,
                summary=summary,
                collision_signals=novelty.collision_signals_json or [],
                related_rows=matrix.items_json or [],
                differentiators=matrix.differentiators_json or [],
            ),
            created_by=created_by or "researcher",
        )
        self.session.add(brief)
        self.session.commit()
        self.session.refresh(brief)
        return brief

    def list_packages_for_idea(self, idea_id: str, limit: int = 20) -> list[ResearchBrief]:
        if self.session.get(Idea, idea_id) is None:
            raise ValueError("Idea not found")
        limit = max(1, min(limit, 100))
        briefs = (
            self.session.query(ResearchBrief)
            .filter(ResearchBrief.scope == "sota_review_package")
            .order_by(ResearchBrief.created_at.desc())
            .limit(300)
            .all()
        )
        return [brief for brief in briefs if idea_id in (brief.idea_ids_json or [])][:limit]

    def get_package(self, idea_id: str, brief_id: str) -> ResearchBrief | None:
        brief = self.session.get(ResearchBrief, brief_id)
        if (
            brief is None
            or brief.scope != "sota_review_package"
            or idea_id not in (brief.idea_ids_json or [])
        ):
            return None
        return brief

    def _review_queries(self, idea: Idea, base_query: str) -> list[str]:
        candidates = [
            base_query,
            " ".join([idea.title, "state of the art", "baseline", "benchmark"]),
            " ".join(
                [
                    idea.title,
                    idea.method_sketch,
                    " ".join(idea.datasets_json or []),
                    " ".join(idea.metrics_json or []),
                ]
            ),
            " ".join(
                [
                    idea.core_hypothesis,
                    idea.novelty_argument,
                    "nearest work ablation evaluation",
                ]
            ),
        ]
        return [_compact_query(query) for query in _unique(candidates) if _compact_query(query)]

    def _manual_checklist(self, include_external: bool, missing_searches: list[str]) -> list[str]:
        checklist = [
            "Search the exact idea title, core hypothesis, method terms, datasets, and metrics.",
            "Record the nearest paper, year, benchmark setting, metric, and claimed delta.",
            "Compare the generated idea against every high-overlap local evidence, gap, idea, and literature row.",
            "Rewrite the novelty claim as one falsifiable sentence after nearest-work review.",
            "Update the decision memo before changing the idea status from revise to pursue.",
        ]
        if not include_external:
            checklist.insert(0, "Run external literature search before claiming novelty.")
        if missing_searches:
            checklist.append("Close missing searches: " + ", ".join(missing_searches[:8]) + ".")
        return checklist

    def _review_status(self, risk_level: str, missing_searches: list[str]) -> str:
        if missing_searches or risk_level in {"high", "medium", "unknown"}:
            return "manual_sota_review_required"
        return "candidate_ready_for_advisor_sota_confirmation"

    def _render_markdown(
        self,
        *,
        idea: Idea,
        summary: dict[str, Any],
        collision_signals: list[dict[str, Any]],
        related_rows: list[dict[str, Any]],
        differentiators: list[str],
    ) -> str:
        lines = [
            "# SOTA Review Package",
            "",
            f"- Idea: `{idea.title}`",
            f"- Review Status: `{summary['review_status']}`",
            f"- Novelty Risk: `{summary['novelty_risk_level']}`",
            f"- Local Overlap Score: `{summary['local_overlap_score']}`",
            f"- External Overlap Score: `{summary['external_overlap_score']}`",
            f"- Novelty Check: `{summary['novelty_check_id']}`",
            f"- Related Work Matrix: `{summary['related_work_matrix_id']}`",
            "",
            "## Review Queries",
            "",
        ]
        lines.extend(f"- {query}" for query in summary["review_queries"])
        lines.extend(["", "## Manual Checklist", ""])
        lines.extend(f"- [ ] {item}" for item in summary["manual_checklist"])
        lines.extend(["", "## Collision Signals", ""])
        if collision_signals:
            for signal in collision_signals[:8]:
                lines.append(
                    "- "
                    f"`{signal.get('source_type', '')}` "
                    f"{signal.get('label', '')} "
                    f"(score={signal.get('score', 0.0)})"
                )
        else:
            lines.append("- No local collision signals were found.")
        lines.extend(["", "## Related Work Rows", ""])
        if related_rows:
            for row in related_rows[:8]:
                lines.append(
                    "- "
                    f"`{row.get('source_type', '')}` "
                    f"{row.get('title', '')} "
                    f"(overlap={row.get('overlap_score', 0.0)})"
                )
        else:
            lines.append("- No related-work rows were found.")
        lines.extend(["", "## Differentiators", ""])
        if differentiators:
            lines.extend(f"- {item}" for item in differentiators[:8])
        else:
            lines.append("- Add a differentiator after nearest-work review.")
        if summary["missing_searches"]:
            lines.extend(["", "## Missing Searches", ""])
            lines.extend(f"- {item}" for item in summary["missing_searches"])
        return "\n".join(lines)


def _compact_query(query: str, limit: int = 360) -> str:
    return " ".join((query or "").split())[:limit]


def _unique(items: list[str]) -> list[str]:
    seen = set()
    unique = []
    for item in items:
        clean = " ".join(str(item or "").split())
        key = clean.lower()
        if clean and key not in seen:
            unique.append(clean)
            seen.add(key)
    return unique
