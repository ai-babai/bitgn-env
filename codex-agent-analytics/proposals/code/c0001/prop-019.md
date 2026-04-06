# Code proposal prop-019

- local_run_id: local_run_20260405T112755Z_2432565
- code_version: c0001
- model: gpt-5.3-codex
- primary_task: t30
- affected_tasks: t30
- policy: include blocking proposals only

## Focus
- problem: Task t30 fails with fail_group=one_short_token. The agent submitted `804` while the scorer expected `805`. Run evidence shows it computed `805` blacklist records first, then switched to a deduplicated unique-account interpretation (`805 804 1`) and answered the smaller number without an instruction to count distinct accounts.
- solution_type: rules

## Primary task proposal
- none (no blocking code proposals in selected scope)
