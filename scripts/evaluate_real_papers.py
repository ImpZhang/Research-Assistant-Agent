#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections.abc import Callable
from datetime import datetime, timezone
import json
import mimetypes
import os
from pathlib import Path
from multiprocessing import Process
import signal
import sys
import time
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from backend.app import create_app  # noqa: E402
from backend.research.db import SessionLocal  # noqa: E402
from backend.research.models import Job, utc_now  # noqa: E402
from backend.research.services.embedding_service import EmbeddingService  # noqa: E402
from backend.research.services.related_work_service import RelatedWorkService  # noqa: E402
from backend.research.services.retrieval_service import RetrievalService  # noqa: E402
from backend.research.services.workflow_service import (  # noqa: E402
    JobCanceledError,
    WorkflowService,
)


DEFAULT_CONTEXT_QUERIES = [
    "worldwide image geolocalization benchmark retrieval reranking",
    "large vision language model reasoning image geolocation",
    "hierarchical geolocalization coordinate prediction dataset evaluation",
]


class WorkflowTimeoutError(TimeoutError):
    pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate real papers through the local agent flow."
    )
    parser.add_argument(
        "papers", nargs="+", help="PDF, text, or Markdown files to upload and evaluate."
    )
    parser.add_argument("--max-gaps", type=int, default=3)
    parser.add_argument("--max-ideas-per-gap", type=int, default=1)
    parser.add_argument("--context-limit", type=int, default=5)
    parser.add_argument(
        "--workflow-timeout-seconds",
        type=int,
        default=180,
        help="Abort the workflow worker after this many seconds and recover job artifacts.",
    )
    parser.add_argument(
        "--workflow-mode",
        choices=["async-poll", "sync-endpoint"],
        default="async-poll",
        help=(
            "Run literature-to-ideas through a local job worker and poll status, or use the "
            "legacy synchronous endpoint."
        ),
    )
    parser.add_argument(
        "--workflow-poll-interval-seconds",
        type=float,
        default=1.5,
        help="Polling interval for async-poll workflow jobs.",
    )
    parser.add_argument(
        "--deep-step-timeout-seconds",
        type=int,
        default=45,
        help="Abort each deep quality-loop API call after this many seconds and keep partial results.",
    )
    parser.add_argument(
        "--run-workflow-novelty-check",
        action="store_true",
        help=(
            "Run the workflow's built-in novelty check. Disabled by default because it may call "
            "external literature providers and can dominate real-paper evaluation time."
        ),
    )
    parser.add_argument(
        "--require-external-embeddings",
        action="store_true",
        help="Fail a paper evaluation if embedding rebuild falls back to local hash embeddings.",
    )
    parser.add_argument(
        "--benchmark-profile-id",
        default="",
        help="Optional benchmark profile id to execute for the top generated idea's experiment plan.",
    )
    parser.add_argument(
        "--require-benchmark-profile",
        action="store_true",
        help="Fail a paper evaluation when --benchmark-profile-id is set but cannot execute.",
    )
    parser.add_argument(
        "--skip-deep-quality-loop",
        action="store_true",
        help="Skip proposal/review/experiment-analysis/decision/audit follow-up artifacts.",
    )
    parser.add_argument(
        "--skip-retrieval-mode-comparison",
        action="store_true",
        help="Skip local-hash retrieval baseline comparison for the context queries.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "outputs" / "evaluations"),
        help="Directory for JSON and Markdown evaluation reports.",
    )
    args = parser.parse_args()

    if os.getenv("ALLOW_REAL_PAPER_EVAL") != "1":
        print(
            "Refusing to run real-paper evaluation. Set ALLOW_REAL_PAPER_EVAL=1 "
            "after confirming provider cost/rate-limit expectations."
        )
        return 2

    client = TestClient(create_app())
    started_at = datetime.now(timezone.utc)
    report = {
        "started_at": started_at.isoformat(),
        "project_root": str(PROJECT_ROOT),
        "config": {
            "max_gaps": args.max_gaps,
            "max_ideas_per_gap": args.max_ideas_per_gap,
            "context_limit": args.context_limit,
            "workflow_timeout_seconds": args.workflow_timeout_seconds,
            "workflow_mode": args.workflow_mode,
            "workflow_poll_interval_seconds": args.workflow_poll_interval_seconds,
            "deep_step_timeout_seconds": args.deep_step_timeout_seconds,
            "run_workflow_novelty_check": args.run_workflow_novelty_check,
            "require_external_embeddings": args.require_external_embeddings,
            "benchmark_profile_id": args.benchmark_profile_id,
            "require_benchmark_profile": args.require_benchmark_profile,
            "run_deep_quality_loop": not args.skip_deep_quality_loop,
            "compare_retrieval_modes": not args.skip_retrieval_mode_comparison,
        },
        "health": _require_ok(client.get("/health"), "health"),
        "readiness": _require_ok(client.get("/health/ready"), "readiness"),
        "papers": [],
    }
    for paper in args.papers:
        print(f"Evaluating paper: {paper}", flush=True)
        report["papers"].append(
            _evaluate_one_paper(
                client,
                Path(paper).expanduser(),
                max_gaps=args.max_gaps,
                max_ideas_per_gap=args.max_ideas_per_gap,
                context_limit=args.context_limit,
                workflow_timeout_seconds=args.workflow_timeout_seconds,
                workflow_mode=args.workflow_mode,
                workflow_poll_interval_seconds=args.workflow_poll_interval_seconds,
                deep_step_timeout_seconds=args.deep_step_timeout_seconds,
                run_workflow_novelty_check=args.run_workflow_novelty_check,
                require_external_embeddings=args.require_external_embeddings,
                benchmark_profile_id=args.benchmark_profile_id,
                require_benchmark_profile=args.require_benchmark_profile,
                run_deep_quality_loop=not args.skip_deep_quality_loop,
                compare_retrieval_modes=not args.skip_retrieval_mode_comparison,
            )
        )

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["summary"] = _build_summary(report["papers"])
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = started_at.strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"real_paper_eval_{stamp}.json"
    markdown_path = output_dir / f"real_paper_eval_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(_render_markdown(report), encoding="utf-8")
    print(f"Saved JSON report: {json_path}")
    print(f"Saved Markdown report: {markdown_path}")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["summary"]["failed_paper_count"] == 0 else 1


