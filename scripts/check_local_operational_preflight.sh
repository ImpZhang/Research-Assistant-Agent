#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ -n "${LOCAL_PREFLIGHT_STRICT_GIT:-}" ] && [ -z "${PILOT_PREFLIGHT_STRICT_GIT:-}" ]; then
  export PILOT_PREFLIGHT_STRICT_GIT="$LOCAL_PREFLIGHT_STRICT_GIT"
fi

bash scripts/check_pilot_operational_preflight.sh
