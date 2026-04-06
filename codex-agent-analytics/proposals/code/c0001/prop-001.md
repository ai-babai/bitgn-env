# Code proposal prop-001

- local_run_id: local_run_20260403T212858Z_55860
- code_version: c0001
- model: gpt-5.3-codex
- primary_task: t03
- affected_tasks: t03
- policy: include blocking proposals only

## Focus
- problem: Task t03 fails with fail_group=path_typo. The run failed because the required capture write path was `01_capture/influential/...`, but the agent created and used `01_capture/influental/...` instead. Evidence: score detail reports missing write to `01_capture/influential/2026-03-23__hn-agent-kernel-stateful-agents.md`, and tool calls show `mkdir`/`write` under the misspelled directory.
- solution_type: rules

## Primary task proposal
- none (no blocking code proposals in selected scope)
