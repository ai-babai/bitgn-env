# Code proposal prop-018

- local_run_id: local_run_20260405T105916Z_2421379
- code_version: c0001
- model: gpt-5.3-codex
- primary_task: t26
- affected_tasks: t26
- policy: include blocking proposals only

## Focus
- problem: Task t26 fails with fail_group=write_redundancy. The run failed because `outbox/84207.json` was written twice in one task. Tool traces show a malformed first JSON write (escaped quotes) followed by a corrective rewrite to the same path, and the scorer flagged this as `unexpected file write 'outbox/84207.json'`.
- solution_type: rules

## Primary task proposal
- none (no blocking code proposals in selected scope)
