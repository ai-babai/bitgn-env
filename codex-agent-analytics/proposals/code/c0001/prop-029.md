# Code proposal prop-029

- local_run_id: local_run_20260405T161316Z_2570309
- code_version: c0001
- model: gpt-5.3-codex
- primary_task: t23
- affected_tasks: t23
- policy: include blocking proposals only

## Focus
- problem: Task t23 fails with fail_group=outcome_mismatch. The run returned `OUTCOME_NONE_CLARIFICATION` while scoring expected `OUTCOME_OK`. Evidence shows the agent stopped immediately on duplicate same-name contacts because active rules explicitly forbid tie-break disambiguation, even for routine inbox outreach where repository workflow/account signals can reduce to a single recipient.
- solution_type: rules

## Primary task proposal
- none (no blocking code proposals in selected scope)
