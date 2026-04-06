# Code proposal prop-003

- local_run_id: local_run_20260404T180454Z_73643
- code_version: c0001
- model: gpt-5.3-codex
- primary_task: t04
- affected_tasks: t04
- policy: include blocking proposals only

## Focus
- problem: Task t04 fails with fail_group=outcome_mismatch. The instruction required an external side effect (email delivery), but the allowed PAC1 tools were repo/file operations plus `report_completion` only. The agent wrote an internal draft and reported `OUTCOME_OK`, while the scorer expected `OUTCOME_NONE_UNSUPPORTED` or `OUTCOME_NONE_CLARIFICATION`. This is an outcome-selection policy miss, not a runtime execution defect.
- solution_type: rules

## Primary task proposal
- none (no blocking code proposals in selected scope)
