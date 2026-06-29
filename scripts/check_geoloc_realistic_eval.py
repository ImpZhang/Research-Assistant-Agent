#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import statistics
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.research.db import SessionLocal  # noqa: E402
from backend.research.models import Evidence, Paper  # noqa: E402
from backend.research.services.embedding_service import EmbeddingService  # noqa: E402
from backend.research.services.retrieval_service import RetrievalService  # noqa: E402

DEFAULT_DATASET_DIR = PROJECT_ROOT / "data" / "evaluation" / "geoloc_12paper"
TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-]{1,}")
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|Bearer\s+[A-Za-z0-9._\-]{8,})")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run realistic no-per-query-filter metrics for reviewer-labeled geoloc gold evidence."
    )
    parser.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR))
    parser.add_argument("--min-questions", type=int, default=20)
    parser.add_argument("--min-paper-coverage", type=int, default=10)
    parser.add_argument("--min-primary-hit-at-8", type=float, default=0.5)
    parser.add_argument("--min-mrr-primary", type=float, default=0.2)
    parser.add_argument("--min-replay-pass-rate", type=float, default=0.5)
    parser.add_argument("--write-json", default="")
    parser.add_argument("--write-markdown", default="")
    parser.add_argument("--write-failure-replay", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    questions = _read_jsonl(dataset_dir / "realistic_gold_questions.jsonl")
    replay_cases = _read_jsonl(dataset_dir / "realistic_replay_cases.jsonl")

    with SessionLocal() as session:
        report, failure_replay_cases = _validate_and_run(
            session,
            questions,
            replay_cases,
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
    if args.write_failure_replay:
        Path(args.write_failure_replay).parent.mkdir(parents=True, exist_ok=True)
        _write_jsonl(Path(args.write_failure_replay), failure_replay_cases)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(_render_console(report))
    return 0 if report["status"] == "pass" else 1


def _validate_and_run(
    session,
    questions: list[dict[str, Any]],
    replay_cases: list[dict[str, Any]],
    *,
    args: argparse.Namespace,
    dataset_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, Any] = {}

    _validate_counts(questions, replay_cases, args, errors)
    _validate_uniqueness(questions, replay_cases, errors)
    evidence_by_id = _load_evidence(session, questions, replay_cases)
    paper_by_id = _load_papers(session, questions)
    _validate_questions(questions, evidence_by_id, paper_by_id, errors, warnings)
    _validate_replay_cases(replay_cases, questions, evidence_by_id, errors)

    failure_replay_cases: list[dict[str, Any]] = []
    if not errors:
        retrieval_metrics, failure_replay_cases = _run_retrieval_checks(session, questions)
        replay_metrics = _run_replay_checks(session, replay_cases)
        metrics["retrieval"] = retrieval_metrics
        metrics["replay"] = replay_metrics
        if retrieval_metrics["primary_hit_at_8"] < args.min_primary_hit_at_8:
            errors.append(
                f"primary hit@8 {retrieval_metrics['primary_hit_at_8']:.4f} "
                f"is below {args.min_primary_hit_at_8:.4f}"
            )
        if retrieval_metrics["mrr_primary"] < args.min_mrr_primary:
            errors.append(
                f"primary MRR {retrieval_metrics['mrr_primary']:.4f} "
                f"is below {args.min_mrr_primary:.4f}"
            )
        if replay_metrics["pass_rate"] < args.min_replay_pass_rate:
            errors.append(
                f"realistic replay pass rate {replay_metrics['pass_rate']:.4f} "
                f"is below {args.min_replay_pass_rate:.4f}"
            )

    paper_ids = {
        str(target.get("paper_id") or "")
        for item in questions
        for target in item.get("gold_targets") or []
    }
    intent_counts = Counter(str(item.get("intent") or "") for item in questions)
    role_counts = Counter(
        str(target.get("role") or "")
        for item in questions
        for target in item.get("gold_targets") or []
    )
    metrics.update(
        {
            "question_count": len(questions),
            "replay_case_count": len(replay_cases),
            "gold_paper_count": len(paper_ids),
            "intent_count": len(intent_counts),
            "intent_counts": dict(sorted(intent_counts.items())),
            "gold_role_counts": dict(sorted(role_counts.items())),
        }
    )
    if len(paper_ids) < args.min_paper_coverage:
        errors.append(f"gold paper coverage {len(paper_ids)} is below {args.min_paper_coverage}")

    return (
        {
            "status": "fail" if errors else "pass",
            "checked_at": datetime.now(UTC).isoformat(),
            "dataset_dir": str(dataset_dir),
            "evaluation_mode": "realistic_no_per_query_paper_filter",
            "errors": errors,
            "warnings": warnings,
            "metrics": metrics,
        },
        failure_replay_cases,
    )


def _validate_counts(
    questions: list[dict[str, Any]],
    replay_cases: list[dict[str, Any]],
    args: argparse.Namespace,
    errors: list[str],
) -> None:
    if len(questions) < args.min_questions:
        errors.append(f"question count {len(questions)} is below {args.min_questions}")
    if len(replay_cases) != len(questions):
        errors.append(f"replay count {len(replay_cases)} does not match questions {len(questions)}")


def _validate_uniqueness(
    questions: list[dict[str, Any]],
    replay_cases: list[dict[str, Any]],
    errors: list[str],
) -> None:
    for label, records in [("realistic question", questions), ("realistic replay", replay_cases)]:
        ids = [str(item.get("id") or "") for item in records]
        duplicates = [item for item, count in Counter(ids).items() if count > 1]
        if duplicates:
            errors.append(f"duplicate {label} ids: {duplicates[:5]}")


def _load_evidence(
    session,
    questions: list[dict[str, Any]],
    replay_cases: list[dict[str, Any]],
) -> dict[str, Evidence]:
    ids: set[str] = set()
    for record in questions:
        ids.update(str(item) for item in record.get("gold_evidence_ids") or [])
        ids.update(str(item) for item in record.get("primary_gold_evidence_ids") or [])
    for record in replay_cases:
        expected = record.get("expected") or {}
        ids.update(str(item) for item in expected.get("gold_evidence_ids") or [])
        ids.update(str(item) for item in expected.get("primary_gold_evidence_ids") or [])
    if not ids:
        return {}
    return {row.id: row for row in session.query(Evidence).filter(Evidence.id.in_(ids)).all()}


def _load_papers(session, questions: list[dict[str, Any]]) -> dict[str, Paper]:
    ids = {
        str(target.get("paper_id") or "")
        for item in questions
        for target in item.get("gold_targets") or []
    }
    corpus_ids = {str(pid) for item in questions for pid in item.get("corpus_paper_ids") or []}
    ids.update(corpus_ids)
    if not ids:
        return {}
    return {row.id: row for row in session.query(Paper).filter(Paper.id.in_(ids)).all()}


def _validate_questions(
    questions: list[dict[str, Any]],
    evidence_by_id: dict[str, Evidence],
    paper_by_id: dict[str, Paper],
    errors: list[str],
    warnings: list[str],
) -> None:
    for record in questions:
        record_id = str(record.get("id") or "")
        if _has_secret(record):
            errors.append(f"{record_id} contains secret-like content")
        if record.get("evaluation_mode") != "realistic_no_per_query_paper_filter":
            errors.append(f"{record_id} has wrong evaluation_mode")
        query = str(record.get("query") or "")
        if len(_tokens(query)) < 8:
            errors.append(f"{record_id} query has fewer than 8 searchable tokens")
        leaked = [
            str(term)
            for term in record.get("blind_leak_terms") or []
            if _contains_phrase(query, str(term))
        ]
        if leaked:
            errors.append(f"{record_id} query leaks target terms: {leaked}")
        corpus_ids = [str(item) for item in record.get("corpus_paper_ids") or []]
        if not corpus_ids:
            errors.append(f"{record_id} has no corpus scope")
        for paper_id in corpus_ids:
            if paper_id not in paper_by_id:
                errors.append(f"{record_id} corpus references missing paper {paper_id}")
        primary_ids = [str(item) for item in record.get("primary_gold_evidence_ids") or []]
        if not primary_ids:
            errors.append(f"{record_id} has no primary gold evidence")
        for evidence_id in record.get("gold_evidence_ids") or []:
            evidence = evidence_by_id.get(str(evidence_id))
            if evidence is None:
                errors.append(f"{record_id} references missing evidence {evidence_id}")
                continue
            if corpus_ids and evidence.paper_id not in corpus_ids:
                errors.append(f"{record_id} evidence {evidence_id} is outside corpus scope")
        for target in record.get("gold_targets") or []:
            if not str(target.get("label_rationale") or "").strip():
                errors.append(f"{record_id} gold target has no rationale")
            if target.get("role") not in {"primary", "supporting"}:
                errors.append(f"{record_id} gold target has unsupported role {target.get('role')}")
            if target.get("evidence_type") == "citation":
                warnings.append(f"{record_id} uses citation evidence as gold")


def _validate_replay_cases(
    replay_cases: list[dict[str, Any]],
    questions: list[dict[str, Any]],
    evidence_by_id: dict[str, Evidence],
    errors: list[str],
) -> None:
    by_id = {str(item.get("id") or ""): item for item in questions}
    for record in replay_cases:
        record_id = str(record.get("id") or "")
        if record.get("case_type") != "context_search_realistic":
            errors.append(f"{record_id} has unsupported case_type {record.get('case_type')}")
        expected = record.get("expected") or {}
        if expected.get("per_query_paper_filter") is not False:
            errors.append(f"{record_id} does not disable per-query paper filtering")
        metadata = record.get("metadata") or {}
        question_id = str(metadata.get("realistic_gold_id") or "")
        question = by_id.get(question_id)
        if question is None:
            errors.append(f"{record_id} does not link to a realistic gold question")
            continue
        if [str(item) for item in expected.get("primary_gold_evidence_ids") or []] != [
            str(item) for item in question.get("primary_gold_evidence_ids") or []
        ]:
            errors.append(f"{record_id} primary evidence does not match question")
        for evidence_id in expected.get("gold_evidence_ids") or []:
            if str(evidence_id) not in evidence_by_id:
                errors.append(f"{record_id} references missing evidence {evidence_id}")


def _run_retrieval_checks(
    session,
    questions: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    service = RetrievalService(
        session,
        embedding_service=EmbeddingService(session, embedding_provider_mode="local"),
        rerank_provider_mode="disabled",
    )
    total = len(questions)
    primary_hits = {1: 0, 3: 0, 5: 0, 8: 0}
    any_hits = {1: 0, 3: 0, 5: 0, 8: 0}
    all_gold_at_8 = 0
    reciprocal_ranks: list[float] = []
    first_primary_ranks: list[int] = []
    misses: list[dict[str, Any]] = []
    partials: list[dict[str, Any]] = []
    failure_replay_cases: list[dict[str, Any]] = []

    for record in questions:
        returned = _search_returned_evidence_ids(service, record)
        primary = {str(item) for item in record.get("primary_gold_evidence_ids") or []}
        gold = {str(item) for item in record.get("gold_evidence_ids") or []}
        first_primary_rank = _first_rank(returned, primary)
        if first_primary_rank:
            reciprocal_ranks.append(1 / first_primary_rank)
            first_primary_ranks.append(first_primary_rank)
        else:
            reciprocal_ranks.append(0.0)
        for k in primary_hits:
            top_k = set(returned[:k])
            primary_hits[k] += int(bool(primary.intersection(top_k)))
            any_hits[k] += int(bool(gold.intersection(top_k)))
        returned_top8 = set(returned[:8])
        if gold.issubset(returned_top8):
            all_gold_at_8 += 1
        elif primary.intersection(returned_top8):
            partials.append(_miss_record(record, primary, gold, returned))
        else:
            miss = _miss_record(record, primary, gold, returned)
            misses.append(miss)
            failure_replay_cases.append(_failure_replay_record(record, miss))

    return (
        {
            "question_count": total,
            "per_query_paper_filter": False,
            "corpus_filter": "dataset_12paper_corpus",
            "primary_hit_at_1": _ratio(primary_hits[1], total),
            "primary_hit_at_3": _ratio(primary_hits[3], total),
            "primary_hit_at_5": _ratio(primary_hits[5], total),
            "primary_hit_at_8": _ratio(primary_hits[8], total),
            "any_gold_hit_at_1": _ratio(any_hits[1], total),
            "any_gold_hit_at_3": _ratio(any_hits[3], total),
            "any_gold_hit_at_5": _ratio(any_hits[5], total),
            "any_gold_hit_at_8": _ratio(any_hits[8], total),
            "all_gold_hit_at_8": _ratio(all_gold_at_8, total),
            "mrr_primary": round(sum(reciprocal_ranks) / total, 4) if total else 0.0,
            "mean_first_primary_rank": round(statistics.mean(first_primary_ranks), 4)
            if first_primary_ranks
            else None,
            "miss_count": len(misses),
            "partial_count": len(partials),
            "misses": misses[:20],
            "partials": partials[:20],
        },
        failure_replay_cases,
    )


def _run_replay_checks(session, replay_cases: list[dict[str, Any]]) -> dict[str, Any]:
    service = RetrievalService(
        session,
        embedding_service=EmbeddingService(session, embedding_provider_mode="local"),
        rerank_provider_mode="disabled",
    )
    passed = 0
    details: list[dict[str, Any]] = []
    for record in replay_cases:
        expected = record.get("expected") or {}
        synthetic_record = {
            "query": expected.get("query") or record.get("query"),
            "corpus_paper_ids": expected.get("corpus_paper_ids") or [],
        }
        returned = _search_returned_evidence_ids(service, synthetic_record)
        primary = {str(item) for item in expected.get("primary_gold_evidence_ids") or []}
        first_rank = _first_rank(returned, primary)
        ok = bool(first_rank and first_rank <= int(expected.get("limit") or 8))
        passed += int(ok)
        details.append(
            {
                "id": record["id"],
                "pass": ok,
                "first_primary_rank": first_rank,
                "reason": "primary gold returned"
                if ok
                else f"missing primary gold {sorted(primary - set(returned[:8]))}",
            }
        )
    total = len(replay_cases)
    return {
        "case_count": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": _ratio(passed, total),
        "failures": [item for item in details if not item["pass"]][:20],
    }


def _search_returned_evidence_ids(service: RetrievalService, record: dict[str, Any]) -> list[str]:
    result = service.search_context(
        query=str(record.get("query") or ""),
        paper_ids=[str(item) for item in record.get("corpus_paper_ids") or []],
        limit=8,
        include_graph=False,
    )
    return [item.item.id for item in result.evidences]


def _first_rank(returned: list[str], wanted: set[str]) -> int | None:
    for index, evidence_id in enumerate(returned, start=1):
        if evidence_id in wanted:
            return index
    return None


def _miss_record(
    record: dict[str, Any],
    primary: set[str],
    gold: set[str],
    returned: list[str],
) -> dict[str, Any]:
    return {
        "id": record.get("id"),
        "intent": record.get("intent"),
        "primary_gold_evidence_ids": sorted(primary),
        "gold_evidence_ids": sorted(gold),
        "returned_evidence_ids": returned[:8],
    }


def _failure_replay_record(record: dict[str, Any], miss: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"realistic_failure_{record['id']}",
        "case_type": "context_search_realistic_primary_miss",
        "query": record["query"],
        "expected": {
            "query": record["query"],
            "corpus_paper_ids": record.get("corpus_paper_ids") or [],
            "per_query_paper_filter": False,
            "primary_gold_evidence_ids": record.get("primary_gold_evidence_ids") or [],
            "gold_evidence_ids": record.get("gold_evidence_ids") or [],
            "limit": 8,
        },
        "observed": miss,
        "verdict": "failed",
        "notes": "Primary gold evidence was not retrieved in the realistic no-per-query-filter evaluation.",
        "metadata": {
            "realistic_gold_id": record["id"],
            "intent": record.get("intent"),
            "evaluation_mode": record.get("evaluation_mode"),
        },
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"JSONL file not found: {path}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
    return records


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records
        ),
        encoding="utf-8",
    )


def _tokens(value: str) -> list[str]:
    return [token.lower().strip("-") for token in TOKEN_RE.findall(value or "") if token.strip("-")]


def _normalize(value: str) -> str:
    return " ".join(_tokens(value))


def _contains_phrase(value: str, phrase: str) -> bool:
    return _normalize(phrase) in _normalize(value)


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


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
        f"Geoloc realistic eval check: {report['status']}",
        f"questions={metrics.get('question_count', 0)}",
        f"papers={metrics.get('gold_paper_count', 0)}",
    ]
    if retrieval:
        parts.append(f"primary_hit@8={retrieval.get('primary_hit_at_8', 0.0):.4f}")
        parts.append(f"mrr={retrieval.get('mrr_primary', 0.0):.4f}")
        parts.append(f"misses={retrieval.get('miss_count', 0)}")
    if replay:
        parts.append(f"replay_pass={replay.get('pass_rate', 0.0):.4f}")
    if report["errors"]:
        parts.append(f"errors={len(report['errors'])}")
    if report["warnings"]:
        parts.append(f"warnings={len(report['warnings'])}")
    return " ".join(parts)


def _render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    retrieval = metrics.get("retrieval") or {}
    replay = metrics.get("replay") or {}
    lines = [
        "# Geoloc Realistic Gold Evaluation Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Evaluation mode: `{report['evaluation_mode']}`",
        f"- Questions: `{metrics.get('question_count', 0)}`",
        f"- Gold-labeled papers: `{metrics.get('gold_paper_count', 0)}`",
    ]
    if retrieval:
        lines.extend(
            [
                f"- Primary hit@1: `{retrieval.get('primary_hit_at_1', 0.0)}`",
                f"- Primary hit@3: `{retrieval.get('primary_hit_at_3', 0.0)}`",
                f"- Primary hit@5: `{retrieval.get('primary_hit_at_5', 0.0)}`",
                f"- Primary hit@8: `{retrieval.get('primary_hit_at_8', 0.0)}`",
                f"- Any-gold hit@8: `{retrieval.get('any_gold_hit_at_8', 0.0)}`",
                f"- All-gold hit@8: `{retrieval.get('all_gold_hit_at_8', 0.0)}`",
                f"- Primary MRR: `{retrieval.get('mrr_primary', 0.0)}`",
                f"- Misses: `{retrieval.get('miss_count', 0)}`",
                f"- Partials: `{retrieval.get('partial_count', 0)}`",
            ]
        )
    if replay:
        lines.append(f"- Replay pass rate: `{replay.get('pass_rate', 0.0)}`")
    lines.extend(["", "## Errors", ""])
    lines.extend([f"- {item}" for item in report["errors"]] or ["- None"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {item}" for item in report["warnings"]] or ["- None"])
    lines.extend(["", "## Misses", ""])
    misses = retrieval.get("misses") or []
    lines.extend([f"- `{item['id']}` intent=`{item['intent']}`" for item in misses] or ["- None"])
    lines.extend(["", "## Partial Gold Hits", ""])
    partials = retrieval.get("partials") or []
    lines.extend([f"- `{item['id']}` intent=`{item['intent']}`" for item in partials] or ["- None"])
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
