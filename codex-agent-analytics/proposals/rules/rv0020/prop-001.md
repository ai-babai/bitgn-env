# Rules proposal prop-001

- local_run_id: local_run_20260405T112755Z_2432565
- rules_version: rv0020
- model: gpt-5.3-codex
- primary_task: t30
- affected_tasks: t30

## Focus
- problem: Task t30 fails with fail_group=one_short_token. The agent submitted `804` while the scorer expected `805`. Run evidence shows it computed `805` blacklist records first, then switched to a deduplicated unique-account interpretation (`805 804 1`) and answered the smaller number without an instruction to count distinct accounts.
- solution_type: rules

## Primary task proposal
- `t30` fail_group=`one_short_token`
  - hypothesis: When prompts ask "how many" over status logs, implicit deduplication can undercount if the intended unit is records/events; requiring explicit unit selection prevents one-off numeric misses.
  - change: Add a counting rule: infer the unit from user wording and source structure before finalizing numeric answers. Default to counting matching records/lines for status-log questions; only switch to unique-entity counting when the prompt explicitly says unique/distinct/per-account. If raw-match and unique counts differ and no distinct cue is present, return the raw-match count.
  - files:
    - `codex-agent-analytics/rules_versions/rv0020/AGENTS.md`: Add concise completion/counting bullets that require explicit count-unit selection and forbid implicit deduplication unless explicitly requested.
  - rollback: Remove the added counting-semantics bullets from `rules_versions/rv0020/AGENTS.md`.
