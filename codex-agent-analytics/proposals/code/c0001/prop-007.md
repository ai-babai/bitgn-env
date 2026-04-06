# Code proposal prop-007

- local_run_id: local_run_20260404T210342Z_78099
- code_version: c0001
- model: gpt-5.3-codex
- primary_task: t13
- affected_tasks: t13
- policy: include blocking proposals only

## Focus
- problem: Task t13 fails with fail_group=date_anchor. The agent called `context` and got `time=2026-01-08`, but then rescheduled by adding two weeks to the existing overdue field value (`2025-12-31 -> 2026-01-14`) instead of anchoring to runtime "today". Scorer evidence expects `next_follow_up_on=2026-01-22`, which is two weeks from the context date. This is a rules/prompting guidance miss on relative-date anchoring, not a runtime tool limitation.
- solution_type: rules

## Primary task proposal
- none (no blocking code proposals in selected scope)
