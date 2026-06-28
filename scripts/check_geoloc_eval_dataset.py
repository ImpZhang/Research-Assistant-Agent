#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.research.db import SessionLocal  # noqa: E402
from backend.research.models import Evidence, Paper  # noqa: E402
from backend.research.services.embedding_service import EmbeddingService  # noqa: E402
from backend.research.services.retrieval_service import RetrievalService  # noqa: E402

DEFAULT_DATASET_DIR = PROJECT_ROOT / "data" / "evaluation" / "geoloc_12paper"
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|Bearer\s+[A-Za-z0-9._\-]{8,})")
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]{2,}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the local geoloc query-evidence and replay dataset."
    )
    parser.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR))
    parser.add_argument("--min-queries", type=int, default=50)
    parser.add_argument("--max-queries", type=int, default=80)
    parser.add_argument("--min-replay-cases", type=int, default=20)
    parser.add_argument("--max-replay-cases", type=int, default=30)
    parser.add_argument("--min-papers", type=int, default=10)
    parser.add_argument("--min-queries-per-paper", type=int, default=2)
    parser.add_argument("--run-retrieval", action="store_true")
    parser.add_argument("--min-hit-at-8", type=float, default=0.85)
    parser.add_argument("--min-replay-pass-rate", type=float, default=0.9)
    parser.add_argument("--write-json", default="")
    parser.add_argument("--write-markdown", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    query_records = _read_jsonl(dataset_dir / "query_evidence.jsonl")
    replay_records = _read_jsonl(dataset_dir / "replay_cases.jsonl")

    with SessionLocal() as session:
        report = _validate(
            session,
            query_records,
            replay_records,
            args=args,
            dataset_dir=dataset_dir,
        )

    if args.write_json:
        Path(args.write_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.write_json).write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.write_markdown:
        Path(args.write_markdown).parent.mkdir(parents=True, exist_ok=True)
        Path(args.write_markdown).write_text(_render_markdown(report), encoding="utf-8")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(_render_console(report))
    return 0 if report["status"] == "pass" else 1


def _validate(
    session,
    query_records: list[dict[str, Any]],
    replay_records: list[dict[str, Any]],
    *,
    args: argparse.Namespace,
    dataset_dir: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, Any] = {}

    _validate_counts(query_records, replay_records, args, errors)
    _validate_uniqueness(query_records, replay_records, errors)
    evidence_by_id = _load_evidence(session, query_records, replay_records)
    paper_by_id = _load_papers(session, query_records)
    _validate_queries(query_records, evidence_by_id, paper_by_id, args, errors, warnings)
    _validate_replay_records(replay_records, query_records, evidence_by_id, errors, warnings)

    if args.run_retrieval and not errors:
        retrieval_metrics = _run_retrieval_checks(session, query_records)
        metrics["retrieval"] = retrieval_metrics
        if retrieval_metrics["hit_at_8"] < args.min_hit_at_8:
            errors.append(
                f"retrieval hit@8 {retrieval_metrics['hit_at_8']:.4f} "
                f"is below {args.min_hit_at_8:.4f}"
            )
        replay_metrics = _run_replay_checks(session, replay_records)
        metrics["replay"] = replay_metrics
        if replay_metrics["pass_rate"] < args.min_replay_pass_rate:
            errors.append(
                f"replay pass rate {replay_metrics['pass_rate']:.4f} "
                f"is below {args.min_replay_pass_rate:.4f}"
            )

    by_paper = Counter(item["paper_title"] for item in query_records)
    metrics.update(
        {
            "query_count": len(query_records),
            "replay_case_count": len(replay_records),
            "paper_count": len(by_paper),
            "queries_by_paper": dict(sorted(by_paper.items())),
            "replay_case_types": dict(Counter(item["case_type"] for item in replay_records)),
        }
    )
    return {
        "status": "fail" if errors else "pass",
        "checked_at": datetime.now(UTC).isoformat(),
        "dataset_dir": str(dataset_dir),
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }


def _validate_counts(
    query_records: list[dict[str, Any]],
    replay_records: list[dict[str, Any]],
    args: argparse.Namespace,
    errors: list[str],
) -> None:
    if not (args.min_queries <= len(query_records) <= args.max_queries):
        errors.append(
            f"query count {len(query_records)} is outside {args.min_queries}-{args.max_queries}"
        )
    if not (args.min_replay_cases <= len(replay_records) <= args.max_replay_cases):
        errors.append(
            f"replay count {len(replay_records)} is outside "
            f"{args.min_replay_cases}-{args.max_replay_cases}"
        )
    paper_count = len({item.get("paper_id") for item in query_records})
    if paper_count < args.min_papers:
        errors.append(f"paper count {paper_count} is below {args.min_papers}")


def _validate_uniqueness(
    query_records: list[dict[str, Any]],
    replay_records: list[dict[str, Any]],
    errors: list[str],
) -> None:
    for label, records in [("query", query_records), ("replay", replay_records)]:
        ids = [str(item.get("id") or "") for item in records]
        duplicates = [item for item, count in Counter(ids).items() if count > 1]
        if duplicates:
            errors.append(f"duplicate {label} ids: {duplicates[:5]}")
    queries = [str(item.get("query") or "").strip().lower() for item in query_records]
    duplicate_queries = [item for item, count in Counter(queries).items() if count > 1]
    if duplicate_queries:
        errors.append(f"duplicate queries: {duplicate_queries[:5]}")


def _load_evidence(
    session,
    query_records: list[dict[str, Any]],
    replay_records: list[dict[str, Any]],
) -> dict[str, Evidence]:
    ids: set[str] = set()
    for record in query_records:
        ids.update(str(item) for item in record.get("gold_evidence_ids") or [])
    for record in replay_records:
        expected = record.get("expected") or {}
        ids.update(str(item) for item in expected.get("required_evidence_ids") or [])
        ids.update(str(item) for item in expected.get("required_cited_evidence_ids") or [])
        ids.update(str(item) for item in expected.get("cited_evidence_ids") or [])
    if not ids:
        return {}
    return {row.id: row for row in session.query(Evidence).filter(Evidence.id.in_(ids)).all()}


def _load_papers(session, query_records: list[dict[str, Any]]) -> dict[str, Paper]:
    ids = {str(item.get("paper_id") or "") for item in query_records if item.get("paper_id")}
    if not ids:
        return {}
    return {row.id: row for row in session.query(Paper).filter(Paper.id.in_(ids)).all()}


def _validate_queries(
    query_records: list[dict[str, Any]],
    evidence_by_id: dict[str, Evidence],
    paper_by_id: dict[str, Paper],
    args: argparse.Namespace,
    errors: list[str],
    warnings: list[str],
) -> None:
    by_paper = Counter(str(item.get("paper_id") or "") for item in query_records)
    for paper_id, count in by_paper.items():
        if count < args.min_queries_per_paper:
            errors.append(f"paper {paper_id} has only {count} queries")

    for record in query_records:
        query = str(record.get("query") or "").strip()
        if len(TOKEN_RE.findall(query)) < 5:
            errors.append(f"{record.get('id')} query has fewer than 5 searchable tokens")
        if _has_secret(record):
            errors.append(f"{record.get('id')} contains secret-like content")
        paper_id = str(record.get("paper_id") or "")
        if paper_id not in paper_by_id:
            errors.append(f"{record.get('id')} references missing paper {paper_id}")
        for evidence_id in record.get("gold_evidence_ids") or []:
            evidence = evidence_by_id.get(str(evidence_id))
            if evidence is None:
                errors.append(f"{record.get('id')} references missing evidence {evidence_id}")
                continue
            if evidence.paper_id != paper_id:
                errors.append(f"{record.get('id')} evidence {evidence_id} belongs to another paper")
            overlap = _term_overlap(query, _evidence_text(evidence))
            if overlap < 2:
                warnings.append(f"{record.get('id')} has low query/evidence term overlap")
        excerpt = str(record.get("evidence_excerpt") or "")
        if len(excerpt) > 320:
            errors.append(f"{record.get('id')} evidence excerpt is too long")


def _validate_replay_records(
    replay_records: list[dict[str, Any]],
    query_records: list[dict[str, Any]],
    evidence_by_id: dict[str, Evidence],
    errors: list[str],
    warnings: list[str],
) -> None:
    query_ids = {str(item.get("id") or "") for item in query_records}
    allowed_types = {"context_search", "citation_audit"}
    for record in replay_records:
        if record.get("case_type") not in allowed_types:
            errors.append(f"{record.get('id')} has unsupported case_type {record.get('case_type')}")
        metadata = record.get("metadata") or {}
        if str(metadata.get("query_evidence_id") or "") not in query_ids:
            errors.append(f"{record.get('id')} does not link to a query-evidence id")
        if _has_secret(record):
            errors.append(f"{record.get('id')} contains secret-like content")
        expected = record.get("expected") or {}
        for evidence_id in list(expected.get("required_evidence_ids") or []) + list(
            expected.get("required_cited_evidence_ids") or []
        ):
            if str(evidence_id) not in evidence_by_id:
                errors.append(f"{record.get('id')} references missing evidence {evidence_id}")
        if record.get("case_type") == "citation_audit":
            terms = [str(item).lower() for item in expected.get("required_citation_terms") or []]
            for evidence_id in expected.get("required_cited_evidence_ids") or []:
                evidence = evidence_by_id.get(str(evidence_id))
                if evidence and any(term not in _evidence_text(evidence).lower() for term in terms):
                    warnings.append(f"{record.get('id')} has citation terms not all in evidence")


def _run_retrieval_checks(session, query_records: list[dict[str, Any]]) -> dict[str, Any]:
    service = RetrievalService(
        session,
        embedding_service=EmbeddingService(session, embedding_provider_mode="local"),
        rerank_provider_mode="disabled",
    )
    total = len(query_records)
    hit_at_1 = 0
    hit_at_3 = 0
    hit_at_8 = 0
    misses: list[dict[str, Any]] = []
    for record in query_records:
        result = service.search_context(
            query=record["query"],
            paper_ids=[record["paper_id"]],
            limit=8,
            include_graph=False,
        )
        returned = [item.item.id for item in result.evidences]
        gold = set(str(item) for item in record.get("gold_evidence_ids") or [])
        if gold.intersection(returned[:1]):
            hit_at_1 += 1
        if gold.intersection(returned[:3]):
            hit_at_3 += 1
        if gold.intersection(returned[:8]):
            hit_at_8 += 1
        else:
            misses.append(
                {
                    "id": record["id"],
                    "paper_title": record["paper_title"],
                    "gold_evidence_ids": sorted(gold),
                    "returned_evidence_ids": returned[:8],
                }
            )
    return {
        "query_count": total,
        "hit_at_1": round(hit_at_1 / total, 4) if total else 0.0,
        "hit_at_3": round(hit_at_3 / total, 4) if total else 0.0,
        "hit_at_8": round(hit_at_8 / total, 4) if total else 0.0,
        "miss_count": len(misses),
        "misses": misses[:20],
    }


def _run_replay_checks(session, replay_records: list[dict[str, Any]]) -> dict[str, Any]:
    passed = 0
    failed = 0
    details: list[dict[str, Any]] = []
    retrieval_service = RetrievalService(
        session,
        embedding_service=EmbeddingService(session, embedding_provider_mode="local"),
        rerank_provider_mode="disabled",
    )
    for record in replay_records:
        if record["case_type"] == "context_search":
            ok, reason = _check_context_replay(retrieval_service, record)
        elif record["case_type"] == "citation_audit":
            ok, reason = _check_citation_replay(session, record)
        else:
            ok, reason = False, "unsupported case type"
        passed += int(ok)
        failed += int(not ok)
        details.append(
            {"id": record["id"], "case_type": record["case_type"], "pass": ok, "reason": reason}
        )
    total = len(replay_records)
    return {
        "case_count": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "failures": [item for item in details if not item["pass"]][:20],
    }


def _check_context_replay(service: RetrievalService, record: dict[str, Any]) -> tuple[bool, str]:
    expected = record.get("expected") or {}
    result = service.search_context(
        query=str(expected.get("query") or record.get("query") or ""),
        paper_ids=[str(item) for item in expected.get("paper_ids") or []],
        limit=int(expected.get("limit") or 8),
        include_graph=bool(expected.get("include_graph", False)),
    )
    returned = {item.item.id for item in result.evidences}
    required = {str(item) for item in expected.get("required_evidence_ids") or []}
    if required.issubset(returned):
        return True, "required evidence returned"
    return False, f"missing required evidence {sorted(required - returned)}"


def _check_citation_replay(session, record: dict[str, Any]) -> tuple[bool, str]:
    expected = record.get("expected") or {}
    required_ids = [str(item) for item in expected.get("required_cited_evidence_ids") or []]
    rows = session.query(Evidence).filter(Evidence.id.in_(required_ids)).all()
    by_id = {row.id: row for row in rows}
    missing = [evidence_id for evidence_id in required_ids if evidence_id not in by_id]
    if missing:
        return False, f"missing citation evidence {missing}"
    paper_ids = {str(item) for item in expected.get("paper_ids") or []}
    wrong_paper = [row.id for row in rows if paper_ids and row.paper_id not in paper_ids]
    if wrong_paper:
        return False, f"wrong paper citations {wrong_paper}"
    terms = [str(item).lower() for item in expected.get("required_citation_terms") or []]
    for row in rows:
        text = _evidence_text(row).lower()
        missing_terms = [term for term in terms if term not in text]
        if missing_terms:
            return False, f"missing citation terms {missing_terms}"
    return True, "citation evidence valid"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        print(f"Dataset file not found: {path}", file=sys.stderr)
        raise SystemExit(1)
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
    return records


def _evidence_text(evidence: Evidence) -> str:
    return " ".join(
        [
            evidence.evidence_type or "",
            evidence.summary or "",
            evidence.supports or "",
            evidence.text or "",
        ]
    )


def _term_overlap(query: str, evidence_text: str) -> int:
    query_terms = {item.lower() for item in TOKEN_RE.findall(query)}
    evidence_terms = {item.lower() for item in TOKEN_RE.findall(evidence_text)}
    return len(query_terms.intersection(evidence_terms))


def _has_secret(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_has_secret(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_secret(item) for item in value)
    if isinstance(value, str):
        return bool(SECRET_RE.search(value))
    return False


def _render_console(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    retrieval = metrics.get("retrieval") or {}
    replay = metrics.get("replay") or {}
    parts = [
        f"Geoloc eval dataset check: {report['status']}",
        f"queries={metrics.get('query_count', 0)}",
        f"replay_cases={metrics.get('replay_case_count', 0)}",
        f"papers={metrics.get('paper_count', 0)}",
    ]
    if retrieval:
        parts.append(f"hit@8={retrieval.get('hit_at_8', 0.0):.4f}")
    if replay:
        parts.append(f"replay_pass={replay.get('pass_rate', 0.0):.4f}")
    if report["errors"]:
        parts.append(f"errors={len(report['errors'])}")
    if report["warnings"]:
        parts.append(f"warnings={len(report['warnings'])}")
    return " ".join(parts)


def _render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Geoloc Evaluation Dataset Quality Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Query-evidence pairs: `{metrics.get('query_count', 0)}`",
        f"- Replay cases: `{metrics.get('replay_case_count', 0)}`",
        f"- Papers: `{metrics.get('paper_count', 0)}`",
    ]
    retrieval = metrics.get("retrieval") or {}
    if retrieval:
        lines.extend(
            [
                f"- Retrieval hit@1: `{retrieval.get('hit_at_1', 0.0)}`",
                f"- Retrieval hit@3: `{retrieval.get('hit_at_3', 0.0)}`",
                f"- Retrieval hit@8: `{retrieval.get('hit_at_8', 0.0)}`",
            ]
        )
    replay = metrics.get("replay") or {}
    if replay:
        lines.append(f"- Replay pass rate: `{replay.get('pass_rate', 0.0)}`")
    lines.extend(["", "## Errors", ""])
    lines.extend([f"- {item}" for item in report["errors"]] or ["- None"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {item}" for item in report["warnings"]] or ["- None"])
    lines.extend(["", "## Queries By Paper", ""])
    for title, count in (metrics.get("queries_by_paper") or {}).items():
        lines.append(f"- {title}: {count}")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
