#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.research.db import SessionLocal  # noqa: E402
from backend.research.models import Evidence, Paper, PaperSection  # noqa: E402


DEFAULT_DATASET_DIR = "data/evaluation/geoloc_12paper"
TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9\-]{2,}")
STOP_TERMS = {
    "and",
    "are",
    "before",
    "for",
    "from",
    "how",
    "that",
    "the",
    "this",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
}


@dataclass(frozen=True)
class EvidenceSnapshot:
    evidence_id: str
    paper_id: str = ""
    paper_title: str = ""
    evidence_type: str = ""
    section_title: str = ""
    text: str = ""
    summary: str = ""


def main() -> int:
    args = parse_args()
    dataset_dir = resolve_project_path(Path(args.dataset_dir))
    report = build_report(dataset_dir)
    if args.write_json:
        write_text(
            resolve_project_path(Path(args.write_json)),
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
    if args.write_markdown:
        write_text(resolve_project_path(Path(args.write_markdown)), render_markdown(report))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(
            "Geoloc retrieval miss analysis: "
            f"misses={report['summary']['miss_count']} "
            f"categories={report['summary']['category_counts']}"
        )
    return 0 if report["status"] == "pass" else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify realistic geolocalization retrieval misses without model calls."
    )
    parser.add_argument("--dataset-dir", default=DEFAULT_DATASET_DIR)
    parser.add_argument("--write-json", default="")
    parser.add_argument("--write-markdown", default="")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def build_report(dataset_dir: Path) -> dict[str, Any]:
    quality_path = dataset_dir / "realistic_quality_report.json"
    questions_path = dataset_dir / "realistic_gold_questions.jsonl"
    failures_path = dataset_dir / "realistic_failure_replay_cases.jsonl"
    errors = []
    for path in [quality_path, questions_path, failures_path]:
        if not path.exists():
            errors.append(f"missing required file: {path}")
    if errors:
        return {
            "status": "fail",
            "dataset_dir": str(dataset_dir),
            "errors": errors,
            "summary": {"miss_count": 0, "category_counts": {}},
            "misses": [],
        }

    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    questions = {row["id"]: row for row in read_jsonl(questions_path)}
    failures = read_jsonl(failures_path)
    ids = collect_evidence_ids(questions, failures)
    snapshots = load_evidence_snapshots(ids)
    analyses = [
        analyze_failure(failure, questions, snapshots)
        for failure in failures
        if failure.get("verdict") == "failed"
    ]
    category_counts = Counter(
        category for analysis in analyses for category in analysis["categories"]
    )
    intent_counts = Counter(analysis.get("intent", "") for analysis in analyses)
    return {
        "status": "pass",
        "dataset_dir": str(dataset_dir),
        "quality_metrics": quality.get("metrics", {}).get("retrieval", {}),
        "summary": {
            "miss_count": len(analyses),
            "category_counts": dict(sorted(category_counts.items())),
            "intent_counts": dict(sorted(intent_counts.items())),
            "recommended_next_actions": recommended_next_actions(category_counts),
        },
        "misses": analyses,
        "errors": [],
    }


def analyze_failure(
    failure: dict[str, Any],
    questions: dict[str, dict[str, Any]],
    snapshots: dict[str, EvidenceSnapshot],
) -> dict[str, Any]:
    observed = failure.get("observed") or {}
    expected = failure.get("expected") or {}
    question_id = observed.get("id") or (failure.get("metadata") or {}).get("realistic_gold_id", "")
    question = questions.get(question_id, {})
    query = failure.get("query") or expected.get("query") or question.get("query", "")
    primary_ids = (
        expected.get("primary_gold_evidence_ids") or question.get("primary_gold_evidence_ids") or []
    )
    gold_ids = expected.get("gold_evidence_ids") or question.get("gold_evidence_ids") or []
    supporting_ids = [item for item in gold_ids if item not in set(primary_ids)]
    returned_ids = observed.get("returned_evidence_ids") or []
    primary_snapshots = [snapshots.get(item) for item in primary_ids if snapshots.get(item)]
    returned_snapshots = [snapshots.get(item) for item in returned_ids if snapshots.get(item)]
    returned_paper_ids = {snapshot.paper_id for snapshot in returned_snapshots}
    primary_paper_ids = {snapshot.paper_id for snapshot in primary_snapshots}

    categories = []
    if set(supporting_ids).intersection(returned_ids):
        categories.append("supporting_over_primary")
    if primary_paper_ids and not primary_paper_ids.intersection(returned_paper_ids):
        categories.append("paper_recall_miss")
    elif primary_paper_ids:
        categories.append("same_paper_wrong_evidence")
    if has_query_term_gap(query, question):
        categories.append("query_term_gap")
    if (
        primary_snapshots
        and returned_snapshots
        and candidate_competes(query, primary_snapshots[0], returned_snapshots[0])
    ):
        categories.append("candidate_competition")
    if primary_snapshots and section_granularity_issue(
        question, primary_snapshots[0], returned_snapshots
    ):
        categories.append("section_evidence_granularity")
    if not categories:
        categories.append("unclassified_retrieval_miss")

    return {
        "id": question_id,
        "intent": observed.get("intent") or (failure.get("metadata") or {}).get("intent", ""),
        "query": query,
        "categories": sorted(set(categories)),
        "primary_gold_evidence_ids": primary_ids,
        "supporting_gold_evidence_ids": supporting_ids,
        "returned_evidence_ids": returned_ids,
        "primary_gold": [snapshot_summary(snapshot) for snapshot in primary_snapshots],
        "top_returned": [snapshot_summary(snapshot) for snapshot in returned_snapshots[:3]],
        "diagnosis": diagnosis_text(categories),
        "recommended_actions": recommended_actions_for(categories),
    }


