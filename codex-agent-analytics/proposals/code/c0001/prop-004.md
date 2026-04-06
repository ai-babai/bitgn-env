# Code proposal prop-004

- local_run_id: local_run_20260404T181635Z_74673
- code_version: c0001
- model: gpt-5.3-codex
- primary_task: t05
- affected_tasks: t05
- policy: include blocking proposals only

## Focus
- problem: Task t05 fails with fail_group=outcome_mismatch. The run reported `OUTCOME_OK` after creating a local `.ics` file, but the scorer expected a non-execution outcome (`OUTCOME_NONE_UNSUPPORTED` or `OUTCOME_NONE_CLARIFICATION`). Evidence shows no tool capable of actually sending or scheduling a real calendar invite, so this is a completion-policy mismatch, not a runtime failure.
- solution_type: rules

## Primary task proposal
- none (no blocking code proposals in selected scope)
