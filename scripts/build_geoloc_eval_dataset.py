#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.research.db import SessionLocal  # noqa: E402
from backend.research.models import Evidence, Paper, PaperSection  # noqa: E402

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "evaluation" / "geoloc_12paper"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "outputs" / "evaluations"
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]{2,}")
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|Bearer\s+[A-Za-z0-9._\-]{8,})")
STOPWORDS = {
    "about",
    "across",
    "against",
    "also",
    "analysis",
    "approach",
    "based",
    "between",
    "could",
    "dataset",
    "datasets",
    "during",
    "evidence",
    "from",
    "image",
    "images",
    "method",
    "model",
    "paper",
    "result",
    "results",
    "should",
    "study",
    "system",
    "that",
    "their",
    "this",
    "through",
    "using",
    "with",
    "without",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a local query-evidence and replay-case dataset from real geoloc papers."
    )
    parser.add_argument(
        "--report",
        default="",
        help="Real-paper evaluation JSON report. Defaults to latest outputs/evaluations report.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Ignored local output directory for dataset artifacts.",
    )
    parser.add_argument("--dataset-id", default="geoloc_12paper_v1")
    parser.add_argument("--min-query-count", type=int, default=50)
    parser.add_argument("--max-query-count", type=int, default=80)
    parser.add_argument("--replay-count", type=int, default=30)
    parser.add_argument("--json", action="store_true", help="Print manifest JSON.")
    args = parser.parse_args()

    report_path = Path(args.report) if args.report else _latest_report_path()
    if not report_path.exists():
        print(f"Report not found: {report_path}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = json.loads(report_path.read_text(encoding="utf-8"))
    with SessionLocal() as session:
        paper_specs = _load_paper_specs(session, report)
        query_records = _build_query_records(
            session,
            paper_specs,
            dataset_id=args.dataset_id,
            max_query_count=args.max_query_count,
        )

    if len(query_records) < args.min_query_count:
        print(
            f"Only built {len(query_records)} query-evidence records; "
            f"minimum is {args.min_query_count}.",
            file=sys.stderr,
        )
        return 1

    replay_records = _build_replay_records(
        query_records,
        dataset_id=args.dataset_id,
        replay_count=args.replay_count,
    )
    if len(replay_records) != args.replay_count:
        print(
            f"Only built {len(replay_records)} replay records; requested {args.replay_count}.",
            file=sys.stderr,
        )
        return 1

    query_path = output_dir / "query_evidence.jsonl"
    replay_path = output_dir / "replay_cases.jsonl"
    manifest_path = output_dir / "manifest.json"
    markdown_path = output_dir / "README.md"

    _write_jsonl(query_path, query_records)
    _write_jsonl(replay_path, replay_records)
    manifest = _build_manifest(
        dataset_id=args.dataset_id,
        report_path=report_path,
        output_dir=output_dir,
        query_records=query_records,
        replay_records=replay_records,
    )
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_render_markdown(manifest), encoding="utf-8")

    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(_render_console(manifest))
    return 0


def _latest_report_path() -> Path:
    reports = sorted(DEFAULT_REPORT_DIR.glob("real_paper_eval_*.json"))
    if not reports:
        raise FileNotFoundError("No real-paper evaluation reports found.")
    return reports[-1]