def has_query_term_gap(query: str, question: dict[str, Any]) -> bool:
    query_tokens = token_set(query)
    primary_targets = [
        target for target in (question.get("gold_targets") or []) if target.get("role") == "primary"
    ]
    required_terms = [
        str(term) for target in primary_targets for term in (target.get("required_terms") or [])
    ]
    if not required_terms:
        return False
    missing = [term for term in required_terms if not token_set(term).intersection(query_tokens)]
    return len(missing) >= max(1, len(required_terms) // 2)


def candidate_competes(query: str, primary: EvidenceSnapshot, top: EvidenceSnapshot) -> bool:
    query_tokens = token_set(query)
    primary_overlap = len(
        token_set(primary.text + " " + primary.summary).intersection(query_tokens)
    )
    top_overlap = len(token_set(top.text + " " + top.summary).intersection(query_tokens))
    return top.evidence_id != primary.evidence_id and top_overlap >= primary_overlap


def section_granularity_issue(
    question: dict[str, Any],
    primary: EvidenceSnapshot,
    returned: list[EvidenceSnapshot],
) -> bool:
    target_sections = {
        str(target.get("section_title") or "").casefold()
        for target in (question.get("gold_targets") or [])
        if target.get("role") == "primary"
    }
    if not target_sections:
        return False
    same_paper = [snapshot for snapshot in returned if snapshot.paper_id == primary.paper_id]
    return bool(same_paper) and primary.section_title.casefold() not in {
        snapshot.section_title.casefold() for snapshot in same_paper
    }


def diagnosis_text(categories: list[str]) -> str:
    ordered = sorted(set(categories))
    if "paper_recall_miss" in ordered:
        return "The primary paper did not enter the top evidence set, so this is a corpus-level recall miss."
    if "same_paper_wrong_evidence" in ordered:
        return "The right paper appears in candidates, but ranking/compression selected the wrong evidence span."
    if "supporting_over_primary" in ordered:
        return "A supporting gold item was retrieved while the primary gold was missed, suggesting role confusion."
    return "The miss needs manual inspection after automatic taxonomy."


def recommended_actions_for(categories: list[str]) -> list[str]:
    actions = []
    category_set = set(categories)
    if "paper_recall_miss" in category_set:
        actions.append(
            "Add profile-aware query variants that include method, dataset, benchmark, and paper-alias clues without leaking labels into evaluation."
        )
    if (
        "same_paper_wrong_evidence" in category_set
        or "section_evidence_granularity" in category_set
    ):
        actions.append(
            "Increase section-level parent context and add section-title features to rerank diagnostics."
        )
    if "supporting_over_primary" in category_set:
        actions.append(
            "Record primary/supporting role confusion in replay and evaluate role-aware rerank features."
        )
    if "query_term_gap" in category_set:
        actions.append(
            "Use query rewrite variants that expand implicit terms such as benchmark, retrieval, hierarchy, reasoning, or taxonomy."
        )
    if "candidate_competition" in category_set:
        actions.append(
            "Add diversity-aware post-processing so one high-overlap family does not crowd out primary evidence."
        )
    return actions or ["Manually inspect this miss and add a targeted replay case."]


def recommended_next_actions(category_counts: Counter[str]) -> list[str]:
    actions = []
    if category_counts.get("paper_recall_miss", 0):
        actions.append(
            "Prioritize query rewrite and candidate-pool recall before changing answer generation."
        )
    if category_counts.get("same_paper_wrong_evidence", 0):
        actions.append(
            "Prioritize section-aware rerank features and compressed-evidence validation."
        )
    if category_counts.get("supporting_over_primary", 0):
        actions.append("Track primary/supporting role confusion as a separate replay metric.")
    if category_counts.get("query_term_gap", 0):
        actions.append("Review hard-question wording and add non-leaky query-intent expansion.")
    return actions or ["No dominant miss category found; expand manual review."]


def collect_evidence_ids(
    questions: dict[str, dict[str, Any]],
    failures: list[dict[str, Any]],
) -> set[str]:
    ids = set()
    for question in questions.values():
        ids.update(question.get("gold_evidence_ids") or [])
    for failure in failures:
        expected = failure.get("expected") or {}
        observed = failure.get("observed") or {}
        ids.update(expected.get("gold_evidence_ids") or [])
        ids.update(expected.get("primary_gold_evidence_ids") or [])
        ids.update(observed.get("returned_evidence_ids") or [])
    return ids


def load_evidence_snapshots(ids: set[str]) -> dict[str, EvidenceSnapshot]:
    if not ids:
        return {}
    with SessionLocal() as session:
        evidences = session.query(Evidence).filter(Evidence.id.in_(sorted(ids))).all()
        papers = {
            paper.id: paper
            for paper in session.query(Paper)
            .filter(Paper.id.in_({evidence.paper_id for evidence in evidences}))
            .all()
        }
        sections = {
            section.id: section
            for section in session.query(PaperSection)
            .filter(
                PaperSection.id.in_(
                    {evidence.section_id for evidence in evidences if evidence.section_id}
                )
            )
            .all()
        }
    snapshots = {}
    for evidence in evidences:
        paper = papers.get(evidence.paper_id)
        section = sections.get(evidence.section_id or "")
        snapshots[evidence.id] = EvidenceSnapshot(
            evidence_id=evidence.id,
            paper_id=evidence.paper_id,
            paper_title=paper.title if paper else "",
            evidence_type=evidence.evidence_type,
            section_title=section.title if section else "",
            text=evidence.text or "",
            summary=evidence.summary or "",
        )
    return snapshots


def snapshot_summary(snapshot: EvidenceSnapshot) -> dict[str, Any]:
    return {
        "evidence_id": snapshot.evidence_id,
        "paper_id": snapshot.paper_id,
        "paper_title": snapshot.paper_title,
        "evidence_type": snapshot.evidence_type,
        "section_title": snapshot.section_title,
        "excerpt": compact_text(snapshot.text or snapshot.summary, 240),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Geoloc Retrieval Miss Analysis",
        "",
        f"- Status: `{report['status']}`",
        f"- Misses analyzed: `{report['summary']['miss_count']}`",
        f"- Category counts: `{json.dumps(report['summary']['category_counts'], ensure_ascii=False, sort_keys=True)}`",
        "",
        "## Recommended Next Actions",
        "",
    ]
    for action in report["summary"].get("recommended_next_actions") or []:
        lines.append(f"- {action}")
    lines.extend(["", "## Misses", ""])
    for miss in report.get("misses") or []:
        lines.extend(
            [
                f"### {miss['id']} - {miss['intent']}",
                "",
                f"- Categories: `{', '.join(miss['categories'])}`",
                f"- Diagnosis: {miss['diagnosis']}",
                f"- Query: {miss['query']}",
                "- Recommended actions:",
            ]
        )
        for action in miss.get("recommended_actions") or []:
            lines.append(f"  - {action}")
        lines.append("- Primary gold:")
        for item in miss.get("primary_gold") or []:
            lines.append(
                f"  - `{item['evidence_id']}` {item['paper_title']} / {item['section_title']}: {item['excerpt']}"
            )
        lines.append("- Top returned:")
        for item in miss.get("top_returned") or []:
            lines.append(
                f"  - `{item['evidence_id']}` {item['paper_title']} / {item['section_title']}: {item['excerpt']}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def token_set(value: str) -> set[str]:
    return {
        token.casefold()
        for token in TOKEN_RE.findall(value or "")
        if token.casefold() not in STOP_TERMS
    }


def compact_text(value: str, limit: int) -> str:
    text = " ".join((value or "").split())
    return text if len(text) <= limit else text[: limit - 14].rstrip() + "...[truncated]"


def resolve_project_path(path: Path) -> Path:
    resolved = path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise SystemExit(f"path must stay inside project root: {path}") from exc
    return resolved


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
