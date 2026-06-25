#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8010}"
BASE_URL="http://${HOST}:${PORT}"
LOG_DIR="${LOG_DIR:-logs}"
LOG_FILE="${LOG_FILE:-${LOG_DIR}/local-runtime-smoke.log}"

mkdir -p "$LOG_DIR"

python3 - "$HOST" "$PORT" <<'PYIN'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
with socket.socket() as probe:
    probe.settimeout(0.25)
    if probe.connect_ex((host, port)) == 0:
        raise SystemExit(f"{host}:{port} is already in use; set PORT to a free local port")
PYIN

SERVER_PID=""
cleanup() {
  if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

HOST="$HOST" PORT="$PORT" ./scripts/run-local.sh >"$LOG_FILE" 2>&1 &
SERVER_PID="$!"

python3 - "$BASE_URL" <<'PYIN'
import json
import sys
import time
import urllib.error
import urllib.request

base_url = sys.argv[1].rstrip("/")


def fetch(path: str) -> tuple[int, str]:
    with urllib.request.urlopen(f"{base_url}{path}", timeout=2) as response:
        return response.status, response.read().decode("utf-8")


last_error = ""
for _ in range(40):
    try:
        status, text = fetch("/health")
        if status == 200:
            health = json.loads(text)
            if health.get("status") == "ok":
                break
    except (OSError, ValueError, urllib.error.URLError) as exc:
        last_error = str(exc)
    time.sleep(0.25)
else:
    raise SystemExit(f"local server did not become healthy: {last_error}")

ready_status, ready_text = fetch("/health/ready")
ready = json.loads(ready_text)
if ready_status != 200 or ready.get("status") != "ready":
    raise SystemExit("local readiness endpoint did not report ready")

workbench_status, workbench_html = fetch("/workbench")
if workbench_status != 200:
    raise SystemExit("Workbench endpoint did not return HTTP 200")
for token in ["Research Assistant Workbench", "Local Launch", "Local Path"]:
    if token not in workbench_html:
        raise SystemExit(f"Workbench HTML is missing `{token}`")

print("Local runtime smoke passed.")
print(f"Base URL: {base_url}")
PYIN

cleanup
trap - EXIT
