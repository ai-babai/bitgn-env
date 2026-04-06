# Code proposal prop-028

- local_run_id: local_run_20260405T150743Z_2529863
- code_version: c0001
- model: gpt-5.3-codex
- primary_task: t23
- affected_tasks: t23
- policy: include blocking proposals only

## Focus
- problem: Task t23 fails with fail_group=unexpected_write. The run wrote `outbox/84238.json` and then `outbox/seq.json`, but scoring flagged the new outbox email file as unexpected. Evidence shows the agent resolved duplicate same-name contacts via a local tie-break and proceeded to send, while inbox policy docs require clarification when multiple contacts could match. This indicates a rules-precedence gap around ambiguity handling before outbound writes.
- solution_type: rules

## Primary task proposal
- none (no blocking code proposals in selected scope)