def _evaluate_one_paper(
    client: TestClient,
    path: Path,
    *,
    max_gaps: int,
    max_ideas_per_gap: int,
    context_limit: int,
    workflow_timeout_seconds: int,
    workflow_mode: str,
    workflow_poll_interval_seconds: float,
    deep_step_timeout_seconds: int,
    run_workflow_novelty_check: bool,
    require_external_embeddings: bool,
    benchmark_profile_id: str,
    require_benchmark_profile: bool,
    run_deep_quality_loop: bool,
    compare_retrieval_modes: bool,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "filename": path.name,
        "status": "failed",
        "steps": {},
        "metrics": {},
        "warnings": [],
        "errors": [],
    }
    try:
        if not path.is_file():
            raise FileNotFoundError(str(path))
        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        print(f"- upload: {path.name}", flush=True)
        upload = _require_ok(
            client.post(
                "/research/papers/upload",
                files={"file": (path.name, path.read_bytes(), media_type)},
            ),
            f"upload {path.name}",
        )
        paper = upload["paper"]
        paper_id = paper["id"]
        result["paper"] = paper
        result["steps"]["upload"] = "ok"

        detail = _require_ok(
            client.get(f"/research/papers/{paper_id}"), f"paper detail {path.name}"
        )
        result["paper_detail"] = {
            "section_count": detail.get("section_count", 0),
            "chunk_count": detail.get("chunk_count", 0),
            "evidence_count": detail.get("evidence_count", 0),
        }
        result["steps"]["paper_detail"] = "ok"

        print(f"- workflow: {path.name}", flush=True)
        workflow = _run_workflow_with_recovery(
            client,
            paper_id=paper_id,
            path=path,
            max_gaps=max_gaps,
            max_ideas_per_gap=max_ideas_per_gap,
            run_workflow_novelty_check=run_workflow_novelty_check,
            workflow_timeout_seconds=workflow_timeout_seconds,
            workflow_mode=workflow_mode,
            workflow_poll_interval_seconds=workflow_poll_interval_seconds,
        )
        result["workflow"] = _summarize_workflow(workflow)
        result["steps"]["workflow"] = (
            "recovered" if workflow.get("_recovered_from_job_artifacts") else "ok"
        )

        print(f"- embeddings: {path.name}", flush=True)
        embeddings = _require_ok(
            client.post(
                "/research/embeddings/rebuild",
                json={
                    "paper_ids": [paper_id],
                    "owner_types": ["evidence", "gap", "idea"],
                    "limit": 200,
                },
            ),
            f"embeddings {path.name}",
        )
        result["embeddings"] = embeddings
        result["steps"]["embeddings"] = "ok"
        provider_fallback = _record_provider_fallback_warning(result, embeddings)
        if provider_fallback and require_external_embeddings:
            raise RuntimeError(
                "embedding provider fallback detected while --require-external-embeddings is set"
            )

        context_results = []
        for query in DEFAULT_CONTEXT_QUERIES:
            print(f"- context: {path.name}: {query[:48]}", flush=True)
            context = _require_ok(
                client.post(
                    "/research/search/context",
                    json={
                        "query": query,
                        "paper_ids": [paper_id],
                        "limit": context_limit,
                        "include_graph": True,
                    },
                ),
                f"context search {path.name}",
            )
            context_results.append(_summarize_context(context))
        result["context_searches"] = context_results
        result["steps"]["context_search"] = "ok"
        if compare_retrieval_modes:
            print(f"- retrieval comparison: {path.name}", flush=True)
            result["retrieval_mode_comparison"] = _compare_retrieval_modes(
                paper_id=paper_id,
                current_context_results=context_results,
                context_limit=context_limit,
            )
            result["steps"]["retrieval_mode_comparison"] = "ok"

        idea_ids = [item["id"] for item in workflow.get("ideas", [])]
        if idea_ids:
            idea_id = idea_ids[0]
            result["top_idea_id"] = idea_id
            if run_deep_quality_loop:
                print(f"- deep quality loop: {path.name}", flush=True)
                result["deep_quality_loop"] = _run_deep_quality_loop(
                    client,
                    idea_id=idea_id,
                    workflow=workflow,
                    path=path,
                    step_timeout_seconds=deep_step_timeout_seconds,
                    benchmark_profile_id=benchmark_profile_id,
                    require_benchmark_profile=require_benchmark_profile,
                )
                result["steps"]["deep_quality_loop"] = "ok"
            print(f"- readiness/quality/advisor: {path.name}", flush=True)
            result["readiness"] = _require_ok(
                client.get(f"/research/ideas/{idea_id}/readiness"),
                f"idea readiness {path.name}",
            )
            result["quality_gate"] = _require_ok(
                client.get(f"/research/ideas/{idea_id}/quality-gate"),
                f"idea quality gate {path.name}",
            )
            result["advisor_chat"] = _summarize_advisor(
                _require_ok(
                    client.post(
                        "/research/advisor/chat",
                        json={
                            "question": (
                                "For this geolocalization paper workflow, what should the "
                                "researcher inspect next before trusting the generated idea?"
                            ),
                            "idea_id": idea_id,
                            "paper_ids": [paper_id],
                            "include_context": True,
                            "context_limit": context_limit,
                            "created_by": "real_paper_eval",
                        },
                    ),
                    f"advisor chat {path.name}",
                )
            )
            result["steps"]["idea_quality"] = "ok"

        result["metrics"] = _paper_metrics(result)
        result["status"] = "completed"
    except Exception as exc:
        result["errors"].append(f"{exc.__class__.__name__}: {str(exc)[:500]}")
    return result


def _record_provider_fallback_warning(
    result: dict[str, Any],
    embeddings: dict[str, Any],
) -> bool:
    model = embeddings.get("model", "")
    if model.startswith("local_hash"):
        result.setdefault("warnings", []).append(
            "embedding_provider_fallback: embeddings used local hash fallback instead of the "
            "configured external embedding provider"
        )
        return True
    return False


