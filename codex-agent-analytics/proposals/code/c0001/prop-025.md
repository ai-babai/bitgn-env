# Code proposal prop-025

- local_run_id: local_run_20260405T141258Z_2504781
- code_version: c0001
- model: gpt-5.3-codex
- primary_task: t32
- affected_tasks: t32
- policy: include blocking proposals only

## Focus
- problem: Task t32 fails with fail_group=missing_account_write. The run updated only `reminders/rem_005.json` and reported success, but scoring required a write to `accounts/acct_005.json`. Evidence shows root `AGENTS.md` explicitly requires updating both reminder and owning account when both carry the follow-up date, and both records were read with matching date fields before mutation. The failure is a harness-rule precedence issue, not a runtime/tooling limitation.
- solution_type: rules

## Primary task proposal
- none (no blocking code proposals in selected scope)
