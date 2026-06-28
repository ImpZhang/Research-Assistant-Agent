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
DEFAULT_QUESTION_SEEDS = PROJECT_ROOT / "configs" / "geoloc_hard_questions.v1.jsonl"
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]{2,}")
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|Bearer\s+[A-Za-z0-9._\-]{8,})")
STOPWORDS = {
    "about",
    "against",
    "already",
    "another",
    "before",
    "between",
    "claim",
    "could",
    "evidence",
    "first",
    "from",
    "geolocalization",
    "image",
    "idea",
    "paper",
    "papers",
    "proposal",
    "propose",
    "research",
    "should",
    "style",
    "system",
    "that",
    "their",
    "this",
    "what",
    "where",
    "which",
    "with",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Map human-authored geoloc hard questions to local evidence ids."
    )
    parser.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR))
    parser.add_argument("--questions", default=str(DEFAULT_QUESTION_SEEDS))
    parser.add_argument("--dataset-id", default="geoloc_12paper_hard_questions_v1")
    parser.add_argument("--min-hard-questions", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    question_path = Path(args.questions)
    query_records = _read_jsonl(dataset_dir / "query_evidence.jsonl")
    question_seeds = _read_jsonl(question_path)
    paper_index = _build_paper_index(query_records)

    errors: list[str] = []
    with SessionLocal() as session:
        evidence_by_paper = _load_evidence_by_paper(session, paper_index)
        hard_questions = _build_hard_questions(
            question_seeds,
            paper_index,
            evidence_by_paper,
            dataset_id=args.dataset_id,
            errors=errors,
        )

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    if len(hard_questions) < args.min_hard_questions:
        print(
            f"Only built {len(hard_questions)} hard questions; "
            f"minimum is {args.min_hard_questions}.",
            file=sys.stderr,
        )
        return 1

    replay_cases = _build_replay_cases(hard_questions, args.dataset_id)
    hard_path = dataset_dir / "hard_questions.jsonl"
    replay_path = dataset_dir / "hard_question_replay_cases.jsonl"
    manifest_path = dataset_dir / "hard_question_manifest.json"
    markdown_path = dataset_dir / "hard_questions.md"

    _write_jsonl(hard_path, hard_questions)
    _write_jsonl(replay_path, replay_cases)
    manifest = _build_manifest(
        dataset_id=args.dataset_id,
        dataset_dir=dataset_dir,
        question_path=question_path,
        hard_questions=hard_questions,
        replay_cases=replay_cases,
    )
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_render_markdown(manifest, hard_questions), encoding="utf-8")

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


def _load_evidence_by_paper(
    session, paper_index: list[dict[str, str]]
) -> dict[str, list[Evidence]]:
    paper_ids = [item["paper_id"] for item in paper_index]
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


