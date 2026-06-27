# Project Skill Registry

This registry describes the project-local `skills/*/SKILL.md` files used by future agents and operators. These are repository assets, not a required global Codex installation.

| Skill | Capability | Main verification |
| --- | --- | --- |
| `skills/paper-ingestion/SKILL.md` | Upload papers, extract chunks/evidence, and prepare paper cards. | `bash scripts/check_research_workflow_primitives.sh` |
| `skills/hybrid-context-search/SKILL.md` | Retrieve source chunks, evidence, gaps, ideas, and GraphRAG-lite context. | `bash scripts/check_context_search_evaluations.sh` |
| `skills/literature-to-ideas/SKILL.md` | Run the main paper-to-ideas workflow and inspect job artifacts. | `bash scripts/check_workflow_job_controls.sh` |
| `skills/sota-review/SKILL.md` | Build SOTA review packages, external-search evidence, signoff records, and benchmark readiness gates. | `bash scripts/check_context_search_evaluations.sh` |
| `skills/benchmark-evaluation/SKILL.md` | Prepare local benchmark fixtures, run guarded benchmark packets, and compare metrics. | `bash scripts/check_local_geoloc_benchmark_smoke.sh` |
| `skills/advisor-action-session/SKILL.md` | Produce traced Advisor answers, follow-up tasks, task snapshots, and Markdown action reports. | `bash scripts/check_workflow_job_controls.sh` |

## Naming

Skill directories use hyphen-case for compatibility with standard skill naming rules. They correspond to the earlier roadmap names `paper_ingestion`, `hybrid_context_search`, `literature_to_ideas`, `sota_review`, `benchmark_evaluation`, and `advisor_action_session`.

## Validation

Run:

```bash
bash scripts/check_project_skills.sh
```

The check verifies required skill files, frontmatter names/descriptions, required instruction sections, and absence of placeholder TODOs.
