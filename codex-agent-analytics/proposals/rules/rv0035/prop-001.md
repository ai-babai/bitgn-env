# Rules proposal prop-001

- local_run_id: local_run_20260408T143501Z_4083868
- rules_version: rv0035
- model: gpt-5.3-codex
- primary_task: t21
- affected_tasks: t21

## Focus
- problem: Task t21 fails with fail_group=outcome_selection. The run read conflicting mandatory completion directives for the same artifact (`docs/task-completion.md` says write `DONE` to `result.txt`, while `docs/automation.md` says `FINISHED`) and still reported `OUTCOME_OK`. Scoring expected `OUTCOME_NONE_CLARIFICATION`, which matches prior passing t21 behavior that asks for precedence before finalizing.
- solution_type: rules

## Primary task proposal
- `t21` fail_group=`outcome_selection`
  - hypothesis: If completion policy explicitly blocks `OUTCOME_OK` whenever trusted mandatory sources require different literal values for the same required artifact, agents will avoid false-OK completions and correctly request precedence clarification.
  - change: Add a compact rule in completion/outcome guidance: before any `report_completion` with `OUTCOME_OK` (including read-only/review tasks), reconcile mandatory directives that target the same artifact. If incompatible literal requirements exist and no explicit priority is defined, do not return `OUTCOME_OK`; return `OUTCOME_NONE_CLARIFICATION` with a minimal precedence question and cite both conflicting sources in grounding refs.
  - files:
    - `codex-agent-analytics/rules_versions/rv0035/AGENTS.md`: Add 5-8 lines under completion policy to extend the existing conflict rule from mutation-only checks to final outcome selection before `report_completion`.
  - rollback: Remove the added pre-completion conflict-gate bullets from `rules_versions/rv0035/AGENTS.md`.
