# Rules proposal prop-001

- local_run_id: local_run_20260409T140110Z_18813
- rules_version: rv0039
- model: gpt-5.3-codex-spark
- primary_task: t22
- affected_tasks: t22, t24

## Focus
- problem: Task t22 fails with fail_group=answer_mismatch. Heuristic fallback analysis due to empty/non-json Codex output.
- solution_type: rules

## Primary task proposal
- `t22` fail_group=`answer_mismatch`
  - hypothesis: More explicit generic completion policy reduces repeated format/process misses.
  - change: Add one generic pre-completion checklist item in rules; avoid task-specific literals.
  - files:
    - `codex-agent-analytics/rules_versions/rv0039/AGENTS.md`: Append one short generic pre-completion checklist rule.
  - rollback: Revert the added checklist line from next rules version.
