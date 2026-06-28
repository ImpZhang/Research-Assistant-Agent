#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.research.db import SessionLocal, init_db  # noqa: E402
from backend.research.services.workflow_worker_service import (  # noqa: E402
    WorkflowWorkerService,
    default_worker_id,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the project-local workflow worker for queued research jobs.",
    )
    parser.add_argument(
        "--worker-id",
        default=default_worker_id(),
        help="Stable label written into job lease metadata.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Claim at most one job and then exit.",
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=0,
        help="Maximum jobs to process before exiting. Use 0 for no limit.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=2.0,
        help="Sleep interval when no job is available.",
    )
    parser.add_argument(
        "--idle-timeout-seconds",
        type=float,
        default=0.0,
        help="Exit after this many idle seconds. Use 0 to wait indefinitely.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    init_db()
    processed = 0
    idle_started_at: float | None = None

    while True:
        with SessionLocal() as session:
            result = WorkflowWorkerService(session, worker_id=args.worker_id).run_once()

        print(json.dumps(result.as_dict(), ensure_ascii=False), flush=True)
        if result.status != "idle":
            processed += 1
            idle_started_at = None
        else:
            idle_started_at = idle_started_at or time.monotonic()

        if args.once:
            return 0 if result.status in {"completed", "idle"} else 1
        if args.max_jobs > 0 and processed >= args.max_jobs:
            return 0
        if (
            args.idle_timeout_seconds > 0
            and idle_started_at is not None
            and time.monotonic() - idle_started_at >= args.idle_timeout_seconds
        ):
            return 0
        time.sleep(max(args.poll_interval_seconds, 0.1))


if __name__ == "__main__":
    raise SystemExit(main())
