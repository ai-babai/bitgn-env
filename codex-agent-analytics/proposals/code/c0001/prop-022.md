# Code proposal prop-022

- local_run_id: local_run_20260405T120138Z_2451877
- code_version: c0001
- model: gpt-5.3-codex
- primary_task: t26
- affected_tasks: t26
- policy: include blocking proposals only

## Focus
- problem: Task t26 fails with fail_group=json_rewrite_lockout. The run wrote `outbox/84535.json` with escaped quotes (`\\\"`) on first write (tool step 30), and the immediate read-back showed the same escaped content (step 31), leaving invalid JSON for the outbox contract. Local rules then blocked any corrective rewrite on the same `*.json` path and required a non-OK finish, which led to `OUTCOME_NONE_UNSUPPORTED` and no `seq.json` bump.
- solution_type: rules

## Primary task proposal
- none (no blocking code proposals in selected scope)
