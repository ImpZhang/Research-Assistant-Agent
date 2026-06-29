# Geoloc Evaluation Dataset Quality

This document defines the local 12-paper query-evidence and replay-case dataset used to strengthen the interview and engineering evaluation story beyond a simple real-paper workflow smoke.

## Current Dataset

The generated dataset is local-only and ignored by Git:

- Dataset directory: `data/evaluation/geoloc_12paper/`
- Query-evidence file: `data/evaluation/geoloc_12paper/query_evidence.jsonl`
- Replay cases file: `data/evaluation/geoloc_12paper/replay_cases.jsonl`
- Hard-question seed file: `configs/geoloc_hard_questions.v1.jsonl`
- Hard-question mapped file: `data/evaluation/geoloc_12paper/hard_questions.jsonl`
- Hard-question replay cases: `data/evaluation/geoloc_12paper/hard_question_replay_cases.jsonl`
- Realistic gold-label seed file: `configs/geoloc_realistic_gold.v1.jsonl`
- Realistic gold-label mapped file: `data/evaluation/geoloc_12paper/realistic_gold_questions.jsonl`
- Realistic replay cases: `data/evaluation/geoloc_12paper/realistic_replay_cases.jsonl`
- Realistic failure replay cases: `data/evaluation/geoloc_12paper/realistic_failure_replay_cases.jsonl`
- Quality report JSON: `data/evaluation/geoloc_12paper/quality_report.json`
- Quality report Markdown: `data/evaluation/geoloc_12paper/quality_report.md`
- Hard-question quality report JSON: `data/evaluation/geoloc_12paper/hard_question_quality_report.json`
- Hard-question quality report Markdown: `data/evaluation/geoloc_12paper/hard_question_quality_report.md`
- Realistic quality report JSON: `data/evaluation/geoloc_12paper/realistic_quality_report.json`
- Realistic quality report Markdown: `data/evaluation/geoloc_12paper/realistic_quality_report.md`

The committed repository contains the generator, checker, tests, and docs, but not the generated paper-derived rows.
The 20 hard-question prompts are committed because they do not contain paper text. Their evidence-id mappings remain local-only because they are derived from the local SQLite corpus.
The realistic gold-label seed is committed as reviewer-style criteria and rationales. Resolved evidence ids, short evidence excerpts, and failure replay cases remain local-only.

## Build

```bash
.venv/bin/python scripts/build_geoloc_eval_dataset.py \
  --report outputs/evaluations/real_paper_eval_20260628_160429.json \
  --output-dir data/evaluation/geoloc_12paper \
  --dataset-id geoloc_12paper_v1 \
  --min-query-count 50 \
  --max-query-count 80 \
  --replay-count 30 \
  --json
```

## Check

```bash
.venv/bin/python scripts/check_geoloc_eval_dataset.py \
  --dataset-dir data/evaluation/geoloc_12paper \
  --min-queries 50 \
  --max-queries 80 \
  --min-replay-cases 20 \
  --max-replay-cases 30 \
  --min-papers 10 \
  --min-queries-per-paper 2 \
  --run-retrieval \
  --min-hit-at-8 0.85 \
  --min-replay-pass-rate 0.9 \
  --write-json data/evaluation/geoloc_12paper/quality_report.json \
  --write-markdown data/evaluation/geoloc_12paper/quality_report.md \
  --json
```

The checker forces local embedding and disables external rerank while validating retrieval/replay, so it does not call model providers or read secrets.

## Hard Questions

The hard-question layer simulates a researcher looking for paper ideas and asking comparison, novelty-boundary, baseline, failure-mode, and benchmark questions across the 12-paper corpus.
It is still a regression-style check: questions may contain strong method anchors and the checker uses the known target paper ids.

Build the mapped local hard-question dataset:

```bash
.venv/bin/python scripts/build_geoloc_hard_questions.py \
  --dataset-dir data/evaluation/geoloc_12paper \
  --questions configs/geoloc_hard_questions.v1.jsonl \
  --dataset-id geoloc_12paper_hard_questions_v1 \
  --min-hard-questions 20 \
  --json
```

Check retrieval and hard replay behavior:

```bash
.venv/bin/python scripts/check_geoloc_hard_questions.py \
  --dataset-dir data/evaluation/geoloc_12paper \
  --min-hard-questions 20 \
  --min-paper-coverage 12 \
  --min-intent-coverage 12 \
  --run-retrieval \
  --min-any-hit-at-8 1.0 \
  --min-all-hit-at-8 1.0 \
  --min-replay-pass-rate 1.0 \
  --write-json data/evaluation/geoloc_12paper/hard_question_quality_report.json \
  --write-markdown data/evaluation/geoloc_12paper/hard_question_quality_report.md \
  --json
```

