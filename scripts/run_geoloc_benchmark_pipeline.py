#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from benchmark_geoloc_predictions import evaluate_predictions, load_records  # noqa: E402


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    ground_truth = resolve_project_path(root, args.ground_truth)
    predictions = resolve_project_path(root, args.predictions)
    json_output = resolve_optional_project_path(root, args.write_json)
    markdown_output = resolve_optional_project_path(root, args.write_markdown)

    errors = missing_file_errors(ground_truth=ground_truth, predictions=predictions, root=root)
    if errors:
        report = pipeline_report(
            root=root,
            ground_truth=ground_truth,
            predictions=predictions,
            metrics_payload={"metrics": {}, "summary": {}},
            errors=errors,
        )
        emit_report(
            report, json_output=json_output, markdown_output=markdown_output, as_json=args.json
        )
        return 1

    try:
        metrics_payload = evaluate_predictions(
            ground_truth=load_records(ground_truth),
            predictions=load_records(predictions),
            baseline_country_accuracy=args.baseline_country_accuracy,
            baseline_mean_geodesic_km=args.baseline_mean_geodesic_km,
        )
    except Exception as exc:
        report = pipeline_report(
            root=root,
            ground_truth=ground_truth,
            predictions=predictions,
            metrics_payload={"metrics": {}, "summary": {}},
            errors=[str(exc)],
        )
        emit_report(
            report, json_output=json_output, markdown_output=markdown_output, as_json=args.json
        )
        return 1

    report = pipeline_report(
        root=root,
        ground_truth=ground_truth,
        predictions=predictions,
        metrics_payload=metrics_payload,
        errors=[],
    )
    emit_report(report, json_output=json_output, markdown_output=markdown_output, as_json=args.json)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the project-local geolocalization benchmark pipeline from prediction JSONL "
            "artifacts to JSON/Markdown reports."
        )
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--ground-truth", default="data/benchmarks/geoloc/validation.jsonl")
    parser.add_argument("--predictions", default="outputs/predictions/geoloc/validation.jsonl")
    parser.add_argument("--baseline-country-accuracy", type=float, default=None)
    parser.add_argument("--baseline-mean-geodesic-km", type=float, default=None)
    parser.add_argument("--write-json", default="")
    parser.add_argument("--write-markdown", default="")
    parser.add_argument("--json", action="store_true", help="Print the pipeline report as JSON.")
    return parser.parse_args()


def pipeline_report(
    *,
    root: Path,
    ground_truth: Path,
    predictions: Path,
    metrics_payload: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    summary = metrics_payload.get("summary") or {}
    missing_predictions = int(summary.get("missing_predictions") or 0)
    matched_predictions = int(summary.get("matched_predictions") or 0)
    warnings = []
    if missing_predictions:
        warnings.append(f"{missing_predictions} ground-truth records are missing predictions.")
    if matched_predictions == 0 and not errors:
        warnings.append("No predictions matched the ground-truth ids.")

    decision = "failed" if errors else "completed_with_warnings" if warnings else "completed"
    return {
        "pipeline": "geoloc_prediction_benchmark",
        "decision": decision,
        "ok": not errors,
        "paths": {
            "ground_truth": relative_path(ground_truth, root),
            "predictions": relative_path(predictions, root),
        },
        "metrics": metrics_payload.get("metrics") or {},
        "summary": summary,
        "warnings": warnings,
        "errors": errors,
    }


def emit_report(
    report: dict[str, Any],
    *,
    json_output: Path | None,
    markdown_output: Path | None,
    as_json: bool,
) -> None:
    if json_output is not None:
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    if markdown_output is not None:
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(render_markdown_report(report), encoding="utf-8")
    if as_json or json_output is None:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))


def render_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Geolocalization Benchmark Pipeline Report",
        "",
        f"- Decision: `{report['decision']}`",
        f"- Ground Truth: `{report['paths']['ground_truth']}`",
        f"- Predictions: `{report['paths']['predictions']}`",
        "",
        "## Metrics",
        "",
    ]
    metrics = report.get("metrics") or {}
    if metrics:
        for name in sorted(metrics):
            metric = metrics[name]
            value = metric.get("value", "")
            direction = metric.get("direction", "")
            lines.append(f"- `{name}`: `{value}` ({direction})")
    else:
        lines.append("- None")
    lines.extend(["", "## Summary", ""])
    for key, value in sorted((report.get("summary") or {}).items()):
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {warning}" for warning in report.get("warnings") or ["None"])
    lines.extend(["", "## Errors", ""])
    lines.extend(f"- {error}" for error in report.get("errors") or ["None"])
    return "\n".join(lines).strip() + "\n"


def missing_file_errors(*, ground_truth: Path, predictions: Path, root: Path) -> list[str]:
    errors = []
    for label, path in (("ground truth", ground_truth), ("predictions", predictions)):
        if not path.exists():
            errors.append(f"{label} file does not exist: {relative_path(path, root)}")
    return errors


def resolve_project_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise SystemExit(f"path must stay inside project root: {path}") from exc
    return resolved


def resolve_optional_project_path(root: Path, value: str) -> Path | None:
    if not value:
        return None
    return resolve_project_path(root, value)


def relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
