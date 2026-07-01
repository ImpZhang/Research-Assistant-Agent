#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_DIR = PROJECT_ROOT / "data" / "evaluation" / "geoloc_12paper"
LOCAL_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"


def main() -> int:
    args = parse_args()
    dataset_dir = resolve_project_path(Path(args.dataset_dir or DEFAULT_DATASET_DIR))
    artifacts = profile_artifacts(dataset_dir)
    command_results: list[dict[str, Any]] = []

    if not args.skip_run:
        command_results.extend(run_realistic_eval(args, dataset_dir, artifacts))
        if not command_failed(command_results):
            command_results.extend(run_miss_analysis(dataset_dir, artifacts))

    report = build_report(
        profile=args.profile,
        dataset_dir=dataset_dir,
        artifacts=artifacts,
        command_results=command_results,
    )

    if args.write_json:
        write_text(
            resolve_project_path(Path(args.write_json)),
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
    if args.write_markdown:
        write_text(resolve_project_path(Path(args.write_markdown)), render_markdown(report))

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_console(report))
    return 0 if report["status"] == "pass" else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the resume-facing retrieval evaluation profile and summarize Hit@8, MRR, "
            "replay, miss cases, and failure taxonomy."
        )
    )
    parser.add_argument("--profile", default="realistic", choices=["realistic"])
    parser.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR))
    parser.add_argument("--min-questions", type=int, default=20)
    parser.add_argument("--min-paper-coverage", type=int, default=10)
    parser.add_argument("--min-primary-hit-at-8", type=float, default=0.5)
    parser.add_argument("--min-mrr-primary", type=float, default=0.2)
    parser.add_argument("--min-replay-pass-rate", type=float, default=0.5)
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Only summarize existing quality and miss-analysis artifacts.",
    )
    parser.add_argument("--write-json", default="")
    parser.add_argument("--write-markdown", default="")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def profile_artifacts(dataset_dir: Path) -> dict[str, Path]:
    return {
        "quality_json": dataset_dir / "realistic_quality_report.json",
        "quality_markdown": dataset_dir / "realistic_quality_report.md",
        "failure_replay_jsonl": dataset_dir / "realistic_failure_replay_cases.jsonl",
        "miss_json": dataset_dir / "realistic_miss_analysis.json",
        "miss_markdown": dataset_dir / "realistic_miss_analysis.md",
    }


def run_realistic_eval(
    args: argparse.Namespace,
    dataset_dir: Path,
    artifacts: dict[str, Path],
) -> list[dict[str, Any]]:
    return [
        run_command(
            "realistic_eval",
            [
                python_executable(),
                str(PROJECT_ROOT / "scripts" / "check_geoloc_realistic_eval.py"),
                "--dataset-dir",
                str(dataset_dir),
                "--min-questions",
                str(args.min_questions),
                "--min-paper-coverage",
                str(args.min_paper_coverage),
                "--min-primary-hit-at-8",
                str(args.min_primary_hit_at_8),
                "--min-mrr-primary",
                str(args.min_mrr_primary),
                "--min-replay-pass-rate",
                str(args.min_replay_pass_rate),
                "--write-json",
                str(artifacts["quality_json"]),
                "--write-markdown",
                str(artifacts["quality_markdown"]),
                "--write-failure-replay",
                str(artifacts["failure_replay_jsonl"]),
            ],
        )
    ]


def run_miss_analysis(dataset_dir: Path, artifacts: dict[str, Path]) -> list[dict[str, Any]]:
    return [
        run_command(
            "miss_taxonomy",
            [
                python_executable(),
                str(PROJECT_ROOT / "scripts" / "analyze_geoloc_retrieval_misses.py"),
                "--dataset-dir",
                str(dataset_dir),
                "--write-json",
                str(artifacts["miss_json"]),
                "--write-markdown",
                str(artifacts["miss_markdown"]),
            ],
        )
    ]


def run_command(name: str, args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "name": name,
        "args": [report_command_arg(arg) for arg in args],
        "returncode": completed.returncode,
        "stdout_tail": tail(completed.stdout),
        "stderr_tail": tail(completed.stderr),
    }