def _build_hard_questions(
    question_seeds: list[dict[str, Any]],
    paper_index: list[dict[str, str]],
    evidence_by_paper: dict[str, list[Evidence]],
    *,
    dataset_id: str,
    errors: list[str],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, seed in enumerate(question_seeds, start=1):
        seed_id = str(seed.get("id") or f"hq_{index:04d}")
        if seed_id in seen_ids:
            errors.append(f"Duplicate hard-question id: {seed_id}")
            continue
        seen_ids.add(seed_id)
        question = str(seed.get("question") or "").strip()
        if len(TOKEN_RE.findall(question)) < 8:
            errors.append(f"{seed_id} question has too few searchable tokens")
            continue
        target_aliases = [str(item).strip() for item in seed.get("target_papers") or [] if item]
        if not target_aliases:
            errors.append(f"{seed_id} has no target_papers")
            continue
        required_terms = [str(item).strip() for item in seed.get("required_terms") or [] if item]
        if len(required_terms) < 2:
            errors.append(f"{seed_id} needs at least two required_terms")
            continue

        mapped: list[dict[str, Any]] = []
        used_evidence_ids: set[str] = set()
        for alias in target_aliases:
            paper = _find_paper(alias, paper_index)
            if paper is None:
                errors.append(f"{seed_id} target paper not found: {alias}")
                continue
            evidence = _select_evidence(
                evidence_by_paper.get(paper["paper_id"], []),
                question=question,
                required_terms=required_terms,
                intent=str(seed.get("intent") or ""),
            )
            if evidence is None:
                errors.append(f"{seed_id} has no evidence match for paper {alias}")
                continue
            if evidence.id in used_evidence_ids:
                continue
            used_evidence_ids.add(evidence.id)
            mapped.append(
                {
                    "paper_id": paper["paper_id"],
                    "paper_title": paper["paper_title"],
                    "paper_filename": paper["paper_filename"],
                    "evidence_id": evidence.id,
                    "evidence_type": evidence.evidence_type,
                    "section_title": evidence.supports or "",
                    "evidence_excerpt": _clip(_evidence_text(evidence), 260),
                }
            )
        if not mapped:
            continue
        records.append(
            {
                "id": seed_id,
                "dataset_id": dataset_id,
                "question": question,
                "query": question,
                "intent": str(seed.get("intent") or "hard_question"),
                "difficulty": str(seed.get("difficulty") or "hard"),
                "target_papers": target_aliases,
                "required_terms": required_terms,
                "gold_paper_ids": [item["paper_id"] for item in mapped],
                "gold_evidence_ids": [item["evidence_id"] for item in mapped],
                "mapped_evidence": mapped,
                "quality": {
                    "mapped_evidence_count": len(mapped),
                    "query_token_count": len(TOKEN_RE.findall(question)),
                    "target_paper_count": len(target_aliases),
                },
            }
        )
    return records


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


def _select_evidence(
    evidences: list[Evidence],
    *,
    question: str,
    required_terms: list[str],
    intent: str,
) -> Evidence | None:
    if not evidences:
        return None
    query_terms = _query_terms(question, required_terms)
    intent_boosts = _intent_evidence_boosts(intent)
    scored: list[tuple[int, int, str, Evidence]] = []
    for index, evidence in enumerate(evidences):
        text = _normalize(_evidence_text(evidence))
        phrase_score = 0
        for term in required_terms:
            normalized_term = _normalize(term)
            if normalized_term and normalized_term in text:
                phrase_score += 8
        token_score = sum(1 for term in query_terms if term in text)
        evidence_type = (evidence.evidence_type or "").replace("_", " ").lower()
        type_score = intent_boosts.get(evidence_type, 0)
        score = phrase_score + token_score + type_score
        scored.append((score, -index, evidence.id, evidence))
    scored.sort(reverse=True)
    if not scored or scored[0][0] <= 0:
        return None
    return scored[0][3]


def _query_terms(question: str, required_terms: list[str]) -> list[str]:
    terms: list[str] = []
    for value in [question, " ".join(required_terms)]:
        for token in TOKEN_RE.findall(value.lower()):
            token = token.strip("-")
            if len(token) < 4 or token in STOPWORDS:
                continue
            if token not in terms:
                terms.append(token)
    return terms


def _intent_evidence_boosts(intent: str) -> dict[str, int]:
    lowered = intent.lower()
    if "baseline" in lowered or "contrast" in lowered:
        return {"comparison": 4, "method": 2}
    if "evaluation" in lowered or "benchmark" in lowered:
        return {"dataset": 4, "result": 4, "limitation": 2}
    if "risk" in lowered or "failure" in lowered or "gap" in lowered:
        return {"limitation": 5, "future work": 3, "problem": 2}
    if "reasoning" in lowered or "method" in lowered or "design" in lowered:
        return {"method": 4, "claim": 2, "problem": 1}
    return {"method": 2, "claim": 1, "comparison": 1}


def _build_replay_cases(
    hard_questions: list[dict[str, Any]],
    dataset_id: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, item in enumerate(hard_questions, start=1):
        records.append(
            {
                "id": f"hard_replay_{index:04d}",
                "case_type": "context_search",
                "query": item["query"],
                "expected": {
                    "query": item["query"],
                    "paper_ids": item["gold_paper_ids"],
                    "required_evidence_ids": item["gold_evidence_ids"],
                    "min_evidence_count": len(item["gold_evidence_ids"]),
                    "limit": 8,
                    "include_graph": False,
                    "live_status": "completed",
                },
                "observed": {
                    "dataset_id": dataset_id,
                    "hard_question_id": item["id"],
                    "gold_evidence_ids": item["gold_evidence_ids"],
                },
                "verdict": "needs_review",
                "notes": "Human-style hard question replay case for local geoloc retrieval stress testing.",
                "metadata": {
                    "dataset_id": dataset_id,
                    "hard_question_id": item["id"],
                    "intent": item["intent"],
                    "target_papers": item["target_papers"],
                },
            }
        )
    return records


def _build_manifest(
    *,
    dataset_id: str,
    dataset_dir: Path,
    question_path: Path,
    hard_questions: list[dict[str, Any]],
    replay_cases: list[dict[str, Any]],
) -> dict[str, Any]:
    paper_titles = {
        evidence["paper_title"]
        for item in hard_questions
        for evidence in item.get("mapped_evidence") or []
    }
    return {
        "dataset_id": dataset_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_dir": str(dataset_dir),
        "question_seed_path": str(question_path),
        "hard_questions_path": str(dataset_dir / "hard_questions.jsonl"),
        "hard_question_replay_cases_path": str(dataset_dir / "hard_question_replay_cases.jsonl"),
        "hard_question_count": len(hard_questions),
        "hard_replay_case_count": len(replay_cases),
        "paper_count": len(paper_titles),
        "intents": dict(sorted(Counter(item["intent"] for item in hard_questions).items())),
        "target_papers": sorted(paper_titles),
        "quality_policy": {
            "human_authored_seed_committed": True,
            "paper_evidence_mapping_committed": False,
            "local_artifact_only": True,
        },
    }


def _render_markdown(manifest: dict[str, Any], hard_questions: list[dict[str, Any]]) -> str:
    lines = [
        f"# {manifest['dataset_id']}",
        "",
        f"- Hard questions: `{manifest['hard_question_count']}`",
        f"- Hard replay cases: `{manifest['hard_replay_case_count']}`",
        f"- Papers covered: `{manifest['paper_count']}`",
        f"- Seed file: `{manifest['question_seed_path']}`",
        "",
        "## Intents",
        "",
    ]
    for intent, count in manifest["intents"].items():
        lines.append(f"- `{intent}`: {count}")
    lines.extend(["", "## Questions", ""])
    for item in hard_questions:
        lines.append(f"- `{item['id']}` {item['question']}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "Questions are committed as reusable human-authored seeds. Evidence mappings are generated locally from SQLite and remain ignored.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_console(manifest: dict[str, Any]) -> str:
    return (
        f"Built {manifest['dataset_id']}: {manifest['hard_question_count']} hard questions, "
        f"{manifest['hard_replay_case_count']} replay cases, {manifest['paper_count']} papers."
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
            evidence.summary or "",
            evidence.supports or "",
            evidence.text or "",
        ]
    )


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9][a-z0-9-]*", (value or "").lower()))


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
