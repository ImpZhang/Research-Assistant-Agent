# Geoloc Evaluation Dataset Quality

This document defines the local 12-paper query-evidence and replay-case dataset used to strengthen the interview and engineering evaluation story beyond a simple real-paper workflow smoke.

## Current Dataset

The generated dataset is local-only and ignored by Git:

- Dataset directory: `data/evaluation/geoloc_12paper/`
- Query-evidence file: `data/evaluation/geoloc_12paper/query_evidence.jsonl`
- Replay cases file: `data/evaluation/geoloc_12paper/replay_cases.jsonl`
- Quality report JSON: `data/evaluation/geoloc_12paper/quality_report.json`
- Quality report Markdown: `data/evaluation/geoloc_12paper/quality_report.md`

The committed repository contains the generator, checker, tests, and docs, but not the generated paper-derived rows.

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

## Interpretation

This dataset is strong evidence for local workflow stability, retrieval grounding checks, and replay infrastructure. It should be described as a local engineering evaluation set, not as a statistical scientific benchmark.

Do not claim:

- scientific SOTA;
- broad geolocalization generalization;
- human-verified citation correctness;
- complete PDF figure/table understanding.

The next quality layer is manual review: inspect sampled query-evidence rows, add human-authored questions, and preserve failed retrieval/citation cases as durable replay cases.
