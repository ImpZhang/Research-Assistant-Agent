from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REPORT_DIR = PROJECT_ROOT / "outputs" / "evaluations"
REPORT_ID_RE = re.compile(r"^real_paper_eval_[0-9]{8}_[0-9]{6}$")


@dataclass(frozen=True)
class RealPaperEvaluationReport:
    report_id: str
    filename: str
    started_at: str
    finished_at: str
    summary: dict[str, Any]
    papers: list[dict[str, Any]]
    markdown_export: str
    json_available: bool
    markdown_available: bool


class EvaluationReportService:
    def __init__(self, report_dir: Path | str = DEFAULT_REPORT_DIR):
        self.report_dir = Path(report_dir)

    def list_real_paper_reports(self, limit: int = 20) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 100))
        report_ids = self._report_ids()
        reports = [self.load_real_paper_report(report_id) for report_id in report_ids[:limit]]
        return [self._summary(report) for report in reports]

    def load_latest_real_paper_report(self) -> dict[str, Any]:
        report_ids = self._report_ids()
        if not report_ids:
            raise FileNotFoundError("No real-paper evaluation reports found.")
        return self._detail(self.load_real_paper_report(report_ids[0]))

    def load_real_paper_report_detail(self, report_id: str) -> dict[str, Any]:
        return self._detail(self.load_real_paper_report(report_id))

    def load_real_paper_report(self, report_id: str) -> RealPaperEvaluationReport:
        if not REPORT_ID_RE.match(report_id):
            raise ValueError("Invalid real-paper evaluation report id.")

        json_path = self.report_dir / f"{report_id}.json"
        markdown_path = self.report_dir / f"{report_id}.md"
        if not json_path.is_file() and not markdown_path.is_file():
            raise FileNotFoundError(f"Real-paper evaluation report not found: {report_id}")

        payload: dict[str, Any] = {}
        if json_path.is_file():
            payload = json.loads(json_path.read_text(encoding="utf-8"))

        markdown_export = ""
        if markdown_path.is_file():
            markdown_export = markdown_path.read_text(encoding="utf-8")

        return RealPaperEvaluationReport(
            report_id=report_id,
            filename=f"{report_id}.json" if json_path.is_file() else f"{report_id}.md",
            started_at=str(payload.get("started_at") or ""),
            finished_at=str(payload.get("finished_at") or ""),
            summary=dict(payload.get("summary") or {}),
            papers=list(payload.get("papers") or []),
            markdown_export=markdown_export,
            json_available=json_path.is_file(),
            markdown_available=markdown_path.is_file(),
        )

    def _report_ids(self) -> list[str]:
        if not self.report_dir.is_dir():
            return []
        ids = {
            path.stem
            for path in self.report_dir.glob("real_paper_eval_*.json")
            if REPORT_ID_RE.match(path.stem)
        }
        ids.update(
            path.stem
            for path in self.report_dir.glob("real_paper_eval_*.md")
            if REPORT_ID_RE.match(path.stem)
        )
        return sorted(ids, reverse=True)

    def _summary(self, report: RealPaperEvaluationReport) -> dict[str, Any]:
        summary = dict(report.summary)
        papers = report.papers
        completed = [paper for paper in papers if paper.get("status") == "completed"]
        readiness_values = [
            float((paper.get("metrics") or {}).get("readiness_score") or 0.0)
            for paper in completed
            if (paper.get("metrics") or {}).get("readiness_score") is not None
        ]
        quality_values = [
            float((paper.get("metrics") or {}).get("quality_score") or 0.0)
            for paper in completed
            if (paper.get("metrics") or {}).get("quality_score") is not None
        ]
        return {
            "report_id": report.report_id,
            "filename": report.filename,
            "started_at": report.started_at,
            "finished_at": report.finished_at,
            "paper_count": int(summary.get("paper_count") or len(papers)),
            "completed_paper_count": int(summary.get("completed_paper_count") or len(completed)),
            "failed_paper_count": int(summary.get("failed_paper_count") or 0),
            "total_gaps": int(summary.get("total_gaps") or 0),
            "total_ideas": int(summary.get("total_ideas") or 0),
            "total_embedding_indexed": int(summary.get("total_embedding_indexed") or 0),
            "embedding_models": list(summary.get("embedding_models") or []),
            "average_readiness": _average(readiness_values),
            "average_quality_gate": _average(quality_values),
            "json_available": report.json_available,
            "markdown_available": report.markdown_available,
        }

    def _detail(self, report: RealPaperEvaluationReport) -> dict[str, Any]:
        payload = self._summary(report)
        payload.update(
            {
                "summary": report.summary,
                "papers": report.papers,
                "markdown_export": report.markdown_export,
                "message": (
                    f"Loaded real-paper evaluation report {report.report_id} "
                    f"with {payload['completed_paper_count']}/{payload['paper_count']} "
                    "completed papers."
                ),
            }
        )
        return payload


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)
