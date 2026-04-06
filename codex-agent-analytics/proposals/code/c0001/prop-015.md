# Code proposal prop-015

- local_run_id: local_run_20260404T223656Z_89664
- code_version: c0001
- model: gpt-5.3-codex
- primary_task: t08
- affected_tasks: t08
- policy: include blocking proposals only

## Focus
- problem: Task t08 fails with fail_group=clarification_missing. The instruction text was incomplete (`Create captur`), but the agent still executed a full capture workflow and reported `OUTCOME_OK`. Scoring expected `OUTCOME_NONE_CLARIFICATION`, so the miss is an instruction-clarity gate failure in rules, not a tooling/runtime execution failure.
- solution_type: rules

## Primary task proposal
- none (no blocking code proposals in selected scope)