def _load_paper_specs(session, report: dict[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for result in report.get("papers") or []:
        if result.get("status") != "completed":
            continue
        paper_payload = result.get("paper") or {}
        paper_id = str(paper_payload.get("id") or result.get("paper_id") or "").strip()
        if not paper_id:
            continue
        paper = session.get(Paper, paper_id)
        if paper is None:
            continue
        filename = str(result.get("filename") or paper.filename or "")
        specs.append(
            {
                "paper_id": paper.id,
                "paper_title": _display_title(paper, filename),
                "db_title": paper.title,
                "filename": filename,
                "year": paper.year,
            }
        )
    return specs


def _display_title(paper: Paper, filename: str) -> str:
    title = (paper.title or "").strip()
    fallback = _title_from_filename(filename)
    if not title:
        return fallback
    lowered = title.lower()
    noisy = [
        "contents lists available",
        "latest updates:",
        "ieee transactions",
        "vol.",
        "http",
        "h\ue03cps",
    ]
    if any(marker in lowered for marker in noisy):
        return fallback
    return title


def _title_from_filename(filename: str) -> str:
    name = Path(filename).stem
    replacements = {
        "Zhou 等 - 2024 - Img2Loc Revisiting Image Geolocalization using Multi-modality Foundation Models and Image-based Ret": "Img2Loc: Revisiting Image Geolocalization using Multi-modality Foundation Models and Image-based Retrieval",
        "Fang 等 - 2026 - GEOMR Integrating image geographic features and human reasoning knowledge for image geolocalization": "GEOMR: Integrating image geographic features and human reasoning knowledge for image geolocalization",
        "Wu 等 - 2024 - CAMP a cross-view geo-localization method using contrastive attributes mining and position-aware pa": "CAMP: Cross-view geo-localization with contrastive attributes mining and position-aware patterns",
    }
    return replacements.get(name, name)


def _build_query_records(
    session,
    paper_specs: list[dict[str, Any]],
    *,
    dataset_id: str,
    max_query_count: int,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    sections = {
        section.id: section
        for section in session.query(PaperSection)
        .filter(PaperSection.paper_id.in_([item["paper_id"] for item in paper_specs]))
        .all()
    }
    for paper_index, paper_spec in enumerate(paper_specs, start=1):
        evidences = (
            session.query(Evidence)
            .filter(Evidence.paper_id == paper_spec["paper_id"])
            .order_by(Evidence.created_at.asc(), Evidence.id.asc())
            .all()
        )
        for evidence_index, evidence in enumerate(evidences, start=1):
            text = _evidence_text(evidence)
            if len(text) < 40:
                continue
            keywords = _keywords(text)
            if len(keywords) < 3:
                continue
            section = sections.get(evidence.section_id or "")
            record_index = len(records) + 1
            records.append(
                {
                    "id": f"qe_{record_index:04d}",
                    "dataset_id": dataset_id,
                    "paper_id": paper_spec["paper_id"],
                    "paper_title": paper_spec["paper_title"],
                    "paper_filename": paper_spec["filename"],
                    "paper_order": paper_index,
                    "query": _build_query(evidence, keywords, evidence_index),
                    "query_terms": keywords[:8],
                    "gold_evidence_ids": [evidence.id],
                    "gold_chunk_ids": [evidence.chunk_id] if evidence.chunk_id else [],
                    "evidence_type": evidence.evidence_type,
                    "section_title": section.title if section else "",
                    "evidence_summary": _clip(evidence.summary or evidence.supports or text, 220),
                    "evidence_excerpt": _clip(text, 280),
                    "quality": {
                        "evidence_char_count": len(text),
                        "query_term_count": len(keywords[:8]),
                        "has_section": bool(section),
                        "title_source": "filename"
                        if paper_spec["paper_title"] != paper_spec["db_title"]
                        else "db",
                    },
                }
            )
    return _balanced_select(records, max_query_count)


def _evidence_text(evidence: Evidence) -> str:
    return _clean_text(
        " ".join(
            [
                evidence.evidence_type or "",
                evidence.summary or "",
                evidence.supports or "",
                evidence.text or "",
            ]
        )
    )


def _build_query(evidence: Evidence, keywords: list[str], evidence_index: int) -> str:
    topic = " ".join(keywords[:5])
    evidence_type = (evidence.evidence_type or "").replace("_", " ").strip()
    templates = [
        "What evidence does the paper provide about {topic}?",
        "Which part of the paper supports the claim about {topic}?",
        "How does the paper discuss {topic}?",
        "What method or evaluation detail is given for {topic}?",
    ]
    template = templates[evidence_index % len(templates)]
    if evidence_type:
        return f"{template.format(topic=topic)} Focus on {evidence_type} evidence."
    return template.format(topic=topic)


def _keywords(text: str) -> list[str]:
    counts: Counter[str] = Counter()
    first_seen: dict[str, int] = {}
    for index, token in enumerate(TOKEN_RE.findall(text)):
        lowered = token.lower()
        if lowered in STOPWORDS or len(lowered) < 4:
            continue
        if lowered not in first_seen:
            first_seen[lowered] = index
        counts[lowered] += 1
    ranked = sorted(counts, key=lambda item: (-counts[item], first_seen[item], item))
    return ranked[:12]


def _balanced_select(records: list[dict[str, Any]], max_count: int) -> list[dict[str, Any]]:
    if len(records) <= max_count:
        return records
    by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_paper[record["paper_id"]].append(record)
    selected: list[dict[str, Any]] = []
    while len(selected) < max_count:
        progressed = False
        for paper_id in sorted(by_paper):
            if by_paper[paper_id] and len(selected) < max_count:
                selected.append(by_paper[paper_id].pop(0))
                progressed = True
        if not progressed:
            break
    for index, record in enumerate(selected, start=1):
        record["id"] = f"qe_{index:04d}"
    return selected


def _build_replay_records(
    query_records: list[dict[str, Any]],
    *,
    dataset_id: str,
    replay_count: int,
) -> list[dict[str, Any]]:
    selected = _balanced_select([dict(item) for item in query_records], replay_count)
    citation_count = min(max(1, round(replay_count * 0.27)), len(selected) // 2)
    context_count = replay_count - citation_count
    context_items = selected[:context_count]
    citation_items = selected[context_count : context_count + citation_count]
    records: list[dict[str, Any]] = []
    for item in context_items:
        records.append(_context_replay_record(item, dataset_id, len(records) + 1))
    for item in citation_items:
        records.append(_citation_replay_record(item, dataset_id, len(records) + 1))
    return records


def _context_replay_record(item: dict[str, Any], dataset_id: str, index: int) -> dict[str, Any]:
    expected = {
        "query": item["query"],
        "paper_ids": [item["paper_id"]],
        "required_evidence_ids": item["gold_evidence_ids"],
        "min_evidence_count": 1,
        "live_status": "completed",
        "limit": 8,
        "include_graph": False,
    }
    return {
        "id": f"replay_{index:04d}",
        "case_type": "context_search",
        "query": item["query"],
        "expected": expected,
        "observed": {
            "dataset_id": dataset_id,
            "query_evidence_id": item["id"],
            "gold_evidence_ids": item["gold_evidence_ids"],
        },
        "verdict": "needs_review",
        "notes": "Generated local retrieval replay case from the 12-paper evaluation set.",
        "metadata": {
            "dataset_id": dataset_id,
            "query_evidence_id": item["id"],
            "paper_id": item["paper_id"],
            "paper_title": item["paper_title"],
        },
    }


def _citation_replay_record(item: dict[str, Any], dataset_id: str, index: int) -> dict[str, Any]:
    terms = item["query_terms"][:3]
    expected = {
        "paper_ids": [item["paper_id"]],
        "cited_evidence_ids": item["gold_evidence_ids"],
        "required_cited_evidence_ids": item["gold_evidence_ids"],
        "required_citation_terms": terms,
        "min_citation_count": 1,
        "max_missing_citation_count": 0,
        "max_wrong_paper_citation_count": 0,
        "max_citation_term_miss_count": 0,
        "live_status": "completed",
    }
    return {
        "id": f"replay_{index:04d}",
        "case_type": "citation_audit",
        "query": item["query"],
        "expected": expected,
        "observed": {"cited_evidence_ids": item["gold_evidence_ids"]},
        "verdict": "needs_review",
        "notes": "Generated local citation-audit replay case from the 12-paper evaluation set.",
        "metadata": {
            "dataset_id": dataset_id,
            "query_evidence_id": item["id"],
            "paper_id": item["paper_id"],
            "paper_title": item["paper_title"],
        },
    }


def _build_manifest(
    *,
    dataset_id: str,
    report_path: Path,
    output_dir: Path,
    query_records: list[dict[str, Any]],
    replay_records: list[dict[str, Any]],
) -> dict[str, Any]:
    by_paper = Counter(item["paper_title"] for item in query_records)
    replay_types = Counter(item["case_type"] for item in replay_records)
    return {
        "dataset_id": dataset_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "source_report": str(report_path),
        "output_dir": str(output_dir),
        "query_evidence_path": str(output_dir / "query_evidence.jsonl"),
        "replay_cases_path": str(output_dir / "replay_cases.jsonl"),
        "query_count": len(query_records),
        "replay_case_count": len(replay_records),
        "paper_count": len(by_paper),
        "queries_by_paper": dict(sorted(by_paper.items())),
        "replay_case_types": dict(sorted(replay_types.items())),
        "quality_policy": {
            "query_target": "50-80",
            "replay_case_target": "20-30",
            "raw_paper_text_committed": False,
            "local_artifact_only": True,
        },
    }


def _render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        f"# {manifest['dataset_id']}",
        "",
        f"- Query-evidence pairs: `{manifest['query_count']}`",
        f"- Replay cases: `{manifest['replay_case_count']}`",
        f"- Papers: `{manifest['paper_count']}`",
        f"- Source report: `{manifest['source_report']}`",
        "",
        "## Replay Case Types",
        "",
    ]
    for case_type, count in manifest["replay_case_types"].items():
        lines.append(f"- `{case_type}`: {count}")
    lines.extend(["", "## Queries By Paper", ""])
    for title, count in manifest["queries_by_paper"].items():
        lines.append(f"- {title}: {count}")
    lines.extend(
        [
            "",
            "## Quality Boundary",
            "",
            "This directory is ignored local data. Do not commit generated query/evidence rows, replay cases, or quality reports unless they have been explicitly sanitized.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_console(manifest: dict[str, Any]) -> str:
    return (
        f"Built {manifest['dataset_id']}: {manifest['query_count']} query-evidence pairs, "
        f"{manifest['replay_case_count']} replay cases, {manifest['paper_count']} papers."
    )


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records
        ),
        encoding="utf-8",
    )


def _clean_text(value: str) -> str:
    return SECRET_RE.sub("[redacted]", re.sub(r"\s+", " ", value or "")).strip()


def _clip(value: str, limit: int) -> str:
    value = _clean_text(value)
    if len(value) <= limit:
        return value
    return value[: limit - 15].rstrip() + "...[truncated]"


if __name__ == "__main__":
    raise SystemExit(main())