def _run_workflow_with_recovery(
    client: TestClient,
    *,
    paper_id: str,
    path: Path,
    max_gaps: int,
    max_ideas_per_gap: int,
    run_workflow_novelty_check: bool,
    workflow_timeout_seconds: int,
    workflow_mode: str,
    workflow_poll_interval_seconds: float,
) -> dict[str, Any]:
    payload = {
        "paper_id": paper_id,
        "max_gaps": max_gaps,
        "max_ideas_per_gap": max_ideas_per_gap,
        "run_novelty_check": run_workflow_novelty_check,
        "run_review": True,
        "run_experiment_plan": True,
        "include_markdown_export": True,
    }
    if workflow_mode == "async-poll":
        return _run_workflow_with_local_worker_polling(
            client,
            payload=payload,
            paper_id=paper_id,
            path=path,
            timeout_seconds=workflow_timeout_seconds,
            poll_interval_seconds=workflow_poll_interval_seconds,
        )

    try:
        response = _call_with_timeout(
            lambda: client.post("/research/workflows/literature-to-ideas", json=payload),
            timeout_seconds=workflow_timeout_seconds,
            label=f"workflow {path.name}",
        )
        workflow = _require_ok(response, f"workflow {path.name}")
        workflow["_workflow_execution_mode"] = "sync_endpoint"
        return workflow
    except Exception as exc:
        recovered = _recover_latest_workflow_artifacts(client, paper_id=paper_id)
        if recovered is None:
            raise
        recovered["_workflow_execution_mode"] = "recovered_from_job_artifacts"
        recovered["_workflow_warning"] = f"{exc.__class__.__name__}: {str(exc)[:240]}"
        return recovered


def _run_workflow_with_local_worker_polling(
    client: TestClient,
    *,
    payload: dict[str, Any],
    paper_id: str,
    path: Path,
    timeout_seconds: int,
    poll_interval_seconds: float,
) -> dict[str, Any]:
    job_id = _queue_local_workflow_job(payload)
    worker = Process(target=_run_local_workflow_job_worker, args=(job_id,), daemon=True)
    worker.start()
    poll_history: list[dict[str, Any]] = []
    deadline = time.monotonic() + max(1, timeout_seconds)
    last_stage = ""
    last_status = ""
    final_job: dict[str, Any] | None = None

    while time.monotonic() < deadline:
        job = _require_ok(client.get(f"/research/jobs/{job_id}"), f"workflow job {job_id}")
        final_job = job
        stage = job.get("stage") or (job.get("output") or {}).get("stage") or ""
        status = job.get("status", "")
        progress = float(job.get("progress") or 0.0)
        poll_history.append(
            {
                "status": status,
                "progress": round(progress, 4),
                "stage": stage,
                "stage_message": job.get("stage_message", ""),
            }
        )
        if stage != last_stage or status != last_status:
            print(
                f"  - workflow job {job_id}: {status} {progress:.0%} {stage}".rstrip(),
                flush=True,
            )
            last_stage = stage
            last_status = status
        if status == "completed":
            worker.join(timeout=5)
            artifacts = _require_ok(
                client.get(f"/research/jobs/{job_id}/artifacts"),
                f"workflow artifacts {path.name}",
            )
            workflow = _workflow_from_artifacts(artifacts, recovered_from_job_artifacts=False)
            workflow["_workflow_execution_mode"] = "async_job_polling"
            workflow["_poll_history"] = _compact_poll_history(poll_history)
            return workflow
        if status in {"failed", "canceled"}:
            worker.join(timeout=5)
            recovered = _recover_latest_workflow_artifacts(client, paper_id=paper_id)
            if recovered is None:
                raise RuntimeError(
                    f"workflow job {job_id} ended as {status}: {job.get('error', '')}"
                )
            recovered["_workflow_execution_mode"] = "recovered_from_job_artifacts"
            recovered["_workflow_warning"] = (
                f"workflow job {job_id} ended as {status}: {job.get('error', '')[:240]}"
            )
            recovered["_poll_history"] = _compact_poll_history(poll_history)
            return recovered
        time.sleep(max(0.1, poll_interval_seconds))

    if worker.is_alive():
        worker.terminate()
        worker.join(timeout=5)
    _mark_workflow_job_timed_out(job_id, timeout_seconds)
    recovered = _recover_latest_workflow_artifacts(client, paper_id=paper_id)
    if recovered is None:
        stage = (final_job or {}).get("stage", "")
        raise WorkflowTimeoutError(
            f"workflow {path.name} timed out after {timeout_seconds} seconds at stage {stage}"
        )
    recovered["_workflow_execution_mode"] = "recovered_from_job_artifacts"
    recovered["_workflow_warning"] = (
        f"WorkflowTimeoutError: workflow {path.name} timed out after {timeout_seconds} seconds"
    )
    recovered["_poll_history"] = _compact_poll_history(poll_history)
    return recovered


def _queue_local_workflow_job(payload: dict[str, Any]) -> str:
    session = SessionLocal()
    try:
        job = WorkflowService(session).queue_literature_to_ideas(
            paper_id=payload["paper_id"],
            max_gaps=payload.get("max_gaps", 4),
            max_ideas_per_gap=payload.get("max_ideas_per_gap", 2),
            run_review=payload.get("run_review", True),
            run_novelty_check=payload.get("run_novelty_check", True),
            run_experiment_plan=payload.get("run_experiment_plan", True),
            include_markdown_export=payload.get("include_markdown_export", True),
        )
        return job.id
    finally:
        session.close()


def _run_local_workflow_job_worker(job_id: str) -> None:
    session = SessionLocal()
    try:
        WorkflowService(session).run_literature_to_ideas_job(job_id)
    except JobCanceledError:
        return
    finally:
        session.close()


def _mark_workflow_job_timed_out(job_id: str, timeout_seconds: int) -> None:
    session = SessionLocal()
    try:
        job = session.get(Job, job_id)
        if job is None or job.status not in {"pending", "running"}:
            return
        job.status = "canceled"
        job.error = f"Timed out by real-paper evaluator after {timeout_seconds} seconds"
        job.finished_at = utc_now()
        job.output_json = {
            **(job.output_json or {}),
            "stage": "timed_out",
            "stage_message": job.error,
        }
        session.commit()
    finally:
        session.close()


