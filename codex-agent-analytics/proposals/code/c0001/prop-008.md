# Code proposal prop-008

- local_run_id: local_run_20260404T211806Z_79006
- code_version: c0001
- model: gpt-5.3-codex
- primary_task: t13
- affected_tasks: t13
- policy: include blocking proposals only

## Focus
- problem: Task t13 fails with fail_group=write_redundancy. The final date was correct, but the run issued duplicate writes to the same two files. Tool trace shows four writes total: first to `accounts/acct_001.json` and `reminders/rem_001.json`, then a second formatting-only rewrite to each path. The scorer flagged both paths as unexpected writes, which is consistent with a strict write-set/write-count contract rather than a date-computation failure.
- solution_type: rules

## Primary task proposal
- none (no blocking code proposals in selected scope)
