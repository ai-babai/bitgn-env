# Code proposal prop-016

- local_run_id: local_run_20260405T100531Z_2402126
- code_version: c0001
- model: gpt-5.3-codex
- primary_task: t21
- affected_tasks: t21
- policy: include blocking proposals only

## Focus
- problem: Task t21 fails with fail_group=policy_conflict. The run read two mandatory completion-policy docs that required incompatible literals for the same output file, then proceeded with one branch and returned OUTCOME_OK. Scoring expected OUTCOME_NONE_CLARIFICATION, which indicates a missing ambiguity gate for conflicting policy directives. Evidence is in tool calls reading both docs and then writing `result.txt` without clarifying precedence.
- solution_type: rules

## Primary task proposal
- none (no blocking code proposals in selected scope)
