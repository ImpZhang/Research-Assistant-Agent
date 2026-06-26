#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "== Local agent readiness =="
bash scripts/check_local_agent_readiness.sh

echo
echo "== Model provider configuration =="
python3 scripts/check_model_provider_config.py

echo
echo "== Local backup manifest =="
python3 scripts/build_local_backup_manifest.py

echo
echo "== Geolocalization benchmark readiness =="
python3 scripts/prepare_local_geoloc_benchmark.py --inspect-only

echo
echo "Local doctor completed."
