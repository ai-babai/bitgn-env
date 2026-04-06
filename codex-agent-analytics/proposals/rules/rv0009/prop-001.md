# Rules proposal prop-001

- local_run_id: local_run_20260404T211806Z_79006
- rules_version: rv0009
- model: gpt-5.3-codex
- primary_task: t13
- affected_tasks: t13

## Focus
- problem: Task t13 fails with fail_group=write_redundancy. The final date was correct, but the run issued duplicate writes to the same two files. Tool trace shows four writes total: first to `accounts/acct_001.json` and `reminders/rem_001.json`, then a second formatting-only rewrite to each path. The scorer flagged both paths as unexpected writes, which is consistent with a strict write-set/write-count contract rather than a date-computation failure.
- solution_type: rules

## Primary task proposal
- `t13` fail_group=`write_redundancy`
  - hypothesis: On strict-scored tasks, corrective rewrite cycles (write, verify, rewrite same path) can fail even when final file contents are correct; requiring one deliberate write per target path reduces this class of failures.
  - change: Add a compact execution rule: before any `write`, capture exact target line formatting and prepare final replacement text; then perform at most one write per target file for the task unless the first write created invalid syntax. Treat post-write cosmetic reindent/reflow edits as disallowed in focused-diff workflows. Verification should be read-only and should not trigger formatting rewrites.
  - files:
    - `codex-agent-analytics/rules_versions/rv0009/AGENTS.md`: Add 3-5 bullets in completion/workflow guidance defining single-pass write discipline, explicit ban on formatting-only rewrites, and pre-write formatting capture.
  - rollback: Remove the added single-pass write bullets from the active rules AGENTS file.
