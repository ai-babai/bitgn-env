# Code proposal prop-002

- local_run_id: local_run_20260403T212858Z_55860
- code_version: c0001
- model: gpt-5.3-codex
- primary_task: t03
- affected_tasks: t03
- policy: include blocking proposals only

## Focus
- problem: Task t03 fails with fail_group=path_typo. The task failed because the required capture write target was `01_capture/influential/...`, but the agent created and wrote `01_capture/influental/...`. Evidence: scorer reported missing write at `01_capture/influential/2026-03-23__hn-agent-kernel-stateful-agents.md`, while tool calls show `mkdir` and `write` under the misspelled directory.
- solution_type: rules

## Primary task proposal
- none (no blocking code proposals in selected scope)
