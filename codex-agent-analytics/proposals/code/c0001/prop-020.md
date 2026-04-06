# Code proposal prop-020

- local_run_id: local_run_20260405T114558Z_2444194
- code_version: c0001
- model: gpt-5.3-codex
- primary_task: t23
- affected_tasks: t23
- policy: include blocking proposals only

## Focus
- problem: Task t23 fails with fail_group=outcome_mismatch. The run returned `OUTCOME_NONE_CLARIFICATION` instead of the expected `OUTCOME_OK`. Evidence shows the agent stopped at duplicate full-name matching in `contacts/` and did not apply account-level disambiguation, even though a passing `t23` run resolved the same pattern by using workflow/account signals and proceeded with an outbox write. The current rule set over-triggers clarification for name collisions that are still deterministically resolvable.
- solution_type: rules

## Primary task proposal
- none (no blocking code proposals in selected scope)
