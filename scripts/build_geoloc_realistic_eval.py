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

DEFAULT_DATASET_DIR = PROJECT_ROOT / "data" / "evaluation" / "geoloc_12paper"
DEFAULT_GOLD_SPEC = PROJECT_ROOT / "configs" / "geoloc_realistic_gold.v1.jsonl"
TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-]{1,}")
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|Bearer\s+[A-Za-z0-9._\-]{8,})")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build realistic no-per-query-filter geoloc gold labels from reviewer specs."
    )
    parser.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR))
    parser.add_argument("--gold-spec", default=str(DEFAULT_GOLD_SPEC))
    parser.add_argument("--dataset-id", default="geoloc_12paper_realistic_gold_v1")
    parser.add_argument("--min-questions", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    spec_path = Path(args.gold_spec)
    query_records = _read_jsonl(dataset_dir / "query_evidence.jsonl")
    gold_specs = _read_jsonl(spec_path)
    paper_index = _build_paper_index(query_records)
    corpus_paper_ids = [item["paper_id"] for item in paper_index]

    errors: list[str] = []
    with SessionLocal() as session:
        evidence_by_paper = _load_evidence_by_paper(session, corpus_paper_ids)
        questions = _build_questions(
            gold_specs,
            paper_index,
            evidence_by_paper,
            dataset_id=args.dataset_id,
            corpus_paper_ids=corpus_paper_ids,
            errors=errors,
        )

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    if len(questions) < args.min_questions:
        print(
            f"Only built {len(questions)} realistic gold questions; "
            f"minimum is {args.min_questions}.",
            file=sys.stderr,
        )
        return 1

    replay_cases = _build_replay_cases(questions, args.dataset_id, corpus_paper_ids)
    questions_path = dataset_dir / "realistic_gold_questions.jsonl"
    replay_path = dataset_dir / "realistic_replay_cases.jsonl"
    manifest_path = dataset_dir / "realistic_gold_manifest.json"
    markdown_path = dataset_dir / "realistic_gold_review.md"

    _write_jsonl(questions_path, questions)
    _write_jsonl(replay_path, replay_cases)
    manifest = _build_manifest(
        dataset_id=args.dataset_id,
        dataset_dir=dataset_dir,
        spec_path=spec_path,
        questions=questions,
        replay_cases=replay_cases,
        corpus_paper_ids=corpus_paper_ids,
    )
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_render_markdown(manifest, questions), encoding="utf-8")

    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(_render_console(manifest))
    return 0


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"JSONL file not found: {path}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
        if _has_secret(record):
            raise SystemExit(f"Secret-like content found at {path}:{line_number}")
        records.append(record)
    return records


def _build_paper_index(query_records: list[dict[str, Any]]) -> list[dict[str, str]]:
    by_id: dict[str, dict[str, str]] = {}
    for record in query_records:
        paper_id = str(record.get("paper_id") or "")
        if not paper_id or paper_id in by_id:
            continue
        by_id[paper_id] = {
            "paper_id": paper_id,
            "paper_title": str(record.get("paper_title") or ""),
            "paper_filename": str(record.get("paper_filename") or ""),
        }
    return list(by_id.values())


def _load_evidence_by_paper(session, paper_ids: list[str]) -> dict[str, list[Evidence]]:
    rows = (
        session.query(Evidence)
        .filter(Evidence.paper_id.in_(paper_ids))
        .order_by(Evidence.paper_id.asc(), Evidence.created_at.asc(), Evidence.id.asc())
        .all()
    )
    by_paper: dict[str, list[Evidence]] = {}
    for row in rows:
        by_paper.setdefault(row.paper_id, []).append(row)
    return by_paper


