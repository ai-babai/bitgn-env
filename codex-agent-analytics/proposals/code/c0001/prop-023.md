# Code proposal prop-023

- local_run_id: local_run_20260405T122453Z_2465862
- code_version: c0001
- model: gpt-5.3-codex
- primary_task: t26
- affected_tasks: t26
- policy: include blocking proposals only

## Focus
- problem: Task t26 fails with fail_group=write_redundancy. Tool traces show two writes to the same new file path (`outbox/84400.json`): an initial escaped-quote JSON write followed by a corrective rewrite. The scorer then reported `unexpected file write 'outbox/84400.json'`, so the task failed despite correct final email content and `seq.json` bump.
- solution_type: rules

## Primary task proposal
- none (no blocking code proposals in selected scope)
