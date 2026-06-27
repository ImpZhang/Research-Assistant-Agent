from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from backend.research.models import ExperimentRun, Idea, ResearchBrief
from backend.research.schemas import ReplayCaseCreate
from backend.research.services.agent_trace_service import AgentTraceService
from backend.research.services.benchmark_evidence_service import BenchmarkEvidenceService
from backend.research.services.literature_search_service import LiteratureSearchService
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
        benchmark_readiness = BenchmarkEvidenceService(self.session).readiness_for_idea(idea_id)
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
            "benchmark_evidence_readiness": _compact_benchmark_readiness(benchmark_readiness),
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

    def create_external_search_evidence(
        self,
        idea_id: str,
        *,
        review_package_id: str = "",
        queries: list[str] | None = None,
        include_external: bool = True,
        limit: int = 8,
        created_by: str = "researcher",
    ) -> ResearchBrief:
        idea = self.session.get(Idea, idea_id)
        if idea is None:
            raise ValueError("Idea not found")
        package = self._load_review_package(idea_id, review_package_id)
        query_list = self._external_search_queries(idea, package, queries or [])
        limit = max(1, min(limit, 20))
        searches = []
        service = LiteratureSearchService(self.session)
        for query in query_list:
            try:
                response = service.search(
                    query=query,
                    limit=limit,
                    include_external=include_external,
                )
                searches.append(
                    {
                        "query": response.query,
                        "local_status": response.local_status,
                        "external_status": response.external_status,
                        "items": [_literature_item_payload(item) for item in response.items],
                        "message": response.message,
                    }
                )
            except ValueError as exc:
                searches.append(
                    {
                        "query": query,
                        "local_status": "failed",
                        "external_status": "not_run",
                        "items": [],
                        "message": str(exc),
                    }
                )
        summary = self._external_search_summary(
            idea=idea,
            package=package,
            searches=searches,
            include_external=include_external,
        )
        brief = ResearchBrief(
            title=f"SOTA External Search Evidence - {idea.title[:160]}",
            scope="sota_external_search_evidence",
            idea_ids_json=[idea.id],
            summary_json=summary,
            markdown_export=self._render_external_search_markdown(idea, summary),
            created_by=created_by or "researcher",
        )
        self.session.add(brief)
        self.session.commit()
        self.session.refresh(brief)
        return brief

    def list_external_search_evidence(
        self,
        idea_id: str,
        limit: int = 20,
    ) -> list[ResearchBrief]:
        if self.session.get(Idea, idea_id) is None:
            raise ValueError("Idea not found")
        limit = max(1, min(limit, 100))
        briefs = (
            self.session.query(ResearchBrief)
            .filter(ResearchBrief.scope == "sota_external_search_evidence")
            .order_by(ResearchBrief.created_at.desc())
            .limit(300)
            .all()
        )
        return [brief for brief in briefs if idea_id in (brief.idea_ids_json or [])][:limit]

    def get_external_search_evidence(
        self,
        idea_id: str,
        brief_id: str,
    ) -> ResearchBrief | None:
        brief = self.session.get(ResearchBrief, brief_id)
        if (
            brief is None
            or brief.scope != "sota_external_search_evidence"
            or idea_id not in (brief.idea_ids_json or [])
        ):
            return None
        return brief

    def create_signoff(
        self,
        idea_id: str,
        *,
        review_package_id: str = "",
        external_search_evidence_id: str = "",
        decision: str = "needs_more_search",
        reviewer: str = "researcher",
        external_searches_completed: bool = False,
        nearest_work: list[dict[str, Any]] | None = None,
        evidence_links: list[dict[str, Any]] | None = None,
        benchmark_run_ids: list[str] | None = None,
        final_novelty_claim: str = "",
        limitations: list[str] | None = None,
        notes: str = "",
        created_by: str = "researcher",
    ) -> ResearchBrief:
        idea = self.session.get(Idea, idea_id)
        if idea is None:
            raise ValueError("Idea not found")

        package = self._load_review_package(idea_id, review_package_id)
        external_search_evidence = self._load_external_search_evidence(
            idea_id,
            external_search_evidence_id,
        )
        effective_external_search_completed = self._effective_external_search_completed(
            external_searches_completed,
            external_search_evidence,
        )
        benchmark_runs = self._load_benchmark_runs(idea_id, benchmark_run_ids or [])
        benchmark_readiness = BenchmarkEvidenceService(self.session).readiness_for_idea(idea_id)
        clean_nearest_work = [_compact_mapping(row) for row in (nearest_work or [])]
        clean_evidence_links = [_compact_mapping(row) for row in (evidence_links or [])]
        clean_limitations = _unique([str(item) for item in (limitations or [])])
        signoff_status = self._signoff_status(
            decision=decision,
            external_searches_completed=effective_external_search_completed,
            nearest_work=clean_nearest_work,
            benchmark_runs=benchmark_runs,
        )
        summary = {
            "idea_id": idea.id,
            "idea_title": idea.title,
            "review_package_id": package.id if package else "",
            "external_search_evidence_id": (
                external_search_evidence.id if external_search_evidence else ""
            ),
            "decision": decision,
            "signoff_status": signoff_status,
            "reviewer": reviewer or "researcher",
            "external_searches_completed": external_searches_completed,
            "effective_external_search_completed": effective_external_search_completed,
            "external_search_status": (
                (external_search_evidence.summary_json or {}).get("search_status", "")
                if external_search_evidence
                else ""
            ),
            "nearest_work": clean_nearest_work,
            "evidence_links": clean_evidence_links,
            "benchmark_run_ids": [run.id for run in benchmark_runs],
            "benchmark_run_statuses": {run.id: run.status for run in benchmark_runs},
            "benchmark_evidence_readiness": _compact_benchmark_readiness(benchmark_readiness),
            "final_novelty_claim": final_novelty_claim.strip(),
            "limitations": clean_limitations,
            "notes": notes.strip(),
            "manual_gate_summary": self._manual_gate_summary(
                decision=decision,
                signoff_status=signoff_status,
                external_searches_completed=effective_external_search_completed,
                nearest_work=clean_nearest_work,
                benchmark_runs=benchmark_runs,
                benchmark_readiness=benchmark_readiness,
            ),
        }
        brief = ResearchBrief(
            title=f"SOTA Signoff - {idea.title[:180]}",
            scope="sota_signoff_record",
            idea_ids_json=[idea.id],
            summary_json=summary,
            markdown_export=self._render_signoff_markdown(idea, summary, benchmark_runs),
            created_by=created_by or reviewer or "researcher",
        )
        self.session.add(brief)
        self.session.commit()
        self.session.refresh(brief)
        self._capture_sota_false_positive_replay_case(idea, brief, summary)
        return brief

    def list_signoffs_for_idea(self, idea_id: str, limit: int = 20) -> list[ResearchBrief]:
        if self.session.get(Idea, idea_id) is None:
            raise ValueError("Idea not found")
        limit = max(1, min(limit, 100))
        briefs = (
            self.session.query(ResearchBrief)
            .filter(ResearchBrief.scope == "sota_signoff_record")
            .order_by(ResearchBrief.created_at.desc())
            .limit(300)
            .all()
        )
        return [brief for brief in briefs if idea_id in (brief.idea_ids_json or [])][:limit]

    def get_signoff(self, idea_id: str, brief_id: str) -> ResearchBrief | None:
        brief = self.session.get(ResearchBrief, brief_id)
        if (
            brief is None
            or brief.scope != "sota_signoff_record"
            or idea_id not in (brief.idea_ids_json or [])
        ):
            return None
        return brief

    def _capture_sota_false_positive_replay_case(
        self,
        idea: Idea,
        signoff: ResearchBrief,
        summary: dict[str, Any],
    ) -> None:
        manual_gate = summary.get("manual_gate_summary") or {}
        if summary.get("signoff_status") != "sota_confirmed":
            return
        if bool(manual_gate.get("ready_for_sota_claim", False)):
            return

        AgentTraceService(self.session).create_replay_case(
            ReplayCaseCreate(
                case_type="sota_readiness_false_positive",
                query=(
                    "SOTA signoff was confirmed while manual readiness gates were not closed: "
                    f"{idea.title}"
                ),
                expected={
                    "idea_id": idea.id,
                    "sota_signoff_id": signoff.id,
                    "signoff_status": "sota_confirmed",
                    "require_ready_for_sota_claim": True,
                    "require_effective_external_search_completed": True,
                    "require_benchmark_evidence_ready": True,
                    "min_nearest_work_count": 1,
                    "min_benchmark_run_count": 1,
                    "max_sota_blocker_count": 0,
                    "live_status": "completed",
                },
                observed={
                    "signoff_status": summary.get("signoff_status", ""),
                    "ready_for_sota_claim": bool(manual_gate.get("ready_for_sota_claim", False)),
                    "effective_external_search_completed": bool(
                        summary.get("effective_external_search_completed", False)
                    ),
                    "benchmark_evidence_ready": bool(
                        manual_gate.get("benchmark_evidence_ready_for_sota_review", False)
                    ),
                    "sota_blockers": manual_gate.get("blockers") or [],
                    "nearest_work_count": len(summary.get("nearest_work") or []),
                    "benchmark_run_count": len(summary.get("benchmark_run_ids") or []),
                },
                verdict="needs_review",
                notes="Automatically captured from SOTA signoff manual gate mismatch.",
                metadata={
                    "source": "sota_signoff_record",
                    "sota_signoff_id": signoff.id,
                    "idea_id": idea.id,
                },
            )
        )

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

    def _external_search_queries(
        self,
        idea: Idea,
        package: ResearchBrief | None,
        explicit_queries: list[str],
    ) -> list[str]:
        package_queries = []
        if package is not None:
            package_queries = list((package.summary_json or {}).get("review_queries") or [])
        candidates = explicit_queries + package_queries
        if not candidates:
            candidates = [
                " ".join([idea.title, "state of the art benchmark"]),
                " ".join([idea.title, idea.method_sketch, "nearest work"]),
                " ".join(
                    [
                        idea.core_hypothesis,
                        " ".join(idea.datasets_json or []),
                        " ".join(idea.metrics_json or []),
                    ]
                ),
            ]
        return [_compact_query(query) for query in _unique(candidates) if _compact_query(query)][:6]

    def _external_search_summary(
        self,
        *,
        idea: Idea,
        package: ResearchBrief | None,
        searches: list[dict[str, Any]],
        include_external: bool,
    ) -> dict[str, Any]:
        external_statuses = [search.get("external_status", "") for search in searches]
        result_count = sum(len(search.get("items") or []) for search in searches)
        external_items = [
            item
            for search in searches
            for item in search.get("items", [])
            if item.get("provider") != "local"
        ]
        missing_searches = self._external_missing_searches(include_external, external_statuses)
        search_status = self._external_search_status(include_external, external_statuses)
        return {
            "idea_id": idea.id,
            "idea_title": idea.title,
            "review_package_id": package.id if package else "",
            "include_external": include_external,
            "search_status": search_status,
            "ready_for_signoff": search_status == "external_completed",
            "query_count": len(searches),
            "result_count": result_count,
            "external_result_count": len(external_items),
            "external_statuses": external_statuses,
            "missing_searches": missing_searches,
            "queries": [search.get("query", "") for search in searches],
            "searches": searches,
        }

    def _external_search_status(
        self,
        include_external: bool,
        external_statuses: list[str],
    ) -> str:
        if not include_external:
            return "external_not_requested"
        if external_statuses and all(status == "completed" for status in external_statuses):
            return "external_completed"
        if any(status.startswith("partial:") for status in external_statuses):
            return "external_partial"
        if any(status.startswith("rate_limited:") for status in external_statuses):
            return "external_rate_limited"
        if any(status == "disabled" for status in external_statuses):
            return "external_disabled"
        if any(status.startswith("failed:") for status in external_statuses):
            return "external_failed"
        return "external_not_completed"

    def _external_missing_searches(
        self,
        include_external: bool,
        external_statuses: list[str],
    ) -> list[str]:
        if not include_external:
            return ["external_literature_search_not_requested"]
        missing = []
        for status in external_statuses:
            if status == "completed":
                continue
            if status == "disabled":
                missing.append("external_literature_search_disabled")
            elif status.startswith("partial:"):
                missing.append("external_literature_search_partial")
            elif status.startswith("rate_limited:"):
                missing.append("external_literature_search_rate_limited")
            elif status.startswith("failed:"):
                missing.append("external_literature_search_failed")
            else:
                missing.append("external_literature_search_not_completed")
        return _unique(missing)

    def _load_review_package(self, idea_id: str, review_package_id: str) -> ResearchBrief | None:
        if not review_package_id:
            return None
        package = self.session.get(ResearchBrief, review_package_id)
        if (
            package is None
            or package.scope != "sota_review_package"
            or idea_id not in (package.idea_ids_json or [])
        ):
            raise ValueError("SOTA review package not found")
        return package

    def _load_external_search_evidence(
        self,
        idea_id: str,
        evidence_id: str,
    ) -> ResearchBrief | None:
        if not evidence_id:
            return None
        evidence = self.session.get(ResearchBrief, evidence_id)
        if (
            evidence is None
            or evidence.scope != "sota_external_search_evidence"
            or idea_id not in (evidence.idea_ids_json or [])
        ):
            raise ValueError("SOTA external search evidence not found")
        return evidence

    def _effective_external_search_completed(
        self,
        external_searches_completed: bool,
        external_search_evidence: ResearchBrief | None,
    ) -> bool:
        if external_searches_completed:
            return True
        if external_search_evidence is None:
            return False
        summary = external_search_evidence.summary_json or {}
        return bool(summary.get("ready_for_signoff"))

    def _load_benchmark_runs(
        self,
        idea_id: str,
        benchmark_run_ids: list[str],
    ) -> list[ExperimentRun]:
        runs: list[ExperimentRun] = []
        for run_id in _unique(benchmark_run_ids):
            run = self.session.get(ExperimentRun, run_id)
            if run is None or run.idea_id != idea_id:
                raise ValueError("Benchmark run not found")
            runs.append(run)
        return runs

    def _signoff_status(
        self,
        *,
        decision: str,
        external_searches_completed: bool,
        nearest_work: list[dict[str, Any]],
        benchmark_runs: list[ExperimentRun],
    ) -> str:
        if decision == "not_novel":
            return "rejected_not_novel"
        if decision == "benchmark_required":
            return "benchmark_required"
        if decision == "needs_more_search":
            return "needs_more_search"
        if not external_searches_completed:
            return "provisional_missing_external_search"
        if not nearest_work:
            return "provisional_missing_nearest_work"
        if any(run.status not in {"completed", "inconclusive"} for run in benchmark_runs):
            return "provisional_benchmark_run_open"
        return "sota_confirmed"

    def _manual_gate_summary(
        self,
        *,
        decision: str,
        signoff_status: str,
        external_searches_completed: bool,
        nearest_work: list[dict[str, Any]],
        benchmark_runs: list[ExperimentRun],
        benchmark_readiness: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        blockers: list[str] = []
        if not external_searches_completed:
            blockers.append("external_searches_not_completed")
        if decision == "confirmed_novel" and not nearest_work:
            blockers.append("nearest_work_not_recorded")
        if any(run.status not in {"completed", "inconclusive"} for run in benchmark_runs):
            blockers.append("benchmark_run_not_final")
        if decision == "confirmed_novel" and not bool(
            (benchmark_readiness or {}).get("ready_for_sota_review", False)
        ):
            blockers.append("benchmark_evidence_not_ready")
        return {
            "ready_for_sota_claim": signoff_status == "sota_confirmed" and not blockers,
            "requires_human_review": signoff_status != "sota_confirmed",
            "blockers": blockers,
            "nearest_work_count": len(nearest_work),
            "benchmark_run_count": len(benchmark_runs),
            "benchmark_evidence_ready_for_sota_review": bool(
                (benchmark_readiness or {}).get("ready_for_sota_review", False)
            ),
            "benchmark_evidence_readiness_status": (benchmark_readiness or {}).get(
                "readiness_status",
                "",
            ),
            "benchmark_evidence_missing_items": (benchmark_readiness or {}).get(
                "missing_items",
                [],
            ),
            "benchmark_evidence_warnings": (benchmark_readiness or {}).get("warnings", []),
        }

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
        lines.extend(["", "## Benchmark Evidence Readiness", ""])
        readiness = summary.get("benchmark_evidence_readiness") or {}
        lines.append(f"- Status: `{readiness.get('readiness_status', 'unknown')}`")
        lines.append(f"- Ready For SOTA Review: `{readiness.get('ready_for_sota_review', False)}`")
        lines.append(
            f"- Completed Benchmark Runs: {readiness.get('completed_benchmark_run_count', 0)}"
        )
        lines.append(f"- Comparison Briefs: {readiness.get('benchmark_comparison_count', 0)}")
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

    def _render_signoff_markdown(
        self,
        idea: Idea,
        summary: dict[str, Any],
        benchmark_runs: list[ExperimentRun],
    ) -> str:
        lines = [
            "# SOTA Signoff Record",
            "",
            f"- Idea: `{idea.title}`",
            f"- Decision: `{summary['decision']}`",
            f"- Signoff Status: `{summary['signoff_status']}`",
            f"- Reviewer: `{summary['reviewer']}`",
            f"- External Searches Completed: `{summary['external_searches_completed']}`",
            f"- Effective External Search Completed: `{summary['effective_external_search_completed']}`",
            f"- Review Package: `{summary['review_package_id'] or 'none'}`",
            f"- External Search Evidence: `{summary['external_search_evidence_id'] or 'none'}`",
            "",
            "## Final Novelty Claim",
            "",
            summary["final_novelty_claim"] or "No final novelty claim recorded.",
            "",
            "## Nearest Work",
            "",
        ]
        nearest_work = summary.get("nearest_work") or []
        if nearest_work:
            for row in nearest_work:
                lines.append(
                    "- "
                    f"{row.get('title', 'Untitled work')} "
                    f"({row.get('year', 'year unknown')}): "
                    f"{row.get('relationship', row.get('notes', 'relationship not recorded'))}"
                )
        else:
            lines.append("- No nearest work recorded.")

        lines.extend(["", "## Benchmark Runs", ""])
        if benchmark_runs:
            for run in benchmark_runs:
                lines.append(
                    f"- `{run.id}` {run.title} "
                    f"status={run.status}, metrics={list((run.metric_results_json or {}).keys())}"
                )
        else:
            lines.append("- No benchmark run linked.")

        lines.extend(["", "## Evidence Links", ""])
        evidence_links = summary.get("evidence_links") or []
        if evidence_links:
            for link in evidence_links:
                label = link.get("label") or link.get("id") or link.get("url") or "evidence"
                target = link.get("url") or link.get("id") or link.get("path") or ""
                lines.append(f"- {label}: {target}")
        else:
            lines.append("- No evidence links recorded.")

        lines.extend(["", "## Manual Gate", ""])
        gate = summary.get("manual_gate_summary") or {}
        lines.append(f"- Ready For SOTA Claim: `{gate.get('ready_for_sota_claim', False)}`")
        lines.append(
            "- Benchmark Evidence Ready: "
            f"`{gate.get('benchmark_evidence_ready_for_sota_review', False)}`"
        )
        if gate.get("benchmark_evidence_readiness_status"):
            lines.append(
                f"- Benchmark Evidence Status: `{gate.get('benchmark_evidence_readiness_status')}`"
            )
        blockers = gate.get("blockers") or []
        if blockers:
            lines.extend(f"- Blocker: `{blocker}`" for blocker in blockers)
        else:
            lines.append("- No signoff blockers recorded.")

        if summary.get("limitations"):
            lines.extend(["", "## Limitations", ""])
            lines.extend(f"- {item}" for item in summary["limitations"])
        if summary.get("notes"):
            lines.extend(["", "## Notes", "", summary["notes"]])
        return "\n".join(lines).strip() + "\n"

    def _render_external_search_markdown(
        self,
        idea: Idea,
        summary: dict[str, Any],
    ) -> str:
        lines = [
            "# SOTA External Search Evidence",
            "",
            f"- Idea: `{idea.title}`",
            f"- Search Status: `{summary['search_status']}`",
            f"- Ready For Signoff: `{summary['ready_for_signoff']}`",
            f"- Review Package: `{summary['review_package_id'] or 'none'}`",
            f"- Query Count: {summary['query_count']}",
            f"- Result Count: {summary['result_count']}",
            f"- External Result Count: {summary['external_result_count']}",
            "",
            "## Queries",
            "",
        ]
        lines.extend(f"- {query}" for query in summary.get("queries") or [])
        if summary.get("missing_searches"):
            lines.extend(["", "## Missing Searches", ""])
            lines.extend(f"- `{item}`" for item in summary["missing_searches"])
        lines.extend(["", "## Results", ""])
        for search in summary.get("searches") or []:
            lines.append(
                f"### {search.get('query', 'query')}\n\n"
                f"- External Status: `{search.get('external_status', '')}`\n"
                f"- Local Status: `{search.get('local_status', '')}`"
            )
            items = search.get("items") or []
            if not items:
                lines.append("- No results recorded.")
                continue
            for item in items[:8]:
                lines.append(
                    "- "
                    f"`{item.get('provider', '')}` "
                    f"{item.get('title', 'Untitled')} "
                    f"({item.get('year', 'year unknown')}) "
                    f"score={item.get('score', 0.0)}"
                )
        return "\n".join(lines).strip() + "\n"


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


def _compact_mapping(row: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, value in row.items():
        if value is None:
            continue
        if isinstance(value, str):
            clean = " ".join(value.split())
            if clean:
                compact[str(key)] = clean[:1000]
        elif isinstance(value, (int, float, bool)):
            compact[str(key)] = value
        else:
            compact[str(key)] = value
    return compact


def _compact_benchmark_readiness(readiness: dict[str, Any]) -> dict[str, Any]:
    return {
        "readiness_status": readiness.get("readiness_status", ""),
        "ready_for_sota_review": bool(readiness.get("ready_for_sota_review", False)),
        "benchmark_run_count": int(readiness.get("benchmark_run_count", 0) or 0),
        "completed_benchmark_run_count": int(
            readiness.get("completed_benchmark_run_count", 0) or 0
        ),
        "benchmark_comparison_count": int(readiness.get("benchmark_comparison_count", 0) or 0),
        "latest_completed_run_id": readiness.get("latest_completed_run_id", ""),
        "latest_comparison_brief_id": readiness.get("latest_comparison_brief_id", ""),
        "latest_comparison_status": readiness.get("latest_comparison_status", ""),
        "missing_items": list(readiness.get("missing_items") or []),
        "warnings": list(readiness.get("warnings") or []),
        "recommended_actions": list(readiness.get("recommended_actions") or []),
    }


def _literature_item_payload(item: Any) -> dict[str, Any]:
    return {
        "provider": item.provider,
        "source_id": item.source_id,
        "title": item.title,
        "authors": item.authors,
        "year": item.year,
        "venue": item.venue,
        "url": item.url,
        "abstract": item.abstract[:800],
        "score": item.score,
        "metadata": item.metadata,
    }
