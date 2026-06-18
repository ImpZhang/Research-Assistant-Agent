# Representative Paper Human Review Protocol

This protocol defines the first real-paper review gate for Research Assistant Agent. It is a human review checklist, not a synthetic test fixture, and it must be run with a representative non-sensitive paper chosen by the operator or research owner.

## Purpose

The review verifies whether the Workbench-first pilot experience produces useful research artifacts from a realistic paper:

- paper ingestion and card extraction
- gap mining and idea generation
- evidence ledger, claim validation, readiness, and quality-gate signals
- project cockpit, task board, handoff bundle, release/review artifacts, and dossier export
- operator observability through request ids, readiness checks, and scope status

## Required Input

Use a paper that can be reviewed and stored according to project policy. Do not use private, embargoed, credential-bearing, or legally restricted material unless the operator explicitly approves that data handling path.

Record these fields before the run:

| Field | Value |
| --- | --- |
| Review date | TBD |
| Reviewer | TBD |
| Paper title | TBD |
| Paper source or citation | TBD |
| Commit SHA | TBD |
| Workbench/API path used | Workbench-first |
| Request id samples | TBD |
| Product-effect score and band | TBD |
| Bundle readiness level | TBD |

## Review Steps

1. Confirm `GET /health`, `GET /health/ready`, and authenticated `GET /research/status` are ready for the intended deployment.
2. Confirm Workbench shows runtime readiness, request-id signal, and project scope compatibility before running the paper.
3. Upload the representative paper and run the literature-to-ideas workflow.
4. Review the generated paper card, gaps, idea set, related-work matrix, proposal, experiment plan, evidence ledger, claim validation packet, readiness score, quality gate, cockpit, task board, and dossier.
5. Export the project or idea bundle and confirm the manifest includes the expected readiness, review, release, and signoff metadata.
6. Run `check_product_effect_smoke.sh` with `PRODUCT_EFFECT_SMOKE_PAPER_FILE` pointing to the same representative paper when an automated score is appropriate.
7. Capture human findings in the table below and file implementation follow-ups as task-board items or issues.

## Human Findings

| Area | Pass/Concern/Fail | Evidence | Follow-up |
| --- | --- | --- | --- |
| Paper card fidelity | TBD | TBD | TBD |
| Gap usefulness | TBD | TBD | TBD |
| Idea novelty and feasibility | TBD | TBD | TBD |
| Evidence ledger support routing | TBD | TBD | TBD |
| Claim validation quality | TBD | TBD | TBD |
| Readiness and quality-gate calibration | TBD | TBD | TBD |
| Project cockpit actionability | TBD | TBD | TBD |
| Handoff bundle completeness | TBD | TBD | TBD |
| Workbench usability | TBD | TBD | TBD |
| Observability and support correlation | TBD | TBD | TBD |

## Exit Criteria

A representative-paper review can be marked pilot-acceptable only when:

- the reviewer can explain the paper, generated gaps, and top idea from exported artifacts without reading raw logs
- at least one generated idea has evidence-linked rationale and realistic next tasks
- major unsupported claims are either flagged by claim validation or captured as follow-up tasks
- readiness, quality gate, cockpit, and bundle readiness agree on the main blockers
- Workbench exposes request id and scope/readiness status for support handoff
- all critical concerns have explicit owner, artifact link, or task-board follow-up

## Non-Goals

This protocol does not approve production multi-user isolation, service restarts, migrations, external provider usage, or backup restore execution. Those remain separate operator-approved hardening steps.
