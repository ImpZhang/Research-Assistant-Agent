import json
from pathlib import Path

from scripts import run_retrieval_eval


def test_retrieval_eval_summary_uses_quality_and_miss_reports(tmp_path: Path) -> None:
    quality_path = tmp_path / "realistic_quality_report.json"
    miss_path = tmp_path / "realistic_miss_analysis.json"
    quality_path.write_text(
        json.dumps(
            {
                "status": "pass",
                "metrics": {
                    "gold_paper_count": 3,
                    "question_count": 5,
                    "retrieval": {
                        "primary_hit_at_8": 0.8,
                        "mrr_primary": 0.61,
                        "miss_count": 1,
                    },
                    "replay": {"pass_rate": 0.75},
                },
            }
        ),
        encoding="utf-8",
    )
    miss_path.write_text(
        json.dumps(
            {
                "status": "pass",
                "summary": {
                    "miss_count": 1,
                    "category_counts": {
                        "candidate_competition": 1,
                        "query_term_gap": 1,
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    report = run_retrieval_eval.build_report(
        profile="realistic",
        dataset_dir=tmp_path,
        artifacts={
            "quality_json": quality_path,
            "quality_markdown": tmp_path / "realistic_quality_report.md",
            "failure_replay_jsonl": tmp_path / "realistic_failure_replay_cases.jsonl",
            "miss_json": miss_path,
            "miss_markdown": tmp_path / "realistic_miss_analysis.md",
        },
        command_results=[],
    )

    assert report["status"] == "pass"
    assert report["metrics"]["paper_count"] == 3
    assert report["metrics"]["question_count"] == 5
    assert report["metrics"]["primary_hit_at_8"] == 0.8
    assert report["metrics"]["primary_mrr"] == 0.61
    assert report["metrics"]["replay_pass_rate"] == 0.75
    assert report["metrics"]["failure_taxonomy_category_count"] == 2
    assert report["resume_summary"]["primary_hit_at_8_percent"] == 80.0
    assert report["resume_summary"]["primary_mrr_percent"] == 61.0


def test_retrieval_eval_summary_fails_when_artifacts_are_missing(tmp_path: Path) -> None:
    report = run_retrieval_eval.build_report(
        profile="realistic",
        dataset_dir=tmp_path,
        artifacts=run_retrieval_eval.profile_artifacts(tmp_path),
        command_results=[],
    )

    assert report["status"] == "fail"
    assert any("missing quality report" in error for error in report["errors"])
    assert any("missing miss analysis report" in error for error in report["errors"])
