# Rules proposal prop-004

- local_run_id: local_run_20260408T133900Z_4041991
- rules_version: rv0032
- model: gpt-5.3-codex
- primary_task: t43
- affected_tasks: t43

## Focus
- problem: Task t43 fails with fail_group=outcome_selection. The run correctly computed the relative date and searched captures, but when no exact match was found it still returned `OUTCOME_OK` with nearby items. Scoring evidence shows an explicit outcome mismatch: expected `OUTCOME_NONE_CLARIFICATION`, got `OUTCOME_OK`. This is a completion-outcome policy miss, not a runtime/tooling blocker.
- solution_type: rules

## Primary task proposal
- `t43` fail_group=`outcome_selection`
  - hypothesis: If completion rules require `OUTCOME_NONE_CLARIFICATION` whenever a singular lookup question has zero or multiple exact matches, agents will avoid false-final `OUTCOME_OK` responses on unresolved retrievals.
  - change: Add a compact outcome-selection rule in AGENTS completion guidance: for user prompts that imply exactly one target record (for example, "which X"), first verify cardinality of exact matches. If exact-match count is not exactly one, do not finalize as `OUTCOME_OK`; return `OUTCOME_NONE_CLARIFICATION` with a minimal clarification question (or explicit confirmation request) instead of substituting nearest results.
  - files:
    - `codex-agent-analytics/rules_versions/rv0032/AGENTS.md`: Add 5-9 lines in completion/outcome section defining a singular-lookup cardinality gate and mapping non-singleton results to clarification outcome.
  - rollback: Remove the added singular-lookup clarification gate block from `rules_versions/rv0032/AGENTS.md`.
