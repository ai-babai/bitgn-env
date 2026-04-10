# Rules proposal prop-001

- local_run_id: local_run_20260409T181900Z_64781
- rules_version: rv0049
- model: gpt-5.3-codex
- primary_task: t43
- affected_tasks: t43

## Focus
- problem: Task t43 fails with fail_group=one_short_token. The run computed the relative date correctly (`2026-03-01`) and confirmed zero matching captures, but still finalized with `OUTCOME_OK`. Scoring expected `OUTCOME_NONE_CLARIFICATION`, so the failure is an outcome-selection miss for a single-item lookup with no match.
- solution_type: rules

## Primary task proposal
- `t43` fail_group=`one_short_token`
  - hypothesis: When a user question semantically expects exactly one item (for example, "which one"/"what was it"), returning "none found" with `OUTCOME_OK` causes grading and interaction mismatches; a clarification outcome is more robust when candidate count is zero.
  - change: Add a completion rule: for read-only lookup tasks that imply exactly one expected result, run a final cardinality check on the resolved candidate set. If count is 0, forbid `OUTCOME_OK` and return `OUTCOME_NONE_CLARIFICATION` with a minimal disambiguation question (for example, confirm anchor/date scope or alternative range). Keep `OUTCOME_OK` only when exactly one candidate is resolved.
  - files:
    - `codex-agent-analytics/rules_versions/rv0049/AGENTS.md`: Add one focused bullet in the completion/outcome section defining an exact-one cardinality gate for singular lookup prompts and mandatory clarification on zero matches.
  - rollback: Remove the added cardinality-gate bullet from `rules_versions/rv0049/AGENTS.md`.
