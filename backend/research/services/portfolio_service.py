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

    def compare_snapshots(
        self,
        baseline_snapshot_id: str,
        candidate_snapshot_id: str,
    ) -> dict:
        baseline = self.get_snapshot(baseline_snapshot_id)
        candidate = self.get_snapshot(candidate_snapshot_id)
        if baseline is None:
            raise ValueError("Baseline portfolio snapshot not found")
        if candidate is None:
            raise ValueError("Candidate portfolio snapshot not found")

        baseline_items = _items_by_idea_id(baseline.ranked_items_json or [])
        candidate_items = _items_by_idea_id(candidate.ranked_items_json or [])
        baseline_ids = set(baseline_items)
        candidate_ids = set(candidate_items)
        added_ids = sorted(candidate_ids - baseline_ids)
        removed_ids = sorted(baseline_ids - candidate_ids)
        kept_ids = sorted(baseline_ids & candidate_ids)
        rank_changes = [
            _rank_change_payload(baseline_items[idea_id], candidate_items[idea_id])
            for idea_id in kept_ids
        ]
        rank_changes.sort(key=lambda item: (item["to_rank"], item["idea_id"]))
        comparison = {
            "baseline_snapshot_id": baseline.id,
            "candidate_snapshot_id": candidate.id,
            "baseline_title": baseline.title,
            "candidate_title": candidate.title,
            "added_idea_ids": added_ids,
            "removed_idea_ids": removed_ids,
            "kept_idea_ids": kept_ids,
            "rank_changes": rank_changes,
            "summary": (
                f"Compared portfolio snapshots: {len(added_ids)} added, "
                f"{len(removed_ids)} removed, {len(kept_ids)} kept."
            ),
        }
        comparison["markdown_export"] = render_portfolio_comparison_markdown(comparison)
        return comparison


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


def render_portfolio_agenda_markdown(snapshot: IdeaPortfolioSnapshot) -> str:
    items = snapshot.ranked_items_json or []
    lines = [
        f"# Research Execution Agenda: {_clean_text(snapshot.title)}",
        "",
        f"- Portfolio Snapshot ID: `{snapshot.id}`",
        f"- Ranked idea count: {len(items)}",
        f"- Created by: {_clean_text(snapshot.created_by)}",
        "",
        "## Focus",
        "",
        _clean_text(snapshot.description)
        or "Advance the highest-ranked ideas through quick novelty validation, MVP experiments, and decision checkpoints.",
        "",
        "## Priority Tracks",
        "",
    ]
    if not items:
        lines.append("No ideas are saved in this portfolio snapshot.")
        return _finish(lines)

    for item in items[:5]:
        lines.extend(_agenda_track(item))

    lines.extend(
        [
            "",
            "## 30/60/90 Day Plan",
            "",
            "### First 30 Days",
            "",
            "- Re-run novelty checks for the top ranked ideas against newly added papers.",
            "- Convert the top idea into one executable MVP experiment.",
            "- Freeze datasets, baselines, metrics, and a failure criterion before running experiments.",
            "",
            "### Days 31-60",
            "",
            "- Run ablations and robustness checks for the strongest MVP result.",
            "- Archive or revise ideas whose novelty or feasibility weakens after experiments.",
            "- Save a new portfolio snapshot and compare it against this baseline.",
            "",
            "### Days 61-90",
            "",
            "- Turn the leading track into a paper outline or workshop submission plan.",
            "- Use reviewer simulation to identify missing experiments before writing.",
            "- Decide whether the portfolio supports one full paper, a benchmark paper, or multiple follow-up ideas.",
        ]
    )
    return _finish(lines)


