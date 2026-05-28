from sqlalchemy.orm import Session

from backend.research.models import Idea, IdeaPortfolioSnapshot
from backend.research.services.idea_ranking_service import IdeaRankingService, RankedIdea


class PortfolioService:
    def __init__(self, session: Session):
        self.session = session

    def create_snapshot(
        self,
        *,
        title: str,
        description: str = "",
        created_by: str = "researcher",
        idea_ids: list[str] | None = None,
        gap_ids: list[str] | None = None,
        paper_ids: list[str] | None = None,
        limit: int = 10,
        weights: dict[str, float] | None = None,
        include_refined: bool = True,
        deduplicate_lineage: bool = True,
    ) -> IdeaPortfolioSnapshot:
        ranking_request = {
            "idea_ids": idea_ids or [],
            "gap_ids": gap_ids or [],
            "paper_ids": paper_ids or [],
            "limit": limit,
            "weights": weights or {},
            "include_refined": include_refined,
            "deduplicate_lineage": deduplicate_lineage,
        }
        ranked = IdeaRankingService(self.session).rank_ideas(**ranking_request)
        markdown = render_idea_portfolio_markdown(title, ranked)
        snapshot = IdeaPortfolioSnapshot(
            title=_clean_text(title) or "Research Idea Portfolio",
            description=_clean_text(description),
            ranking_request_json=ranking_request,
            idea_ids_json=[item.idea.id for item in ranked],
            ranked_items_json=[_ranked_item_payload(item) for item in ranked],
            markdown_export=markdown,
            created_by=_clean_text(created_by) or "researcher",
        )
        self.session.add(snapshot)
        self.session.commit()
        self.session.refresh(snapshot)
        return snapshot

    def list_snapshots(self, limit: int = 50) -> list[IdeaPortfolioSnapshot]:
        limit = max(1, min(limit, 200))
        return (
            self.session.query(IdeaPortfolioSnapshot)
            .order_by(IdeaPortfolioSnapshot.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_snapshot(self, snapshot_id: str) -> IdeaPortfolioSnapshot | None:
        return self.session.get(IdeaPortfolioSnapshot, snapshot_id)


def render_idea_portfolio_markdown(title: str, ranked_items: list[RankedIdea]) -> str:
    clean_title = _clean_text(title) or "Research Idea Portfolio"
    lines = [
        f"# {clean_title}",
        "",
        f"- Ranked idea count: {len(ranked_items)}",
        "- Ranking method: weighted heuristic with novelty, feasibility, impact, evidence, experiment readiness, resource efficiency, and human feedback adjustments.",
    ]

    if not ranked_items:
        lines.extend(["", "No ranked ideas matched the request."])
        return _finish(lines)

    for item in ranked_items:
        idea = item.idea
        lines.extend(
            [
                "",
                f"## {item.rank}. {_clean_text(idea.title)}",
                "",
                f"- Idea ID: `{idea.id}`",
                f"- Parent Idea ID: `{idea.parent_idea_id or 'none'}`",
                f"- Status: `{idea.status}`",
                f"- Weighted score: {item.weighted_score}",
                f"- Related Gap IDs: {_inline_ids(idea.related_gap_ids_json or [])}",
                f"- Related Paper IDs: {_inline_ids(idea.related_paper_ids_json or [])}",
                "",
                "### Score Breakdown",
                "",
            ]
        )
        for key, value in item.score_breakdown.items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "### Ranking Rationale", ""])
        lines.extend(f"- {_clean_text(reason)}" for reason in item.rationale)
        lines.extend(
            [
                "",
                "### Research Question",
                "",
                _clean_text(idea.research_question),
                "",
                "### Core Hypothesis",
                "",
                _clean_text(idea.core_hypothesis),
                "",
                "### First Method Sketch",
                "",
                _clean_text(idea.method_sketch),
            ]
        )
    return _finish(lines)


def render_snapshot_markdown(snapshot: IdeaPortfolioSnapshot) -> str:
    return snapshot.markdown_export


def _ranked_item_payload(item: RankedIdea) -> dict:
    idea: Idea = item.idea
    return {
        "rank": item.rank,
        "idea_id": idea.id,
        "title": idea.title,
        "parent_idea_id": idea.parent_idea_id,
        "weighted_score": item.weighted_score,
        "score_breakdown": item.score_breakdown,
        "rationale": item.rationale,
        "status": idea.status,
        "version": idea.version,
    }


def _inline_ids(ids: list[str]) -> str:
    if not ids:
        return "`none`"
    return ", ".join(f"`{_clean_text(item_id)}`" for item_id in ids)


def _clean_text(text: str) -> str:
    return " ".join(str(text or "").split())


def _finish(lines: list[str]) -> str:
    return "\n".join(lines).strip() + "\n"
