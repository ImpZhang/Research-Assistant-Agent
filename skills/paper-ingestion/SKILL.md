---
name: paper-ingestion
description: Ingest local research papers into the Research Assistant Agent. Use when an agent needs to upload .txt, .md, or .pdf papers, extract sections/chunks/evidence, build a paper card, and verify that the paper is ready for downstream literature-to-ideas or context-search workflows.
---

# Paper Ingestion

## Purpose

Turn a local paper file into durable paper, section, chunk, structured evidence, and paper-card records that later workflows can cite.

## Backing APIs And Tools

- `POST /research/papers/upload`
- `GET /research/papers/{paper_id}`
- `GET /research/papers/{paper_id}/evidence`
- `POST /research/papers/{paper_id}/card/extract`
- `POST /research/papers/{paper_id}/card/extract-structured`
- Tool manifest name: `upload_paper`

## Workflow

1. Confirm the file is intentionally provided for local processing; do not inspect private papers unless the operator says they are safe for the task.
2. Upload only supported `.txt`, `.md`, or `.pdf` files through `/research/papers/upload`.
3. Record the returned `paper.id`; downstream workflows should pass ids, not raw file paths.
4. Fetch paper evidence and card records to confirm the paper has usable problem, method, result, limitation, future-work, table, figure-caption, and quantitative-result signals when present.
5. If the heuristic card is weak and model keys are configured, use structured extraction; otherwise keep the deterministic fallback result and mark missing fields as evidence gaps.

## Safety Boundaries

- Do not paste full private paper text into traces, replay cases, or public docs.
- Do not bypass upload size/type guardrails.
- Do not claim SOTA or novelty from ingestion alone.
- Treat extracted chunks as local artifacts under the project root.

## Failure Handling

- Empty or binary-like files should stop at upload guardrails.
- Weak section detection should still preserve source chunks; continue with caveated card extraction.
- Figure/table/result extraction is heuristic text extraction; if a PDF is scanned or table text is visually encoded, create a page-aware follow-up rather than inventing missing evidence.
- For PDFs with poor text extraction, prefer page-aware follow-up extraction work rather than hand-editing database rows.

## Verification

- Run `bash scripts/check_research_workflow_primitives.sh` after changing ingestion, card extraction, gap mining, or idea generation.
- Run `bash scripts/check_context_search_evaluations.sh` after changing chunk/evidence retrieval behavior.
