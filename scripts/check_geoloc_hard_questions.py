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
from backend.research.models import Evidence  # noqa: E402
from backend.research.services.embedding_service import EmbeddingService  # noqa: E402
from backend.research.services.retrieval_service import RetrievalService  # noqa: E402

DEFAULT_DATASET_DIR = PROJECT_ROOT / "data" / "evaluation" / "geoloc_12paper"
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]{2,}")
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|Bearer\s+[A-Za-z0-9._\-]{8,})")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate human-authored geoloc hard questions and replay cases."
    )
    parser.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR))
    parser.add_argument("--min-hard-questions", type=int, default=20)
    parser.add_argument("--min-paper-coverage", type=int, default=8)
    parser.add_argument("--min-intent-coverage", type=int, default=6)
    parser.add_argument("--run-retrieval", action="store_true")
    parser.add_argument("--min-any-hit-at-8", type=float, default=0.85)
    parser.add_argument("--min-all-hit-at-8", type=float, default=0.65)
    parser.add_argument("--min-replay-pass-rate", type=float, default=0.65)
    parser.add_argument("--write-json", default="")
    parser.add_argument("--write-markdown", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    hard_questions = _read_jsonl(dataset_dir / "hard_questions.jsonl")
    replay_cases = _read_jsonl(dataset_dir / "hard_question_replay_cases.jsonl")

    with SessionLocal() as session:
        report = _validate(
            session,
            hard_questions,
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

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(_render_console(report))
    return 0 if report["status"] == "pass" else 1


def _validate(
    session,
    hard_questions: list[dict[str, Any]],
    replay_cases: list[dict[str, Any]],
    *,
    args: argparse.Namespace,
    dataset_dir: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, Any] = {}

    _validate_counts(hard_questions, replay_cases, args, errors)
    _validate_uniqueness(hard_questions, replay_cases, errors)
    evidence_by_id = _load_evidence(session, hard_questions, replay_cases)
    _validate_hard_questions(hard_questions, evidence_by_id, errors, warnings)
    _validate_replay_cases(replay_cases, hard_questions, evidence_by_id, errors)

    if args.run_retrieval and not errors:
        retrieval_metrics = _run_retrieval_checks(session, hard_questions)
        replay_metrics = _run_replay_checks(session, replay_cases)
        metrics["retrieval"] = retrieval_metrics
        metrics["replay"] = replay_metrics
        if retrieval_metrics["any_hit_at_8"] < args.min_any_hit_at_8:
            errors.append(
                f"hard-question any-hit@8 {retrieval_metrics['any_hit_at_8']:.4f} "
                f"is below {args.min_any_hit_at_8:.4f}"
            )
        if retrieval_metrics["all_hit_at_8"] < args.min_all_hit_at_8:
            errors.append(
                f"hard-question all-hit@8 {retrieval_metrics['all_hit_at_8']:.4f} "
                f"is below {args.min_all_hit_at_8:.4f}"
            )
        if replay_metrics["pass_rate"] < args.min_replay_pass_rate:
            errors.append(
                f"hard-question replay pass rate {replay_metrics['pass_rate']:.4f} "
                f"is below {args.min_replay_pass_rate:.4f}"
            )

    paper_ids = {
        str(paper_id) for item in hard_questions for paper_id in item.get("gold_paper_ids") or []
    }
    intent_counts = Counter(str(item.get("intent") or "") for item in hard_questions)
    target_counts = Counter(
        str(target) for item in hard_questions for target in item.get("target_papers") or []
    )
    metrics.update(
        {
            "hard_question_count": len(hard_questions),
            "hard_replay_case_count": len(replay_cases),
            "paper_count": len(paper_ids),
            "intent_count": len(intent_counts),
            "intent_counts": dict(sorted(intent_counts.items())),
            "target_paper_counts": dict(sorted(target_counts.items())),
        }
    )
    if len(paper_ids) < args.min_paper_coverage:
        errors.append(f"paper coverage {len(paper_ids)} is below {args.min_paper_coverage}")
    if len(intent_counts) < args.min_intent_coverage:
        errors.append(f"intent coverage {len(intent_counts)} is below {args.min_intent_coverage}")

    return {
        "status": "fail" if errors else "pass",
        "checked_at": datetime.now(UTC).isoformat(),
        "dataset_dir": str(dataset_dir),
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }


def _validate_counts(
    hard_questions: list[dict[str, Any]],
    replay_cases: list[dict[str, Any]],
    args: argparse.Namespace,
    errors: list[str],
) -> None:
    if len(hard_questions) < args.min_hard_questions:
        errors.append(
            f"hard-question count {len(hard_questions)} is below {args.min_hard_questions}"
        )
    if len(replay_cases) != len(hard_questions):
        errors.append(
            f"hard replay count {len(replay_cases)} does not match "
            f"hard questions {len(hard_questions)}"
        )


def _validate_uniqueness(
    hard_questions: list[dict[str, Any]],
    replay_cases: list[dict[str, Any]],
    errors: list[str],
) -> None:
    for label, records in [("hard question", hard_questions), ("hard replay", replay_cases)]:
        ids = [str(item.get("id") or "") for item in records]
        duplicates = [item for item, count in Counter(ids).items() if count > 1]
        if duplicates:
            errors.append(f"duplicate {label} ids: {duplicates[:5]}")
    questions = [str(item.get("question") or "").strip().lower() for item in hard_questions]
    duplicate_questions = [item for item, count in Counter(questions).items() if count > 1]
    if duplicate_questions:
        errors.append(f"duplicate hard questions: {duplicate_questions[:3]}")


def _load_evidence(
    session,
    hard_questions: list[dict[str, Any]],
    replay_cases: list[dict[str, Any]],
) -> dict[str, Evidence]:
    ids: set[str] = set()
    for record in hard_questions:
        ids.update(str(item) for item in record.get("gold_evidence_ids") or [])
    for record in replay_cases:
        expected = record.get("expected") or {}
        ids.update(str(item) for item in expected.get("required_evidence_ids") or [])
    if not ids:
        return {}
    return {row.id: row for row in session.query(Evidence).filter(Evidence.id.in_(ids)).all()}


def _validate_hard_questions(
    hard_questions: list[dict[str, Any]],
    evidence_by_id: dict[str, Evidence],
    errors: list[str],
    warnings: list[str],
) -> None:
    for record in hard_questions:
        record_id = str(record.get("id") or "")
        if _has_secret(record):
            errors.append(f"{record_id} contains secret-like content")
        question = str(record.get("question") or "")
        if len(TOKEN_RE.findall(question)) < 8:
            errors.append(f"{record_id} question has fewer than 8 searchable tokens")
        if str(record.get("difficulty") or "") != "hard":
            warnings.append(f"{record_id} difficulty is not hard")
        if len(record.get("required_terms") or []) < 2:
            errors.append(f"{record_id} has fewer than two required terms")
        gold_ids = [str(item) for item in record.get("gold_evidence_ids") or []]
        if not gold_ids:
            errors.append(f"{record_id} has no gold evidence")
        paper_ids = [str(item) for item in record.get("gold_paper_ids") or []]
        if len(paper_ids) != len(gold_ids):
            errors.append(f"{record_id} paper/evidence mapping length mismatch")
        for evidence_id in gold_ids:
            evidence = evidence_by_id.get(evidence_id)
            if evidence is None:
                errors.append(f"{record_id} references missing evidence {evidence_id}")
                continue
            if evidence.paper_id not in paper_ids:
                errors.append(f"{record_id} evidence {evidence_id} belongs to another paper")
        if len(record.get("mapped_evidence") or []) != len(gold_ids):
            warnings.append(f"{record_id} mapped_evidence detail count does not match gold ids")


def _validate_replay_cases(
    replay_cases: list[dict[str, Any]],
    hard_questions: list[dict[str, Any]],
    evidence_by_id: dict[str, Evidence],
    errors: list[str],
) -> None:
    hard_by_id = {str(item.get("id") or ""): item for item in hard_questions}
    for record in replay_cases:
        record_id = str(record.get("id") or "")
        if record.get("case_type") != "context_search":
            errors.append(f"{record_id} has unsupported case_type {record.get('case_type')}")
        if _has_secret(record):
            errors.append(f"{record_id} contains secret-like content")
        metadata = record.get("metadata") or {}
        hard_question_id = str(metadata.get("hard_question_id") or "")
        hard_question = hard_by_id.get(hard_question_id)
        if hard_question is None:
            errors.append(f"{record_id} does not link to a hard question")
            continue
        expected = record.get("expected") or {}
        required_ids = [str(item) for item in expected.get("required_evidence_ids") or []]
        if required_ids != [str(item) for item in hard_question.get("gold_evidence_ids") or []]:
            errors.append(f"{record_id} required evidence does not match hard question")
        for evidence_id in required_ids:
            if evidence_id not in evidence_by_id:
                errors.append(f"{record_id} references missing evidence {evidence_id}")


def _run_retrieval_checks(session, hard_questions: list[dict[str, Any]]) -> dict[str, Any]:
    service = RetrievalService(
        session,
        embedding_service=EmbeddingService(session, embedding_provider_mode="local"),
        rerank_provider_mode="disabled",
    )
    total = len(hard_questions)
    any_hit = 0
    all_hit = 0
    partials: list[dict[str, Any]] = []
    misses: list[dict[str, Any]] = []
    for record in hard_questions:
        returned = _search_returned_evidence_ids(service, record)
        gold = {str(item) for item in record.get("gold_evidence_ids") or []}
        returned_top8 = set(returned[:8])
        if gold.intersection(returned_top8):
            any_hit += 1
        else:
            misses.append(_miss_record(record, gold, returned))
        if gold.issubset(returned_top8):
            all_hit += 1
        elif gold.intersection(returned_top8):
            partials.append(_miss_record(record, gold, returned))
    return {
        "hard_question_count": total,
        "any_hit_at_8": round(any_hit / total, 4) if total else 0.0,
        "all_hit_at_8": round(all_hit / total, 4) if total else 0.0,
        "miss_count": len(misses),
        "partial_count": len(partials),
        "misses": misses[:20],
        "partials": partials[:20],
    }


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
        returned = _search_returned_evidence_ids(
            service,
            {
                "query": expected.get("query") or record.get("query"),
                "gold_paper_ids": expected.get("paper_ids") or [],
            },
        )
        required = {str(item) for item in expected.get("required_evidence_ids") or []}
        ok = required.issubset(set(returned[:8]))
        passed += int(ok)
        details.append(
            {
                "id": record["id"],
                "pass": ok,
                "reason": "required evidence returned"
                if ok
                else f"missing required evidence {sorted(required - set(returned[:8]))}",
            }
        )
    total = len(replay_cases)
    return {
        "case_count": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "failures": [item for item in details if not item["pass"]][:20],
    }


def _search_returned_evidence_ids(
    service: RetrievalService,
    record: dict[str, Any],
) -> list[str]:
    result = service.search_context(
        query=str(record.get("query") or record.get("question") or ""),
        paper_ids=[str(item) for item in record.get("gold_paper_ids") or []],
        limit=8,
        include_graph=False,
    )
    return [item.item.id for item in result.evidences]


def _miss_record(record: dict[str, Any], gold: set[str], returned: list[str]) -> dict[str, Any]:
    return {
        "id": record.get("id"),
        "intent": record.get("intent"),
        "target_papers": record.get("target_papers"),
        "gold_evidence_ids": sorted(gold),
        "returned_evidence_ids": returned[:8],
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
        f"Geoloc hard-question check: {report['status']}",
        f"hard_questions={metrics.get('hard_question_count', 0)}",
        f"replay_cases={metrics.get('hard_replay_case_count', 0)}",
        f"papers={metrics.get('paper_count', 0)}",
    ]
    if retrieval:
        parts.append(f"any_hit@8={retrieval.get('any_hit_at_8', 0.0):.4f}")
        parts.append(f"all_hit@8={retrieval.get('all_hit_at_8', 0.0):.4f}")
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
        "# Geoloc Hard-Question Quality Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Hard questions: `{metrics.get('hard_question_count', 0)}`",
        f"- Hard replay cases: `{metrics.get('hard_replay_case_count', 0)}`",
        f"- Papers covered: `{metrics.get('paper_count', 0)}`",
        f"- Intents covered: `{metrics.get('intent_count', 0)}`",
    ]
    retrieval = metrics.get("retrieval") or {}
    if retrieval:
        lines.extend(
            [
                f"- Any hit@8: `{retrieval.get('any_hit_at_8', 0.0)}`",
                f"- All gold hit@8: `{retrieval.get('all_hit_at_8', 0.0)}`",
                f"- Misses: `{retrieval.get('miss_count', 0)}`",
                f"- Partials: `{retrieval.get('partial_count', 0)}`",
            ]
        )
    replay = metrics.get("replay") or {}
    if replay:
        lines.append(f"- Replay pass rate: `{replay.get('pass_rate', 0.0)}`")
    lines.extend(["", "## Errors", ""])
    lines.extend([f"- {item}" for item in report["errors"]] or ["- None"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {item}" for item in report["warnings"]] or ["- None"])
    lines.extend(["", "## Intent Counts", ""])
    for intent, count in (metrics.get("intent_counts") or {}).items():
        lines.append(f"- `{intent}`: {count}")
    lines.extend(["", "## Target Paper Counts", ""])
    for target, count in (metrics.get("target_paper_counts") or {}).items():
        lines.append(f"- {target}: {count}")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
