# Code proposal prop-031

- local_run_id: local_run_20260405T215418Z_2700233
- code_version: c0001
- model: gpt-5.3-codex
- primary_task: t13
- affected_tasks: t13
- policy: include blocking proposals only

## Focus
- problem: Task t13 fails with fail_group=date_anchor. The failure is an anchor-date selection error, not a sync error. In `tool_calls.jsonl`, `context` returned `2026-11-15T00:00:00Z`, but the agent used `2026-04-05` from session timing and wrote `2026-04-19` instead of expected `2026-11-29`. Account/reminder cross-record alignment was handled correctly; the incorrect anchor drove the wrong result.
- solution_type: rules

## Primary task proposal
- none (no blocking code proposals in selected scope)