def _compact_poll_history(poll_history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compacted: list[dict[str, Any]] = []
    seen = set()
    for item in poll_history:
        key = (item.get("status"), item.get("stage"), item.get("progress"))
        if key in seen:
            continue
        seen.add(key)
        compacted.append(item)
    return compacted[-40:]


def _call_with_timeout(
    callback: Callable[[], Any],
    *,
    timeout_seconds: int,
    label: str,
) -> Any:
    if timeout_seconds <= 0 or not hasattr(signal, "SIGALRM"):
        return callback()

    def _raise_timeout(_signum, _frame) -> None:
        raise WorkflowTimeoutError(f"{label} timed out after {timeout_seconds} seconds")

    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        return callback()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def _recover_latest_workflow_artifacts(
    client: TestClient,
    *,
    paper_id: str,
) -> dict[str, Any] | None:
    session = SessionLocal()
    try:
        jobs = (
            session.query(Job)
            .filter(Job.job_type == "literature_to_ideas_workflow")
            .order_by(Job.created_at.desc())
            .limit(50)
            .all()
        )
        candidate = next(
            (
                job
                for job in jobs
                if (job.input_json or {}).get("paper_id") == paper_id
                and (job.output_json or {}).get("idea_ids")
            ),
            None,
        )
    finally:
        session.close()
    if candidate is None:
        return None

    artifacts = _require_ok(
        client.get(f"/research/jobs/{candidate.id}/artifacts"),
        f"workflow artifact recovery {candidate.id}",
    )
    return _workflow_from_artifacts(artifacts)


def _workflow_from_artifacts(
    artifacts: dict[str, Any],
    *,
    recovered_from_job_artifacts: bool = True,
) -> dict[str, Any]:
    job = artifacts.get("job") or {}
    return {
        "job_id": job.get("id", ""),
        "paper": artifacts.get("paper") or {},
        "card": artifacts.get("card") or {},
        "gaps": artifacts.get("gaps", []),
        "ideas": artifacts.get("ideas", []),
        "novelty_checks": artifacts.get("novelty_checks", []),
        "reviews": artifacts.get("reviews", []),
        "experiment_plans": artifacts.get("experiment_plans", []),
        "markdown_export": artifacts.get("markdown_export", ""),
        "message": artifacts.get("message", ""),
        "_job_status": job.get("status", ""),
        "_job_progress": job.get("progress", 0.0),
        "_job_stage": job.get("stage") or (job.get("output") or {}).get("stage", ""),
        "_job_stage_message": job.get("stage_message")
        or (job.get("output") or {}).get("stage_message", ""),
        "_recovered_from_job_artifacts": recovered_from_job_artifacts,
    }


def _run_deep_quality_loop(
    client: TestClient,
    *,
    idea_id: str,
    workflow: dict[str, Any],
    path: Path,
    step_timeout_seconds: int,
    benchmark_profile_id: str,
    require_benchmark_profile: bool,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "related_work_matrix_id": "",
        "related_work_items": 0,
        "proposal_draft_id": "",
        "proposal_review_id": "",
        "proposal_review_decision": "",
        "proposal_review_score": 0.0,
        "experiment_run_id": "",
        "experiment_run_source": "",
        "experiment_analysis_id": "",
        "experiment_analysis_decision": "",
        "benchmark_profile_id": benchmark_profile_id.strip(),
        "benchmark_run_id": "",
        "benchmark_run_status": "",
        "benchmark_metric_count": 0,
        "decision_memo_id": "",
        "decision": "",
        "assumption_audit_id": "",
        "assumption_count": 0,
        "steps": {},
        "warnings": [],
    }

    print(f"  - related work matrix: {path.name}", flush=True)
    related_work = _create_local_related_work_matrix_step(
        idea_id=idea_id,
        path=path,
        timeout_seconds=step_timeout_seconds,
        result=result,
    )
    if related_work is None:
        return result
    result["related_work_matrix_id"] = related_work["id"]
    result["related_work_items"] = len(related_work.get("items", []))

    experiment_plan_id = ""
    if workflow.get("experiment_plans"):
        experiment_plan_id = workflow["experiment_plans"][0]["id"]
    if not experiment_plan_id:
        print(f"  - experiment plan: {path.name}", flush=True)
        experiment_plan = _post_json_step(
            client,
            f"/research/ideas/{idea_id}/experiment-plan",
            json_payload=None,
            label=f"experiment plan {path.name}",
            step_key="experiment_plan",
            timeout_seconds=step_timeout_seconds,
            result=result,
        )
        if not experiment_plan:
            return result
        experiment_plan_id = experiment_plan["id"]

    print(f"  - proposal draft: {path.name}", flush=True)
    proposal = _post_json_step(
        client,
        f"/research/ideas/{idea_id}/proposal-draft",
        json_payload={
            "related_work_matrix_id": related_work["id"],
            "experiment_plan_id": experiment_plan_id,
            "created_by": "real_paper_eval",
        },
        label=f"proposal draft {path.name}",
        step_key="proposal_draft",
        timeout_seconds=step_timeout_seconds,
        result=result,
    )
    if not proposal:
        return result
    result["proposal_draft_id"] = proposal["id"]

    print(f"  - proposal review: {path.name}", flush=True)
    proposal_review = _post_json_step(
        client,
        f"/research/ideas/{idea_id}/proposal-drafts/{proposal['id']}/review",
        json_payload={"reviewer_type": "advisor", "created_by": "real_paper_eval"},
        label=f"proposal review {path.name}",
        step_key="proposal_review",
        timeout_seconds=step_timeout_seconds,
        result=result,
    )
    if proposal_review:
        result["proposal_review_id"] = proposal_review["id"]
        result["proposal_review_decision"] = proposal_review.get("decision", "")
        result["proposal_review_score"] = proposal_review.get("readiness_score", 0.0)

    benchmark_run = _run_optional_benchmark_profile(
        client,
        experiment_plan_id=experiment_plan_id,
        benchmark_profile_id=benchmark_profile_id,
        require_benchmark_profile=require_benchmark_profile,
        path=path,
        timeout_seconds=step_timeout_seconds,
        result=result,
    )
    experiment_run = benchmark_run
    if experiment_run:
        result["benchmark_run_id"] = experiment_run["id"]
        result["benchmark_run_status"] = experiment_run.get("status", "")
        result["benchmark_metric_count"] = len(experiment_run.get("metric_results", {}))
        result["experiment_run_source"] = "benchmark_profile"
    else:
        print(f"  - experiment run: {path.name}", flush=True)
        experiment_run = _post_json_step(
            client,
            f"/research/experiment-plans/{experiment_plan_id}/runs",
            json_payload={
                "title": "Real-paper evaluation dry run",
                "status": "completed",
                "dataset_snapshot": "Synthetic planning checkpoint from real-paper evaluation",
                "parameters": {"mode": "planning_eval", "source": "real_paper_eval"},
                "metric_results": {
                    "planning_completeness": 0.72,
                    "evidence_alignment": 0.68,
                    "novelty_risk_remaining": 0.42,
                },
                "conclusion": (
                    "Planning checkpoint completed; use real benchmark execution before final claims."
                ),
                "notes": "Generated by local real-paper evaluation to exercise the quality gate loop.",
                "created_by": "real_paper_eval",
            },
            label=f"experiment run {path.name}",
            step_key="experiment_run",
            timeout_seconds=step_timeout_seconds,
            result=result,
        )
        result["experiment_run_source"] = "planning_dry_run" if experiment_run else ""
    if not experiment_run:
        return result
    result["experiment_run_id"] = experiment_run["id"]

    print(f"  - experiment analysis: {path.name}", flush=True)
    experiment_analysis = _post_json_step(
        client,
        f"/research/experiment-runs/{experiment_run['id']}/analysis",
        json_payload={"created_by": "real_paper_eval"},
        label=f"experiment analysis {path.name}",
        step_key="experiment_analysis",
        timeout_seconds=step_timeout_seconds,
        result=result,
    )
    if experiment_analysis:
        result["experiment_analysis_id"] = experiment_analysis["id"]
        result["experiment_analysis_decision"] = experiment_analysis.get("decision", "")

    print(f"  - decision memo: {path.name}", flush=True)
    decision_memo = _post_json_step(
        client,
        f"/research/ideas/{idea_id}/decision-memo",
        json_payload={
            "decision": "revise",
            "rationale": [
                "Real-paper evaluation completed the initial evidence, retrieval, proposal, and planning loop.",
                "Novelty and benchmark execution still need manual SOTA collision review before pursuit.",
            ],
            "evidence_ids": _workflow_evidence_ids(workflow),
            "risks": [
                "Generated idea may overlap with recent geolocalization baselines.",
                "Planning metrics are dry-run signals, not executed benchmark results.",
            ],
            "next_commitments": [
                "Run manual SOTA collision review.",
                "Execute one benchmark slice before upgrading decision to pursue.",
            ],
            "created_by": "real_paper_eval",
        },
        label=f"decision memo {path.name}",
        step_key="decision_memo",
        timeout_seconds=step_timeout_seconds,
        result=result,
    )
    if decision_memo:
        result["decision_memo_id"] = decision_memo["id"]
        result["decision"] = decision_memo.get("decision", "")

    print(f"  - assumption audit: {path.name}", flush=True)
    assumption_audit = _post_json_step(
        client,
        f"/research/ideas/{idea_id}/assumption-audit",
        json_payload={
            "assumptions": [
                {
                    "assumption": "The selected benchmark slice exposes a real geolocalization failure mode.",
                    "risk_level": "medium",
                    "falsification_test": "Compare against the source-paper baseline and one recent VLM baseline.",
                },
                {
                    "assumption": "The proposed intervention is not already covered by the nearest SOTA method.",
                    "risk_level": "high",
                    "falsification_test": "Run manual SOTA review and external literature search.",
                },
            ],
            "created_by": "real_paper_eval",
        },
        label=f"assumption audit {path.name}",
        step_key="assumption_audit",
        timeout_seconds=step_timeout_seconds,
        result=result,
    )
    if assumption_audit:
        result["assumption_audit_id"] = assumption_audit["id"]
        result["assumption_count"] = len(assumption_audit.get("assumptions", []))
    return result


def _run_optional_benchmark_profile(
    client: TestClient,
    *,
    experiment_plan_id: str,
    benchmark_profile_id: str,
    require_benchmark_profile: bool,
    path: Path,
    timeout_seconds: int,
    result: dict[str, Any],
) -> dict[str, Any] | None:
    profile_id = benchmark_profile_id.strip()
    if not profile_id:
        return None

    print(f"  - benchmark profile {profile_id}: {path.name}", flush=True)
    try:
        profiles = _require_ok(client.get("/research/benchmark-profiles"), "benchmark profiles")
        profile = next(
            (item for item in profiles.get("profiles", []) if item.get("id") == profile_id),
            None,
        )
        if profile is None:
            raise RuntimeError(f"Benchmark profile not found: {profile_id}")
        if not profile.get("runnable", False):
            reason = profile.get("disabled_reason") or "profile is not runnable"
            raise RuntimeError(f"Benchmark profile {profile_id} is not runnable: {reason}")
    except Exception as exc:
        result["steps"]["benchmark_profile"] = "failed"
        warning = f"benchmark profile {profile_id}: {exc.__class__.__name__}: {str(exc)[:240]}"
        result["warnings"].append(warning)
        if require_benchmark_profile:
            raise RuntimeError(warning) from exc
        return None

    benchmark_run = _post_json_step(
        client,
        f"/research/experiment-plans/{experiment_plan_id}/benchmark-run/execute",
        json_payload={
            "profile_id": profile_id,
            "created_by": "real_paper_eval",
        },
        label=f"benchmark profile {profile_id} {path.name}",
        step_key="benchmark_profile",
        timeout_seconds=timeout_seconds,
        result=result,
    )
    if benchmark_run is None and require_benchmark_profile:
        raise RuntimeError(f"Benchmark profile {profile_id} did not execute.")
    return benchmark_run


def _create_local_related_work_matrix_step(
    *,
    idea_id: str,
    path: Path,
    timeout_seconds: int,
    result: dict[str, Any],
) -> dict[str, Any] | None:
    label = f"related work matrix {path.name}"
    try:
        matrix = _call_with_timeout(
            lambda: _create_local_related_work_matrix(idea_id),
            timeout_seconds=timeout_seconds,
            label=label,
        )
        result["steps"]["related_work_matrix"] = "ok"
        return matrix
    except Exception as exc:
        result["steps"]["related_work_matrix"] = "failed"
        result["warnings"].append(f"{label}: {exc.__class__.__name__}: {str(exc)[:240]}")
        return None


def _create_local_related_work_matrix(idea_id: str) -> dict[str, Any]:
    session = SessionLocal()
    try:
        embedding_service = EmbeddingService(session, embedding_provider_mode="local")
        retrieval_service = RetrievalService(
            session,
            embedding_service=embedding_service,
            rerank_provider_mode="disabled",
        )
        matrix = RelatedWorkService(
            session,
            retrieval_service=retrieval_service,
        ).create_matrix(
            idea_id,
            include_external=False,
            limit=6,
            created_by="real_paper_eval",
        )
        return {
            "id": matrix.id,
            "items": matrix.items_json or [],
            "summary": matrix.summary,
            "checked_sources": matrix.checked_sources_json or [],
        }
    finally:
        session.close()


def _post_json_step(
    client: TestClient,
    path: str,
    *,
    json_payload: dict[str, Any] | None,
    label: str,
    step_key: str,
    timeout_seconds: int,
    result: dict[str, Any],
) -> dict[str, Any] | None:
    try:
        response = _call_with_timeout(
            lambda: (
                client.post(path, json=json_payload)
                if json_payload is not None
                else client.post(path)
            ),
            timeout_seconds=timeout_seconds,
            label=label,
        )
        result["steps"][step_key] = "ok"
        return _require_ok(response, label)
    except Exception as exc:
        result["steps"][step_key] = "failed"
        result["warnings"].append(f"{label}: {exc.__class__.__name__}: {str(exc)[:240]}")
        return None


def _workflow_evidence_ids(workflow: dict[str, Any]) -> list[str]:
    ids = []
    for idea in workflow.get("ideas", []):
        for evidence_id in idea.get("evidence_ids", []):
            if evidence_id and evidence_id not in ids:
                ids.append(evidence_id)
    return ids[:8]


def _require_ok(response, label: str) -> Any:
    if response.status_code >= 400:
        body = _decode_response(response)
        raise RuntimeError(f"{label} failed with HTTP {response.status_code}: {str(body)[:500]}")
    return _decode_response(response)


def _decode_response(response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


def _summarize_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": workflow.get("job_id"),
        "job_status": workflow.get("_job_status", "completed"),
        "job_progress": workflow.get("_job_progress", 1.0),
        "job_stage": workflow.get("_job_stage", ""),
        "job_stage_message": workflow.get("_job_stage_message", ""),
        "execution_mode": workflow.get("_workflow_execution_mode", "sync_endpoint"),
        "recovered_from_job_artifacts": bool(workflow.get("_recovered_from_job_artifacts")),
        "warning": workflow.get("_workflow_warning", ""),
        "poll_history": workflow.get("_poll_history", []),
        "card_id": (workflow.get("card") or {}).get("id"),
        "gap_count": len(workflow.get("gaps", [])),
        "idea_count": len(workflow.get("ideas", [])),
        "review_count": len(workflow.get("reviews", [])),
        "novelty_check_count": len(workflow.get("novelty_checks", [])),
        "experiment_plan_count": len(workflow.get("experiment_plans", [])),
        "markdown_chars": len(workflow.get("markdown_export", "")),
        "gap_titles": [gap.get("title", "") for gap in workflow.get("gaps", [])[:5]],
        "idea_titles": [idea.get("title", "") for idea in workflow.get("ideas", [])[:5]],
    }


def _summarize_context(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "query": context.get("query", ""),
        "retrieval_method": context.get("retrieval_method", ""),
        "evidence_count": len(context.get("evidences", [])),
        "gap_count": len(context.get("gaps", [])),
        "idea_count": len(context.get("ideas", [])),
        "graph_node_count": len(context.get("graph_nodes", [])),
        "graph_edge_count": len(context.get("graph_edges", [])),
        "top_evidence_id": _top_nested_id(context.get("evidences", []), "evidence"),
        "top_evidence_score": _top_score(context.get("evidences", [])),
        "top_evidence_terms": _top_terms(context.get("evidences", [])),
        "top_gap_id": _top_nested_id(context.get("gaps", []), "gap"),
        "top_gap_score": _top_score(context.get("gaps", [])),
        "top_idea_id": _top_nested_id(context.get("ideas", []), "idea"),
        "top_idea_score": _top_score(context.get("ideas", [])),
    }


def _compare_retrieval_modes(
    *,
    paper_id: str,
    current_context_results: list[dict[str, Any]],
    context_limit: int,
) -> dict[str, Any]:
    session = SessionLocal()
    try:
        embedding_service = EmbeddingService(session, embedding_provider_mode="local")
        local_stats = embedding_service.rebuild_index(
            owner_types=["evidence", "gap", "idea"],
            paper_ids=[paper_id],
            limit=200,
        )
        retrieval = RetrievalService(
            session,
            embedding_service=embedding_service,
            rerank_provider_mode="disabled",
        )
        comparisons = []
        for current in current_context_results:
            local = _summarize_service_context(
                current["query"],
                retrieval.search_context(
                    query=current["query"],
                    paper_ids=[paper_id],
                    limit=context_limit,
                    include_graph=True,
                ),
            )
            comparisons.append(
                {
                    "query": current["query"],
                    "current": current,
                    "local_hash_no_rerank": local,
                    "top_evidence_overlap": bool(
                        current.get("top_evidence_id")
                        and current.get("top_evidence_id") == local.get("top_evidence_id")
                    ),
                    "top_gap_overlap": bool(
                        current.get("top_gap_id")
                        and current.get("top_gap_id") == local.get("top_gap_id")
                    ),
                    "top_idea_overlap": bool(
                        current.get("top_idea_id")
                        and current.get("top_idea_id") == local.get("top_idea_id")
                    ),
                }
            )
        return {
            "baseline": "local_hash_no_rerank",
            "current": "configured_context_retrieval",
            "query_count": len(comparisons),
            "local_embedding_model": local_stats.model,
            "local_embedding_dimension": local_stats.dimension,
            "local_embedding_indexed": local_stats.indexed_count,
            "top_evidence_overlap_count": sum(
                1 for item in comparisons if item["top_evidence_overlap"]
            ),
            "top_gap_overlap_count": sum(1 for item in comparisons if item["top_gap_overlap"]),
            "top_idea_overlap_count": sum(1 for item in comparisons if item["top_idea_overlap"]),
            "comparisons": comparisons,
        }
    finally:
        session.close()


def _summarize_service_context(query: str, result) -> dict[str, Any]:
    return {
        "query": query,
        "retrieval_method": "local_hash_no_rerank",
        "evidence_count": len(result.evidences),
        "gap_count": len(result.gaps),
        "idea_count": len(result.ideas),
        "graph_node_count": len(result.graph_nodes),
        "graph_edge_count": len(result.graph_edges),
        "top_evidence_id": result.evidences[0].item.id if result.evidences else "",
        "top_evidence_score": round(result.evidences[0].score, 4) if result.evidences else 0.0,
        "top_evidence_terms": result.evidences[0].matched_terms if result.evidences else [],
        "top_gap_id": result.gaps[0].item.id if result.gaps else "",
        "top_gap_score": round(result.gaps[0].score, 4) if result.gaps else 0.0,
        "top_idea_id": result.ideas[0].item.id if result.ideas else "",
        "top_idea_score": round(result.ideas[0].score, 4) if result.ideas else 0.0,
    }


def _summarize_advisor(chat: dict[str, Any]) -> dict[str, Any]:
    return {
        "intent": chat.get("intent", ""),
        "readiness_level": chat.get("readiness_level", ""),
        "recommended_action_count": len(chat.get("recommended_actions", [])),
        "risk_alert_count": len(chat.get("risk_alerts", [])),
        "cited_evidence_count": len(chat.get("cited_evidences", [])),
        "answer_chars": len(chat.get("answer_markdown") or chat.get("answer") or ""),
    }


def _top_score(items: list[dict[str, Any]]) -> float:
    if not items:
        return 0.0
    return round(float(items[0].get("score", 0.0)), 4)


def _top_terms(items: list[dict[str, Any]]) -> list[str]:
    if not items:
        return []
    return items[0].get("matched_terms", [])


def _top_nested_id(items: list[dict[str, Any]], key: str) -> str:
    if not items:
        return ""
    nested = items[0].get(key) or {}
    return str(nested.get("id") or "")


def _paper_metrics(result: dict[str, Any]) -> dict[str, Any]:
    workflow = result.get("workflow", {})
    contexts = result.get("context_searches", [])
    readiness = result.get("readiness", {})
    quality = result.get("quality_gate", {})
    deep = result.get("deep_quality_loop", {})
    retrieval_comparison = result.get("retrieval_mode_comparison", {})
    return {
        "sections": result.get("paper_detail", {}).get("section_count", 0),
        "chunks": result.get("paper_detail", {}).get("chunk_count", 0),
        "evidence": result.get("paper_detail", {}).get("evidence_count", 0),
        "gaps": workflow.get("gap_count", 0),
        "ideas": workflow.get("idea_count", 0),
        "reviews": workflow.get("review_count", 0),
        "experiment_plans": workflow.get("experiment_plan_count", 0),
        "workflow_execution_mode": workflow.get("execution_mode", ""),
        "workflow_recovered": bool(workflow.get("recovered_from_job_artifacts")),
        "workflow_stage": workflow.get("job_stage", ""),
        "workflow_poll_points": len(workflow.get("poll_history", [])),
        "embedding_indexed": result.get("embeddings", {}).get("indexed_count", 0),
        "embedding_model": result.get("embeddings", {}).get("model", ""),
        "embedding_dimension": result.get("embeddings", {}).get("dimension", 0),
        "context_searches_with_evidence": sum(1 for item in contexts if item["evidence_count"] > 0),
        "context_searches_with_graph": sum(1 for item in contexts if item["graph_node_count"] > 0),
        "retrieval_comparison_queries": retrieval_comparison.get("query_count", 0),
        "local_retrieval_embedding_indexed": retrieval_comparison.get(
            "local_embedding_indexed",
            0,
        ),
        "retrieval_top_evidence_overlap": retrieval_comparison.get(
            "top_evidence_overlap_count",
            0,
        ),
        "readiness_score": readiness.get("readiness_score", 0.0),
        "readiness_level": readiness.get("readiness_level") or readiness.get("decision", ""),
        "quality_score": quality.get("overall_score", quality.get("gate_score", 0.0)),
        "quality_decision": quality.get("decision", ""),
        "proposal_review_score": deep.get("proposal_review_score", 0.0),
        "proposal_review_decision": deep.get("proposal_review_decision", ""),
        "experiment_analysis_decision": deep.get("experiment_analysis_decision", ""),
        "decision_memo": deep.get("decision", ""),
        "assumption_count": deep.get("assumption_count", 0),
        "benchmark_run_count": 1 if deep.get("benchmark_run_id") else 0,
        "benchmark_completed_count": (1 if deep.get("benchmark_run_status") == "completed" else 0),
        "benchmark_metric_count": deep.get("benchmark_metric_count", 0),
        "experiment_run_source": deep.get("experiment_run_source", ""),
        "deep_quality_warning_count": len(deep.get("warnings", [])),
        "warning_count": len(result.get("warnings", [])),
        "provider_fallback_warning_count": sum(
            1 for warning in result.get("warnings", []) if "provider_fallback" in str(warning)
        ),
    }


def _build_summary(papers: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [paper for paper in papers if paper["status"] == "completed"]
    failed = [paper for paper in papers if paper["status"] != "completed"]
    return {
        "paper_count": len(papers),
        "completed_paper_count": len(completed),
        "failed_paper_count": len(failed),
        "total_gaps": sum(paper.get("metrics", {}).get("gaps", 0) for paper in completed),
        "total_ideas": sum(paper.get("metrics", {}).get("ideas", 0) for paper in completed),
        "total_embedding_indexed": sum(
            paper.get("metrics", {}).get("embedding_indexed", 0) for paper in completed
        ),
        "papers_with_context_evidence": sum(
            1
            for paper in completed
            if paper.get("metrics", {}).get("context_searches_with_evidence", 0) > 0
        ),
        "papers_with_retrieval_comparison": sum(
            1
            for paper in completed
            if paper.get("metrics", {}).get("retrieval_comparison_queries", 0) > 0
        ),
        "retrieval_top_evidence_overlap": sum(
            paper.get("metrics", {}).get("retrieval_top_evidence_overlap", 0) for paper in completed
        ),
        "retrieval_comparison_queries": sum(
            paper.get("metrics", {}).get("retrieval_comparison_queries", 0) for paper in completed
        ),
        "workflow_recovered_count": sum(
            1 for paper in completed if paper.get("metrics", {}).get("workflow_recovered")
        ),
        "warning_count": sum(
            paper.get("metrics", {}).get("warning_count", 0) for paper in completed
        ),
        "provider_fallback_warning_count": sum(
            paper.get("metrics", {}).get("provider_fallback_warning_count", 0)
            for paper in completed
        ),
        "benchmark_run_count": sum(
            paper.get("metrics", {}).get("benchmark_run_count", 0) for paper in completed
        ),
        "benchmark_completed_count": sum(
            paper.get("metrics", {}).get("benchmark_completed_count", 0) for paper in completed
        ),
        "embedding_models": sorted(
            {
                paper.get("metrics", {}).get("embedding_model", "")
                for paper in completed
                if paper.get("metrics", {}).get("embedding_model")
            }
        ),
    }


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Real Paper Evaluation",
        "",
        f"- Started: `{report['started_at']}`",
        f"- Finished: `{report['finished_at']}`",
        f"- Completed papers: `{report['summary']['completed_paper_count']}` / `{report['summary']['paper_count']}`",
        f"- Total gaps: `{report['summary']['total_gaps']}`",
        f"- Total ideas: `{report['summary']['total_ideas']}`",
        f"- Embedding models: `{', '.join(report['summary']['embedding_models']) or 'n/a'}`",
        f"- Workflow recoveries: `{report['summary'].get('workflow_recovered_count', 0)}`",
        f"- Warnings/provider fallbacks: `{report['summary'].get('warning_count', 0)}` / `{report['summary'].get('provider_fallback_warning_count', 0)}`",
        f"- Benchmark runs/completed: `{report['summary'].get('benchmark_run_count', 0)}` / `{report['summary'].get('benchmark_completed_count', 0)}`",
        f"- Retrieval comparison: `{report['summary'].get('retrieval_top_evidence_overlap', 0)}` / `{report['summary'].get('retrieval_comparison_queries', 0)}` top evidence overlap",
        "",
        "## Papers",
        "",
    ]
    for paper in report["papers"]:
        metrics = paper.get("metrics", {})
        lines.extend(
            [
                f"### {paper['filename']}",
                "",
                f"- Status: `{paper['status']}`",
                f"- Workflow: `{metrics.get('workflow_execution_mode', '')}` stage `{metrics.get('workflow_stage', '')}` recovered `{metrics.get('workflow_recovered', False)}` poll points `{metrics.get('workflow_poll_points', 0)}`",
                f"- Sections/chunks/evidence: `{metrics.get('sections', 0)}` / `{metrics.get('chunks', 0)}` / `{metrics.get('evidence', 0)}`",
                f"- Gaps/ideas/reviews/experiment plans: `{metrics.get('gaps', 0)}` / `{metrics.get('ideas', 0)}` / `{metrics.get('reviews', 0)}` / `{metrics.get('experiment_plans', 0)}`",
                f"- Embedding: `{metrics.get('embedding_model', 'n/a')}` dim `{metrics.get('embedding_dimension', 0)}` indexed `{metrics.get('embedding_indexed', 0)}`",
                f"- Context searches with evidence/graph: `{metrics.get('context_searches_with_evidence', 0)}` / `{metrics.get('context_searches_with_graph', 0)}`",
                f"- Retrieval comparison: `{metrics.get('retrieval_top_evidence_overlap', 0)}` / `{metrics.get('retrieval_comparison_queries', 0)}` top evidence overlap; local indexed `{metrics.get('local_retrieval_embedding_indexed', 0)}`",
                f"- Readiness: `{metrics.get('readiness_level', '')}` score `{metrics.get('readiness_score', 0.0)}`",
                f"- Quality gate: `{metrics.get('quality_decision', '')}` score `{metrics.get('quality_score', 0.0)}`",
                f"- Proposal review: `{metrics.get('proposal_review_decision', '')}` score `{metrics.get('proposal_review_score', 0.0)}`",
                f"- Experiment/decision/assumptions: `{metrics.get('experiment_analysis_decision', '')}` / `{metrics.get('decision_memo', '')}` / `{metrics.get('assumption_count', 0)}`",
                f"- Benchmark: runs `{metrics.get('benchmark_run_count', 0)}` completed `{metrics.get('benchmark_completed_count', 0)}` metrics `{metrics.get('benchmark_metric_count', 0)}` source `{metrics.get('experiment_run_source', '')}`",
                f"- Deep quality warnings: `{metrics.get('deep_quality_warning_count', 0)}`",
                f"- Warnings/provider fallbacks: `{metrics.get('warning_count', 0)}` / `{metrics.get('provider_fallback_warning_count', 0)}`",
            ]
        )
        if paper.get("warnings"):
            lines.append(f"- Warnings: `{' | '.join(paper['warnings'])}`")
        if paper.get("errors"):
            lines.append(f"- Errors: `{' | '.join(paper['errors'])}`")
        workflow = paper.get("workflow", {})
        for title in workflow.get("idea_titles", [])[:3]:
            lines.append(f"- Idea: {title}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
