#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import median
from typing import Any


def main() -> int:
    args = parse_args()
    ground_truth = load_records(args.ground_truth)
    predictions = load_records(args.predictions)
    output = evaluate_predictions(
        ground_truth=ground_truth,
        predictions=predictions,
        baseline_country_accuracy=args.baseline_country_accuracy,
        baseline_mean_geodesic_km=args.baseline_mean_geodesic_km,
    )
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    return 0


def evaluate_predictions(
    *,
    ground_truth: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    baseline_country_accuracy: float | None = None,
    baseline_mean_geodesic_km: float | None = None,
) -> dict[str, Any]:
    predictions_by_id = {record_id(record): record for record in predictions}
    if not ground_truth:
        raise ValueError("ground truth file contains no records")
    correct_country = 0
    matched_predictions = 0
    distances_km: list[float] = []
    missing_prediction_ids: list[str] = []

    for truth in ground_truth:
        truth_id = record_id(truth)
        prediction = predictions_by_id.get(truth_id)
        if prediction is None:
            missing_prediction_ids.append(truth_id)
            continue
        matched_predictions += 1
        if normalize_country(country_value(truth)) == normalize_country(country_value(prediction)):
            correct_country += 1
        distance = geodesic_distance_km(lat_lon(truth), lat_lon(prediction))
        if distance is not None:
            distances_km.append(distance)

    total = len(ground_truth)
    country_accuracy = round(correct_country / total, 6)
    metrics: dict[str, Any] = {
        "country_accuracy": metric_payload(
            value=country_accuracy,
            baseline=baseline_country_accuracy,
            direction="higher_is_better",
            extra={
                "correct": correct_country,
                "total": total,
                "matched_predictions": matched_predictions,
                "missing_predictions": len(missing_prediction_ids),
            },
        )
    }
    if distances_km:
        mean_distance = round(sum(distances_km) / len(distances_km), 6)
        median_distance = round(float(median(distances_km)), 6)
        metrics["mean_geodesic_km"] = metric_payload(
            value=mean_distance,
            baseline=baseline_mean_geodesic_km,
            direction="lower_is_better",
            extra={"evaluated_pairs": len(distances_km)},
        )
        metrics["median_geodesic_km"] = {
            "value": median_distance,
            "direction": "lower_is_better",
            "evaluated_pairs": len(distances_km),
        }

    output = {
        "metrics": metrics,
        "summary": {
            "ground_truth_records": total,
            "prediction_records": len(predictions_by_id),
            "matched_predictions": matched_predictions,
            "missing_predictions": len(missing_prediction_ids),
            "missing_prediction_ids": missing_prediction_ids[:20],
        },
    }
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate project-local geolocalization prediction JSONL files."
    )
    parser.add_argument("--ground-truth", required=True, type=Path)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--baseline-country-accuracy", type=float, default=None)
    parser.add_argument("--baseline-mean-geodesic-km", type=float, default=None)
    return parser.parse_args()


def load_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        payload = json.loads(text)
        if not isinstance(payload, list):
            raise ValueError(f"{path} must contain a JSON list or JSONL records")
        return [record for record in payload if isinstance(record, dict)]
    records = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            payload = json.loads(stripped)
            if not isinstance(payload, dict):
                raise ValueError(f"{path} contains a non-object JSONL record")
            records.append(payload)
    return records


def record_id(record: dict[str, Any]) -> str:
    for key in ("id", "image_id", "sample_id", "filename", "path"):
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    raise ValueError("each record must include id, image_id, sample_id, filename, or path")


def country_value(record: dict[str, Any]) -> str:
    for key in ("country", "country_code", "predicted_country", "label_country"):
        value = record.get(key)
        if value is not None:
            return str(value)
    return ""


def normalize_country(value: str) -> str:
    return value.strip().casefold()


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


def geodesic_distance_km(
    truth: tuple[float, float] | None,
    prediction: tuple[float, float] | None,
) -> float | None:
    if truth is None or prediction is None:
        return None
    lat1, lon1 = truth
    lat2, lon2 = prediction
    radius_km = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    haversine = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return round(radius_km * 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine)), 6)


def metric_payload(
    *,
    value: float,
    baseline: float | None,
    direction: str,
    extra: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "value": value,
        "candidate": value,
        "baseline": baseline,
        "direction": direction,
        **extra,
    }
    if baseline is not None:
        delta = round(value - baseline, 6)
        payload["delta"] = delta
        payload["improved"] = delta > 0 if direction == "higher_is_better" else delta < 0
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