def build_report(
    *,
    profile: str,
    dataset_dir: Path,
    artifacts: dict[str, Path],
    command_results: list[dict[str, Any]],
) -> dict[str, Any]:
    quality = read_json_if_exists(artifacts["quality_json"])
    miss = read_json_if_exists(artifacts["miss_json"])
    errors = []
    if quality is None:
        errors.append(f"missing quality report: {artifacts['quality_json']}")
    if miss is None:
        errors.append(f"missing miss analysis report: {artifacts['miss_json']}")
    for command in command_results:
        if command["returncode"] != 0:
            errors.append(f"{command['name']} failed with return code {command['returncode']}")

    quality_status = (quality or {}).get("status")
    miss_status = (miss or {}).get("status")
    if quality is not None and quality_status != "pass":
        errors.append(f"quality report status is {quality_status!r}")
    if miss is not None and miss_status != "pass":
        errors.append(f"miss analysis status is {miss_status!r}")

    quality_metrics = (quality or {}).get("metrics") or {}
    retrieval = quality_metrics.get("retrieval") or {}
    replay = quality_metrics.get("replay") or {}
    miss_summary = (miss or {}).get("summary") or {}
    category_counts = miss_summary.get("category_counts") or {}
    paper_count = int(quality_metrics.get("gold_paper_count") or 0)
    question_count = int(quality_metrics.get("question_count") or 0)
    primary_hit_at_8 = float(retrieval.get("primary_hit_at_8") or 0.0)
    primary_mrr = float(retrieval.get("mrr_primary") or 0.0)
    replay_pass_rate = float(replay.get("pass_rate") or 0.0)
    miss_count = int(miss_summary.get("miss_count") or retrieval.get("miss_count") or 0)

    return {
        "status": "fail" if errors else "pass",
        "checked_at": datetime.now(UTC).isoformat(),
        "profile": profile,
        "dataset_dir": report_path(dataset_dir),
        "commands": command_results,
        "artifacts": {key: report_path(path) for key, path in artifacts.items()},
        "metrics": {
            "paper_count": paper_count,
            "question_count": question_count,
            "primary_hit_at_8": primary_hit_at_8,
            "primary_mrr": primary_mrr,
            "replay_pass_rate": replay_pass_rate,
            "miss_count": miss_count,
            "failure_taxonomy_category_count": len(category_counts),
            "failure_taxonomy_category_counts": category_counts,
        },
        "resume_summary": {
            "paper_count": paper_count,
            "question_count": question_count,
            "primary_hit_at_8_percent": round(primary_hit_at_8 * 100, 2),
            "primary_mrr_percent": round(primary_mrr * 100, 2),
            "replay_pass_rate_percent": round(replay_pass_rate * 100, 2),
            "miss_count": miss_count,
            "failure_taxonomy_category_count": len(category_counts),
        },
        "errors": errors,
    }


def render_console(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    return (
        f"Retrieval eval {report['profile']}: {report['status']} "
        f"papers={metrics['paper_count']} questions={metrics['question_count']} "
        f"primary_hit@8={metrics['primary_hit_at_8']:.4f} "
        f"mrr={metrics['primary_mrr']:.4f} "
        f"replay_pass={metrics['replay_pass_rate']:.4f} "
        f"misses={metrics['miss_count']} "
        f"failure_categories={metrics['failure_taxonomy_category_count']}"
    )


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    summary = report["resume_summary"]
    lines = [
        "# Retrieval Evaluation Summary",
        "",
        f"- Status: `{report['status']}`",
        f"- Profile: `{report['profile']}`",
        f"- Dataset: `{report['dataset_dir']}`",
        f"- Papers: `{metrics['paper_count']}`",
        f"- Questions: `{metrics['question_count']}`",
        f"- Primary Hit@8: `{metrics['primary_hit_at_8']}`",
        f"- Primary MRR: `{metrics['primary_mrr']}`",
        f"- Replay pass rate: `{metrics['replay_pass_rate']}`",
        f"- Misses: `{metrics['miss_count']}`",
        f"- Failure taxonomy categories: `{metrics['failure_taxonomy_category_count']}`",
        "",
        "## Resume Summary",
        "",
        f"- Paper count: `{summary['paper_count']}`",
        f"- Question count: `{summary['question_count']}`",
        f"- Primary Hit@8 percent: `{summary['primary_hit_at_8_percent']}`",
        f"- Primary MRR percent: `{summary['primary_mrr_percent']}`",
        f"- Replay pass rate percent: `{summary['replay_pass_rate_percent']}`",
        f"- Miss count: `{summary['miss_count']}`",
        f"- Failure taxonomy category count: `{summary['failure_taxonomy_category_count']}`",
        "",
        "## Failure Taxonomy",
        "",
    ]
    category_counts = metrics["failure_taxonomy_category_counts"]
    lines.extend([f"- `{key}`: `{value}`" for key, value in category_counts.items()] or ["- None"])
    lines.extend(["", "## Artifacts", ""])
    lines.extend([f"- `{key}`: `{value}`" for key, value in report["artifacts"].items()])
    lines.extend(["", "## Errors", ""])
    lines.extend([f"- {error}" for error in report["errors"]] or ["- None"])
    lines.append("")
    return "\n".join(lines)


def read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_project_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def report_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(resolved)


def report_command_arg(value: str) -> str:
    path = Path(value)
    if not path.is_absolute():
        return value
    return report_path(path)


def python_executable() -> str:
    if LOCAL_PYTHON.exists():
        return str(LOCAL_PYTHON)
    return sys.executable


def tail(value: str, limit: int = 1200) -> str:
    cleaned = (value or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[-limit:]


def command_failed(command_results: list[dict[str, Any]]) -> bool:
    return any(command["returncode"] != 0 for command in command_results)


if __name__ == "__main__":
    raise SystemExit(main())