def render_portfolio_comparison_markdown(comparison: dict) -> str:
    lines = [
        "# Research Idea Portfolio Comparison",
        "",
        f"- Baseline: `{comparison['baseline_snapshot_id']}` {_clean_text(comparison['baseline_title'])}",
        f"- Candidate: `{comparison['candidate_snapshot_id']}` {_clean_text(comparison['candidate_title'])}",
        f"- Added: {len(comparison['added_idea_ids'])}",
        f"- Removed: {len(comparison['removed_idea_ids'])}",
        f"- Kept: {len(comparison['kept_idea_ids'])}",
        "",
        "## Added Ideas",
        "",
    ]
    lines.extend(_render_id_list(comparison["added_idea_ids"]))
    lines.extend(["", "## Removed Ideas", ""])
    lines.extend(_render_id_list(comparison["removed_idea_ids"]))
    lines.extend(["", "## Rank Changes", ""])
    if not comparison["rank_changes"]:
        lines.append("No overlapping ideas to compare.")
    for item in comparison["rank_changes"]:
        lines.extend(
            [
                f"### {_clean_text(item['title'])}",
                "",
                f"- Idea ID: `{item['idea_id']}`",
                f"- Rank: {item['from_rank']} -> {item['to_rank']} ({item['rank_delta']:+d})",
                f"- Score: {item['from_score']} -> {item['to_score']} ({item['score_delta']:+.3f})",
                f"- Status: `{item['status']}`",
                "",
            ]
        )
    return _finish(lines)


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


def _agenda_track(item: dict) -> list[str]:
    title = _clean_text(item.get("title") or "Untitled idea")
    idea_id = _clean_text(item.get("idea_id") or "unknown")
    score = item.get("weighted_score", "unknown")
    rationale = item.get("rationale") or []
    lines = [
        f"### {item.get('rank', '?')}. {title}",
        "",
        f"- Idea ID: `{idea_id}`",
        f"- Portfolio score: {score}",
        f"- Status: `{_clean_text(item.get('status') or 'unknown')}`",
    ]
    if item.get("parent_idea_id"):
        lines.append(f"- Parent Idea ID: `{_clean_text(item['parent_idea_id'])}`")
    if rationale:
        lines.extend(["", "Rationale:"])
        lines.extend(f"- {_clean_text(reason)}" for reason in rationale[:4])
    lines.extend(
        [
            "",
            "Execution steps:",
            "- Validate nearest related-work collisions and update the novelty claim.",
            "- Define one MVP experiment with a pass/fail criterion.",
            "- Run the baseline, proposed variant, and one ablation before expanding scope.",
            "- Record human feedback after the first result and save a new portfolio snapshot.",
            "",
        ]
    )
    return lines


def _items_by_idea_id(items: list[dict]) -> dict[str, dict]:
    return {str(item.get("idea_id")): item for item in items if item.get("idea_id")}


def _rank_change_payload(baseline: dict, candidate: dict) -> dict:
    from_rank = int(baseline.get("rank") or 0)
    to_rank = int(candidate.get("rank") or 0)
    from_score = float(baseline.get("weighted_score") or 0.0)
    to_score = float(candidate.get("weighted_score") or 0.0)
    return {
        "idea_id": candidate.get("idea_id") or baseline.get("idea_id"),
        "title": candidate.get("title") or baseline.get("title") or "Untitled idea",
        "from_rank": from_rank,
        "to_rank": to_rank,
        "rank_delta": from_rank - to_rank,
        "from_score": round(from_score, 3),
        "to_score": round(to_score, 3),
        "score_delta": round(to_score - from_score, 3),
        "status": candidate.get("status") or baseline.get("status") or "",
        "parent_idea_id": candidate.get("parent_idea_id") or baseline.get("parent_idea_id"),
    }


def _render_id_list(ids: list[str]) -> list[str]:
    if not ids:
        return ["None."]
    return [f"- `{item_id}`" for item_id in ids]


def _inline_ids(ids: list[str]) -> str:
    if not ids:
        return "`none`"
    return ", ".join(f"`{_clean_text(item_id)}`" for item_id in ids)


def _clean_text(text: str) -> str:
    return " ".join(str(text or "").split())


def _finish(lines: list[str]) -> str:
    return "\n".join(lines).strip() + "\n"
