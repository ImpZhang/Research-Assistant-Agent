#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


DEFAULT_GROUND_TRUTH = "data/benchmarks/geoloc/validation.jsonl"
DEFAULT_PREDICTIONS = "outputs/predictions/geoloc/validation.jsonl"
DEFAULT_PROFILE_MANIFEST = "configs/benchmark_profiles.json"


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    ground_truth = resolve_project_path(root, args.ground_truth)
    predictions = resolve_project_path(root, args.predictions)
    profile_manifest = resolve_project_path(root, args.profile_manifest)

    created: list[str] = []
    skipped: list[str] = []
    if args.write_example:
        write_example_file(
            ground_truth,
            [
                {"id": "example-nyc", "country": "US", "lat": 40.7128, "lon": -74.006},
                {"id": "example-paris", "country": "FR", "lat": 48.8566, "lon": 2.3522},
            ],
            root=root,
            created=created,
            skipped=skipped,
        )
        write_example_file(
            predictions,
            [
                {"id": "example-nyc", "country": "US", "lat": 40.7128, "lon": -74.006},
                {"id": "example-paris", "country": "FR", "lat": 48.86, "lon": 2.35},
            ],
            root=root,
            created=created,
            skipped=skipped,
        )
    elif not args.inspect_only:
        ground_truth.parent.mkdir(parents=True, exist_ok=True)
        predictions.parent.mkdir(parents=True, exist_ok=True)

    if args.write_profile_manifest:
        write_profile_manifest(
            profile_manifest,
            ground_truth=ground_truth,
            predictions=predictions,
            root=root,
            created=created,
            skipped=skipped,
        )
    elif not args.inspect_only:
        profile_manifest.parent.mkdir(parents=True, exist_ok=True)

    summary = benchmark_readiness_summary(
        root=root,
        ground_truth=ground_truth,
        predictions=predictions,
        profile_manifest=profile_manifest,
        created=created,
        skipped=skipped,
    )

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        print_human_summary(summary)

    if args.require_runnable and not summary["runnable"]:
        return 1
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare or inspect project-local geolocalization benchmark files "
            "for the guarded benchmark runner."
        )
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--ground-truth", default=DEFAULT_GROUND_TRUTH)
    parser.add_argument("--predictions", default=DEFAULT_PREDICTIONS)
    parser.add_argument("--profile-manifest", default=DEFAULT_PROFILE_MANIFEST)
    parser.add_argument(
        "--write-example",
        action="store_true",
        help="Write small ignored JSONL example files only when the target files do not exist.",
    )
    parser.add_argument(
        "--write-profile-manifest",
        action="store_true",
        help="Write an ignored configs/benchmark_profiles.json profile when absent.",
    )
    parser.add_argument(
        "--inspect-only",
        action="store_true",
        help="Inspect paths without creating directories or files.",
    )
    parser.add_argument(
        "--require-runnable",
        action="store_true",
        help="Exit with a non-zero code unless ground truth and predictions are runnable.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args()


def resolve_project_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise SystemExit(f"path must stay inside project root: {path}") from exc
    return resolved


def write_example_file(
    path: Path,
    records: list[dict[str, Any]],
    *,
    root: Path,
    created: list[str],
    skipped: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rel_path = relative_path(path, root)
    if path.exists():
        skipped.append(rel_path)
        return
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records)
        + "\n",
        encoding="utf-8",
    )
    created.append(rel_path)


