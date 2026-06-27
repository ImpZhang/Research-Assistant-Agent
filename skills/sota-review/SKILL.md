---
name: sota-review
description: Prepare and review source-grounded SOTA and novelty evidence for a research idea. Use when an agent needs manual SOTA review packages, external-search evidence, signoff records, benchmark-readiness gates, or caution around state-of-the-art claims.
---

# SOTA Review

## Purpose

Separate product workflow readiness from scientific SOTA claims. This skill produces review packages and signoff evidence, but final SOTA judgment remains human-gated.

## Backing APIs And Tools

- `POST /research/ideas/{idea_id}/sota-review-package`
- `POST /research/ideas/{idea_id}/sota-external-search-evidence`
- `POST /research/ideas/{idea_id}/sota-signoffs`
- `GET /research/ideas/{idea_id}/benchmark-evidence/readiness`
- Tool manifest names: `create_sota_review_package`, `create_sota_external_search_evidence`, `create_sota_signoff_record`, `get_benchmark_evidence_readiness`

## Workflow

1. Start from a concrete `idea_id` with linked evidence and novelty checks.
2. Create a SOTA review package to collect nearest-work, collision, missing-search, and checklist signals.
3. Add external-search evidence only when local provider settings are configured and the operator wants a real-provider pass.
4. Check benchmark-evidence readiness before recording or interpreting signoff.
5. Save signoff decisions with limitations and blockers; keep ready-for-claim false when benchmark evidence is incomplete.

## Safety Boundaries

- Do not say an idea is SOTA only because a generated review looks positive.
- Do not fabricate nearest-work comparisons or benchmark numbers.
- Do not expose provider keys or raw `.env` values in review notes.

## Failure Handling

- If external search is disabled or partial, record missing searches and keep the claim caveated.
- If benchmark comparisons are absent, block ready-for-claim even if the manual decision is favorable.
- Turn missing evidence into benchmark/readiness tasks rather than overriding gates.

## Verification

- Run `bash scripts/check_context_search_evaluations.sh` after SOTA package, external-search evidence, signoff, benchmark-readiness, or context-evaluation changes.
- Run `bash scripts/check_local_geoloc_benchmark_smoke.sh` before claiming the benchmark harness itself works locally.