def _build_questions(
    gold_specs: list[dict[str, Any]],
    paper_index: list[dict[str, str]],
    evidence_by_paper: dict[str, list[Evidence]],
    *,
    dataset_id: str,
    corpus_paper_ids: list[str],
    errors: list[str],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for spec in gold_specs:
        record_id = str(spec.get("id") or "").strip()
        if not record_id:
            errors.append("Gold spec is missing id")
            continue
        if record_id in seen_ids:
            errors.append(f"Duplicate realistic-gold id: {record_id}")
            continue
        seen_ids.add(record_id)

        query = str(spec.get("query") or "").strip()
        if len(_tokens(query)) < 8:
            errors.append(f"{record_id} query has fewer than 8 searchable tokens")
            continue
        leak_terms = [str(item) for item in spec.get("blind_leak_terms") or [] if item]
        leaked = [term for term in leak_terms if _contains_phrase(query, term)]
        if leaked:
            errors.append(f"{record_id} query leaks target terms: {leaked}")
            continue

        gold_targets = []
        used_evidence_ids: set[str] = set()
        for target in spec.get("gold_targets") or []:
            resolved = _resolve_target(target, paper_index, evidence_by_paper, record_id, errors)
            if resolved is None:
                continue
            if resolved["evidence_id"] in used_evidence_ids:
                errors.append(f"{record_id} maps duplicate evidence {resolved['evidence_id']}")
                continue
            used_evidence_ids.add(resolved["evidence_id"])
            gold_targets.append(resolved)
        if not gold_targets:
            errors.append(f"{record_id} has no resolved gold targets")
            continue
        if not any(item["role"] == "primary" for item in gold_targets):
            errors.append(f"{record_id} has no primary gold target")
            continue

        primary_ids = [item["evidence_id"] for item in gold_targets if item["role"] == "primary"]
        supporting_ids = [
            item["evidence_id"] for item in gold_targets if item["role"] == "supporting"
        ]
        records.append(
            {
                "id": record_id,
                "dataset_id": dataset_id,
                "evaluation_mode": "realistic_no_per_query_paper_filter",
                "query": query,
                "intent": str(spec.get("intent") or "realistic_eval"),
                "difficulty": str(spec.get("difficulty") or "realistic_hard"),
                "blind_leak_terms": leak_terms,
                "corpus_paper_ids": corpus_paper_ids,
                "gold_evidence_ids": [item["evidence_id"] for item in gold_targets],
                "primary_gold_evidence_ids": primary_ids,
                "supporting_gold_evidence_ids": supporting_ids,
                "gold_targets": gold_targets,
                "quality": {
                    "gold_target_count": len(gold_targets),
                    "primary_gold_count": len(primary_ids),
                    "supporting_gold_count": len(supporting_ids),
                    "query_token_count": len(_tokens(query)),
                    "reviewer_status": "gold_label_reviewed",
                },
            }
        )
    return records


def _resolve_target(
    target: dict[str, Any],
    paper_index: list[dict[str, str]],
    evidence_by_paper: dict[str, list[Evidence]],
    record_id: str,
    errors: list[str],
) -> dict[str, Any] | None:
    alias = str(target.get("paper_alias") or "").strip()
    paper = _find_paper(alias, paper_index)
    if paper is None:
        errors.append(f"{record_id} target paper not found: {alias}")
        return None
    role = str(target.get("role") or "").strip().lower()
    if role not in {"primary", "supporting"}:
        errors.append(f"{record_id} target {alias} has unsupported role {role}")
        return None
    candidates = evidence_by_paper.get(paper["paper_id"], [])
    scored: list[tuple[int, int, str, Evidence, list[str]]] = []
    for index, evidence in enumerate(candidates):
        score, missing_terms = _score_evidence(evidence, target)
        if score <= 0:
            continue
        scored.append((score, -index, evidence.id, evidence, missing_terms))
    scored.sort(reverse=True)
    if not scored:
        errors.append(f"{record_id} has no evidence candidate for {alias}")
        return None
    score, _negative_index, _evidence_id, evidence, missing_terms = scored[0]
    if missing_terms:
        errors.append(
            f"{record_id} evidence candidate {evidence.id} for {alias} "
            f"misses required terms: {missing_terms}"
        )
        return None
    return {
        "role": role,
        "paper_alias": alias,
        "paper_id": paper["paper_id"],
        "paper_title": paper["paper_title"],
        "paper_filename": paper["paper_filename"],
        "evidence_id": evidence.id,
        "evidence_type": evidence.evidence_type,
        "section_title": evidence.supports or "",
        "required_terms": [str(item) for item in target.get("required_terms") or []],
        "label_rationale": str(target.get("rationale") or ""),
        "match_score": score,
        "evidence_excerpt": _clip(_evidence_text(evidence), 320),
    }


def _find_paper(alias: str, paper_index: list[dict[str, str]]) -> dict[str, str] | None:
    normalized_alias = _normalize(alias)
    best: tuple[int, dict[str, str]] | None = None
    for paper in paper_index:
        haystack = _normalize(f"{paper['paper_title']} {paper['paper_filename']}")
        score = 0
        if normalized_alias in haystack:
            score += 100 + len(normalized_alias)
        alias_tokens = set(normalized_alias.split())
        haystack_tokens = set(haystack.split())
        score += 10 * len(alias_tokens.intersection(haystack_tokens))
        if score and (best is None or score > best[0]):
            best = (score, paper)
    return best[1] if best else None


def _score_evidence(evidence: Evidence, target: dict[str, Any]) -> tuple[int, list[str]]:
    evidence_type = (evidence.evidence_type or "").strip().lower()
    target_type = str(target.get("evidence_type") or "").strip().lower()
    section_hint = str(target.get("section_hint") or "")
    text = _normalize(_evidence_text(evidence))
    supports = _normalize(evidence.supports or "")
    score = 0
    if evidence_type == "citation" and not target.get("allow_reference", False):
        return 0, ["citation evidence is not allowed for this gold target"]
    if target_type:
        if evidence_type != target_type:
            return 0, [f"evidence_type={target_type}"]
        score += 20
    if section_hint:
        hint_tokens = _tokens(section_hint)
        if hint_tokens and all(token in supports for token in hint_tokens):
            score += 12
        elif hint_tokens and all(token in text for token in hint_tokens):
            score += 6
        else:
            return 0, [f"section_hint={section_hint}"]
    missing_terms = []
    for term in target.get("required_terms") or []:
        term_text = str(term)
        term_tokens = _tokens(term_text)
        if not term_tokens:
            continue
        if all(token in text for token in term_tokens):
            score += 10 + len(term_tokens)
        else:
            missing_terms.append(term_text)
    if str(target.get("role") or "").lower() == "primary":
        score += 3
    return score, missing_terms


def _build_replay_cases(
    questions: list[dict[str, Any]],
    dataset_id: str,
    corpus_paper_ids: list[str],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, item in enumerate(questions, start=1):
        records.append(
            {
                "id": f"realistic_replay_{index:04d}",
                "case_type": "context_search_realistic",
                "query": item["query"],
                "expected": {
                    "query": item["query"],
                    "corpus_paper_ids": corpus_paper_ids,
                    "per_query_paper_filter": False,
                    "primary_gold_evidence_ids": item["primary_gold_evidence_ids"],
                    "supporting_gold_evidence_ids": item["supporting_gold_evidence_ids"],
                    "gold_evidence_ids": item["gold_evidence_ids"],
                    "min_primary_hit_count": 1,
                    "limit": 8,
                    "include_graph": False,
                    "live_status": "completed",
                },
                "observed": {
                    "dataset_id": dataset_id,
                    "realistic_gold_id": item["id"],
                    "gold_evidence_ids": item["gold_evidence_ids"],
                },
                "verdict": "needs_live_retrieval",
                "notes": "Realistic no-per-query-paper-filter replay case with reviewer-labeled gold evidence.",
                "metadata": {
                    "dataset_id": dataset_id,
                    "realistic_gold_id": item["id"],
                    "intent": item["intent"],
                    "evaluation_mode": item["evaluation_mode"],
                },
            }
        )
    return records


def _build_manifest(
    *,
    dataset_id: str,
    dataset_dir: Path,
    spec_path: Path,
    questions: list[dict[str, Any]],
    replay_cases: list[dict[str, Any]],
    corpus_paper_ids: list[str],
) -> dict[str, Any]:
    paper_titles = {
        target["paper_title"] for item in questions for target in item.get("gold_targets") or []
    }
    role_counts = Counter(
        target["role"] for item in questions for target in item.get("gold_targets") or []
    )
    return {
        "dataset_id": dataset_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_dir": str(dataset_dir),
        "gold_spec_path": str(spec_path),
        "realistic_gold_questions_path": str(dataset_dir / "realistic_gold_questions.jsonl"),
        "realistic_replay_cases_path": str(dataset_dir / "realistic_replay_cases.jsonl"),
        "question_count": len(questions),
        "replay_case_count": len(replay_cases),
        "corpus_paper_count": len(corpus_paper_ids),
        "gold_paper_count": len(paper_titles),
        "intents": dict(sorted(Counter(item["intent"] for item in questions).items())),
        "gold_roles": dict(sorted(role_counts.items())),
        "quality_policy": {
            "no_per_query_paper_filter": True,
            "reviewer_labeled_gold": True,
            "paper_evidence_mapping_committed": False,
            "local_artifact_only": True,
        },
    }


def _render_markdown(manifest: dict[str, Any], questions: list[dict[str, Any]]) -> str:
    lines = [
        f"# {manifest['dataset_id']}",
        "",
        f"- Realistic questions: `{manifest['question_count']}`",
        f"- Replay cases: `{manifest['replay_case_count']}`",
        f"- Corpus papers: `{manifest['corpus_paper_count']}`",
        f"- Gold-labeled papers: `{manifest['gold_paper_count']}`",
        "- Per-query paper filter: `false`",
        "",
        "## Gold Labels",
        "",
    ]
    for item in questions:
        lines.append(f"### {item['id']}")
        lines.append("")
        lines.append(f"- Query: {item['query']}")
        lines.append(f"- Intent: `{item['intent']}`")
        for target in item["gold_targets"]:
            lines.append(
                f"- `{target['role']}` {target['paper_title']} / {target['section_title']} "
                f"/ `{target['evidence_id']}`: {target['label_rationale']}"
            )
        lines.append("")
    lines.extend(
        [
            "## Boundary",
            "",
            "This is a local ignored gold-label artifact. It contains paper-derived evidence ids and short excerpts, so do not commit generated mappings.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_console(manifest: dict[str, Any]) -> str:
    return (
        f"Built {manifest['dataset_id']}: {manifest['question_count']} realistic questions, "
        f"{manifest['replay_case_count']} replay cases, "
        f"{manifest['gold_paper_count']} gold-labeled papers."
    )


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records
        ),
        encoding="utf-8",
    )


def _evidence_text(evidence: Evidence) -> str:
    return " ".join(
        [
            evidence.evidence_type or "",
            evidence.supports or "",
            evidence.summary or "",
            evidence.text or "",
        ]
    )


def _tokens(value: str) -> list[str]:
    return [token.lower().strip("-") for token in TOKEN_RE.findall(value or "") if token.strip("-")]


def _normalize(value: str) -> str:
    return " ".join(_tokens(value))


def _contains_phrase(value: str, phrase: str) -> bool:
    return _normalize(phrase) in _normalize(value)


def _clip(value: str, limit: int) -> str:
    value = SECRET_RE.sub("[redacted]", re.sub(r"\s+", " ", value or "")).strip()
    if len(value) <= limit:
        return value
    return value[: limit - 15].rstrip() + "...[truncated]"


def _has_secret(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_has_secret(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_secret(item) for item in value)
    if isinstance(value, str):
        return bool(SECRET_RE.search(value))
    return False


if __name__ == "__main__":
    raise SystemExit(main())