def write_profile_manifest(
    path: Path,
    *,
    ground_truth: Path,
    predictions: Path,
    root: Path,
    created: list[str],
    skipped: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rel_path = relative_path(path, root)
    if path.exists():
        skipped.append(rel_path)
        return

    ground_truth_rel = relative_path(ground_truth, root)
    predictions_rel = relative_path(predictions, root)
    manifest = {
        "profiles": [
            {
                "id": "local-geoloc-validation",
                "label": "Local geolocalization validation",
                "description": "Machine-local geolocalization validation split.",
                "benchmark_name": "Local geolocalization validation",
                "dataset": "local-geoloc",
                "split": "validation",
                "baseline_name": "nearest recorded baseline",
                "primary_metric": "country_accuracy",
                "metric_direction": "higher_is_better",
                "command_args": [
                    "python3",
                    "scripts/benchmark_geoloc_predictions.py",
                    "--ground-truth",
                    ground_truth_rel,
                    "--predictions",
                    predictions_rel,
                    "--baseline-country-accuracy",
                    "0.0",
                ],
                "working_directory": ".",
                "metrics_output_path": "",
                "parse_stdout_json": True,
                "timeout_seconds": 120,
                "required_paths": [
                    "scripts/benchmark_geoloc_predictions.py",
                    ground_truth_rel,
                    predictions_rel,
                ],
                "config": {
                    "profile_kind": "geolocalization",
                    "ground_truth_path": ground_truth_rel,
                    "predictions_path": predictions_rel,
                },
            }
        ]
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    created.append(rel_path)


def benchmark_readiness_summary(
    *,
    root: Path,
    ground_truth: Path,
    predictions: Path,
    profile_manifest: Path,
    created: list[str],
    skipped: list[str],
) -> dict[str, Any]:
    ground_truth_report = inspect_jsonl_records(ground_truth, kind="ground_truth")
    prediction_report = inspect_jsonl_records(predictions, kind="predictions")
    missing_paths = [
        relative_path(path, root) for path in (ground_truth, predictions) if not path.exists()
    ]
    blocking_errors = [
        *ground_truth_report["errors"],
        *prediction_report["errors"],
    ]
    warnings = [
        *ground_truth_report["warnings"],
        *prediction_report["warnings"],
    ]

    truth_ids = set(ground_truth_report["ids"])
    prediction_ids = set(prediction_report["ids"])
    matched_ids = sorted(truth_ids & prediction_ids)
    missing_prediction_ids = sorted(truth_ids - prediction_ids)
    extra_prediction_ids = sorted(prediction_ids - truth_ids)
    if missing_prediction_ids:
        warnings.append(
            f"{len(missing_prediction_ids)} ground-truth records are missing predictions."
        )
    if extra_prediction_ids:
        warnings.append(f"{len(extra_prediction_ids)} predictions do not match ground truth ids.")

    runnable = not missing_paths and not blocking_errors
    return {
        "ok": not blocking_errors,
        "runnable": runnable,
        "paths": {
            "ground_truth": relative_path(ground_truth, root),
            "predictions": relative_path(predictions, root),
            "profile_manifest": relative_path(profile_manifest, root),
        },
        "profile_manifest_exists": profile_manifest.exists(),
        "created": created,
        "skipped_existing": skipped,
        "missing_paths": missing_paths,
        "record_counts": {
            "ground_truth": ground_truth_report["record_count"],
            "predictions": prediction_report["record_count"],
            "matched_predictions": len(matched_ids),
            "missing_predictions": len(missing_prediction_ids),
            "extra_predictions": len(extra_prediction_ids),
        },
        "missing_prediction_ids": missing_prediction_ids[:20],
        "extra_prediction_ids": extra_prediction_ids[:20],
        "errors": blocking_errors,
        "warnings": warnings,
        "benchmark_command": [
            "python3",
            "scripts/benchmark_geoloc_predictions.py",
            "--ground-truth",
            relative_path(ground_truth, root),
            "--predictions",
            relative_path(predictions, root),
            "--baseline-country-accuracy",
            "0.0",
        ],
    }


def inspect_jsonl_records(path: Path, *, kind: str) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    ids: list[str] = []
    duplicate_ids: list[str] = []
    if not path.exists():
        return {
            "record_count": 0,
            "ids": ids,
            "errors": errors,
            "warnings": warnings,
        }

    records = load_records(path)
    seen: set[str] = set()
    for index, record in enumerate(records, start=1):
        record_prefix = f"{path}:{index}"
        record_id_value = record_id(record)
        if not record_id_value:
            errors.append(f"{record_prefix} is missing id/image_id/sample_id/filename/path.")
            continue
        if record_id_value in seen:
            duplicate_ids.append(record_id_value)
        seen.add(record_id_value)
        ids.append(record_id_value)

        if kind == "ground_truth" and not country_value(record):
            errors.append(f"{record_prefix} ground truth is missing country/country_code.")
        if kind == "ground_truth" and lat_lon(record) is None:
            errors.append(f"{record_prefix} ground truth is missing lat/lon coordinates.")
        if kind == "predictions" and not country_value(record):
            warnings.append(f"{record_prefix} prediction is missing country/country_code.")
        if kind == "predictions" and lat_lon(record) is None:
            warnings.append(f"{record_prefix} prediction is missing lat/lon coordinates.")

    if not records:
        errors.append(f"{path} contains no JSONL records.")
    if duplicate_ids:
        errors.append(f"{path} contains duplicate ids: {sorted(set(duplicate_ids))[:20]}")

    return {
        "record_count": len(records),
        "ids": ids,
        "errors": errors,
        "warnings": warnings,
    }


def load_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        payload = json.loads(text)
        if not isinstance(payload, list):
            raise ValueError(f"{path} must contain a JSON list or JSONL records")
        return [record for record in payload if isinstance(record, dict)]

    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if not isinstance(payload, dict):
            raise ValueError(f"{path}:{line_number} contains a non-object JSONL record")
        records.append(payload)
    return records


def record_id(record: dict[str, Any]) -> str:
    for key in ("id", "image_id", "sample_id", "filename", "path"):
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def country_value(record: dict[str, Any]) -> str:
    for key in ("country", "country_code", "predicted_country", "label_country"):
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def lat_lon(record: dict[str, Any]) -> tuple[float, float] | None:
    lat = first_float(record, "lat", "latitude", "predicted_lat", "predicted_latitude")
    lon = first_float(record, "lon", "lng", "longitude", "predicted_lon", "predicted_longitude")
    if lat is None or lon is None:
        return None
    return lat, lon


def first_float(record: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = record.get(key)
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def relative_path(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def print_human_summary(summary: dict[str, Any]) -> None:
    print("Local geolocalization benchmark preparation")
    print(f"Runnable: {'yes' if summary['runnable'] else 'no'}")
    print(f"Ground truth: {summary['paths']['ground_truth']}")
    print(f"Predictions: {summary['paths']['predictions']}")
    print(f"Profile manifest: {summary['paths']['profile_manifest']}")
    if summary["created"]:
        print(f"Created: {', '.join(summary['created'])}")
    if summary["skipped_existing"]:
        print(f"Skipped existing: {', '.join(summary['skipped_existing'])}")
    if summary["missing_paths"]:
        print(f"Missing paths: {', '.join(summary['missing_paths'])}")
    for warning in summary["warnings"]:
        print(f"Warning: {warning}")
    for error in summary["errors"]:
        print(f"Error: {error}")
    print("Benchmark command:")
    print(" ".join(summary["benchmark_command"]))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Local geolocalization benchmark preparation failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
