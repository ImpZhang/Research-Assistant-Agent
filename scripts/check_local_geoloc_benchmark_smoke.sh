#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

python3 - <<'PYIN'
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


root = Path.cwd()
outputs_dir = root / "outputs"
outputs_dir.mkdir(exist_ok=True)

with TemporaryDirectory(prefix="local-geoloc-benchmark-smoke-", dir=outputs_dir) as tmp_name:
    tmp_dir = Path(tmp_name)
    ground_truth = tmp_dir / "ground_truth.jsonl"
    predictions = tmp_dir / "predictions.jsonl"
    ground_truth.write_text(
        "\n".join(
            [
                json.dumps({"id": "sample-1", "country": "US", "lat": 40.7128, "lon": -74.006}),
                json.dumps({"id": "sample-2", "country": "FR", "lat": 48.8566, "lon": 2.3522}),
                json.dumps({"id": "sample-3", "country": "JP", "lat": 35.6762, "lon": 139.6503}),
            ]
        ),
        encoding="utf-8",
    )
    predictions.write_text(
        "\n".join(
            [
                json.dumps(
                    {"id": "sample-1", "country": "US", "lat": 40.7128, "lon": -74.006}
                ),
                json.dumps(
                    {"id": "sample-2", "country": "DE", "lat": 52.52, "lon": 13.405}
                ),
            ]
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_geoloc_predictions.py",
            "--ground-truth",
            str(ground_truth),
            "--predictions",
            str(predictions),
            "--baseline-country-accuracy",
            "0.3",
            "--baseline-mean-geodesic-km",
            "700.0",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )

payload = json.loads(completed.stdout)
metrics = payload["metrics"]
summary = payload["summary"]
errors: list[str] = []

country = metrics["country_accuracy"]
if country["value"] != 0.333333:
    errors.append(f"expected country_accuracy 0.333333, got {country['value']}")
if country["baseline"] != 0.3 or country["improved"] is not True:
    errors.append("expected country_accuracy to improve over the smoke baseline")
if country["correct"] != 1 or country["total"] != 3:
    errors.append("expected one correct country over three ground-truth records")
if summary["matched_predictions"] != 2 or summary["missing_predictions"] != 1:
    errors.append("expected two matched predictions and one missing prediction")
if summary["missing_prediction_ids"] != ["sample-3"]:
    errors.append("expected sample-3 to be reported as the missing prediction")

mean_distance = metrics.get("mean_geodesic_km")
median_distance = metrics.get("median_geodesic_km")
if not mean_distance or mean_distance["direction"] != "lower_is_better":
    errors.append("expected lower-is-better mean geodesic distance")
elif mean_distance["value"] <= 0 or mean_distance["baseline"] != 700.0:
    errors.append("expected a positive mean geodesic distance with the smoke baseline")
if not median_distance or median_distance["evaluated_pairs"] != 2:
    errors.append("expected median geodesic distance over two evaluated pairs")

if errors:
    print("Local geolocalization benchmark smoke failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Local geolocalization benchmark smoke passed.")
print(json.dumps({"metrics": metrics, "summary": summary}, ensure_ascii=False, sort_keys=True))
PYIN