## Realistic Gold Evaluation

The realistic layer is the stricter metric surface. It uses reviewer-labeled primary/supporting gold evidence but runs retrieval over the whole 12-paper corpus, not over per-question target paper filters.

Build the resolved gold-label dataset:

```bash
.venv/bin/python scripts/build_geoloc_realistic_eval.py \
  --dataset-dir data/evaluation/geoloc_12paper \
  --gold-spec configs/geoloc_realistic_gold.v1.jsonl \
  --dataset-id geoloc_12paper_realistic_gold_v1 \
  --min-questions 20 \
  --json
```

Run realistic retrieval/replay metrics:

```bash
.venv/bin/python scripts/check_geoloc_realistic_eval.py \
  --dataset-dir data/evaluation/geoloc_12paper \
  --min-questions 20 \
  --min-paper-coverage 12 \
  --min-primary-hit-at-8 0.5 \
  --min-mrr-primary 0.2 \
  --min-replay-pass-rate 0.5 \
  --write-json data/evaluation/geoloc_12paper/realistic_quality_report.json \
  --write-markdown data/evaluation/geoloc_12paper/realistic_quality_report.md \
  --write-failure-replay data/evaluation/geoloc_12paper/realistic_failure_replay_cases.jsonl \
  --json
```

## Latest Quality Result

Latest local result after the 12-paper expansion:

- Query-evidence pairs: `75`
- Replay cases: `30`
- Papers covered: `12`
- Replay case types: `22` context-search cases, `8` citation-audit cases
- Retrieval hit@1: `0.9867`
- Retrieval hit@3: `1.0`
- Retrieval hit@8: `1.0`
- Replay pass rate: `1.0`
- Errors: `0`
- Warnings: `0`

Latest hard-question result:

- Human-style hard questions: `20`
- Hard replay cases: `20`
- Papers covered: `12`
- Intents covered: `19`
- Retrieval any-hit@8: `1.0`
- Retrieval all-gold-hit@8: `1.0`
- Hard replay pass rate: `1.0`
- Errors: `0`
- Warnings: `0`

Latest realistic gold result:

- Reviewer-labeled realistic questions: `20`
- Gold labels: `38` total, `20` primary and `18` supporting
- Corpus scope: `12` papers
- Per-query paper filter: `false`
- Primary hit@1: `0.2`
- Primary hit@3: `0.5`
- Primary hit@5: `0.5`
- Primary hit@8: `0.65`
- Any-gold hit@8: `0.65`
- All-gold hit@8: `0.4`
- Primary MRR: `0.3571`
- Replay pass rate: `0.65`
- Primary misses: `7`
- Partial gold hits: `5`
- Failure replay cases: `7`
- Errors: `0`
- Warnings: `0`
- A second pass matched the first pass on all key retrieval/replay metrics.

## Quality Gates

The current default gates are:

- 50-80 query-evidence pairs.
- 20-30 replay cases.
- At least 10 papers.
- At least 2 query-evidence pairs per paper.
- Every gold evidence id must exist in SQLite and belong to the expected paper.
- Queries must contain at least five searchable tokens.
- Query/gold-evidence term overlap is checked.
- Secret-like values are rejected.
- Evidence excerpts are bounded in length.
- Optional retrieval validation requires hit@8 >= 0.85.
- Optional replay validation requires pass rate >= 0.9.
- Hard-question validation requires 20 questions, 12-paper coverage, broad intent coverage, strict hit@8, and strict replay pass when run with the command above.
- Realistic validation requires reviewer-labeled primary gold, no query leakage of explicit target paper names, no per-query paper filters, corpus-level retrieval, and failure replay export for primary misses.

## Interpretation

This dataset is strong evidence for local workflow stability, retrieval grounding checks, and replay infrastructure. It should be described as a local engineering evaluation set, not as a statistical scientific benchmark.

Do not claim:

- scientific SOTA;
- broad geolocalization generalization;
- human-verified citation correctness;
- complete PDF figure/table understanding.

The hard-question layer improves regression coverage, but the realistic gold layer is the more honest interview metric. The realistic result intentionally drops from `1.0` to `0.65` primary hit@8 because it removes per-query paper filters and keeps failed cases instead of rewriting questions to pass.

The next quality layer is manual review: inspect sampled query-evidence and hard-question mappings, add reviewer comments, and preserve any future failed retrieval/citation cases as durable replay cases.
