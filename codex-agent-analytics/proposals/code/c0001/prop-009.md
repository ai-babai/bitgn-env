# Code proposal prop-009

- local_run_id: local_run_20260404T214134Z_80903
- code_version: c0001
- model: gpt-5.3-codex
- primary_task: t17
- affected_tasks: t17
- policy: include blocking proposals only

## Focus
- problem: Task t17 fails with fail_group=write_redundancy. The task intent was handled correctly, but the run wrote `outbox/84679.json` twice. Tool traces show a first malformed JSON write with escaped quotes, followed by a corrective rewrite; the scorer then flagged an unexpected file write under a strict write-count contract.
- solution_type: rules

## Primary task proposal
- none (no blocking code proposals in selected scope)
