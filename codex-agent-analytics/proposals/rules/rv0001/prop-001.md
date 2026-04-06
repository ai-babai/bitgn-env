# Rules proposal prop-001

- local_run_id: local_run_20260403T212858Z_55860
- rules_version: rv0001
- model: gpt-5.3-codex
- primary_task: t03
- affected_tasks: t03

## Focus
- problem: Task t03 fails with fail_group=path_typo. The run failed because the required capture write path was `01_capture/influential/...`, but the agent created and used `01_capture/influental/...` instead. Evidence: score detail reports missing write to `01_capture/influential/2026-03-23__hn-agent-kernel-stateful-agents.md`, and tool calls show `mkdir`/`write` under the misspelled directory.
- solution_type: rules

## Primary task proposal
- `t03` fail_group=`path_typo`
  - hypothesis: Failures occur when agents create near-match directory names instead of reusing existing canonical buckets; explicit exact-path checks before completion will catch these typos.
  - change: Add a rule requiring agents to enumerate existing destination directories before writing and to reuse exact names when a matching bucket already exists. Add a final verification step that compares required write targets to actual written paths and blocks completion on near-match typos.
  - files:
    - `codex-agent-analytics/rules_versions/rv0001/AGENTS.md`: Add concise workflow bullets for exact destination-name reuse and mandatory pre-completion path verification for required outputs.
  - rollback: Remove the added exact-path and pre-completion verification bullets from the rules file.
