# Rules proposal prop-001

- local_run_id: local_run_20260409T145634Z_32649
- rules_version: rv0043
- model: gpt-5.3-codex
- primary_task: t41
- affected_tasks: t41

## Focus
- problem: Task t41 fails with fail_group=one_short_token. The run called `context` and the tool trace recorded `time=2026-03-18T00:00:00Z`, but the submission was `2026-04-10` while scoring expected `2026-03-19`. Session output shows only `TOOL_OK` text for tool commands, and the agent explicitly stated it saw status-only outputs, then computed the date from a non-anchor source. The failure is a harness guidance gap: no explicit high-priority rule to force payload-visible tool execution before relative-date answers.
- solution_type: rules

## Primary task proposal
- `t41` fail_group=`one_short_token`
  - hypothesis: If rules require a payload-visible `context` read before any relative-date answer, the agent will stop using ambient/system date and consistently compute from the runtime anchor.
  - change: In active rules `AGENTS.md`, add a short high-priority guard: when a decision depends on tool payload (`context`, `read`, `list`, `find`, `search`), run with payload-visible logging (e.g., `NATIVE_LOG_LEVEL=debug`) and do not finalize if command output is status-only. For relative-date prompts, require explicit `anchor=<YYYY-MM-DD> expression=<phrase> result=<YYYY-MM-DD>` self-check from `context.time` immediately before `report_completion`.
  - files:
    - `codex-agent-analytics/rules_versions/rv0043/AGENTS.md`: Add a compact 6-10 line 'tool payload visibility + relative-date anchor check' block near completion rules, forcing retry-with-debug on status-only outputs and mandatory anchor/result self-check before final answer.
  - rollback: Remove the added guard block from `rules_versions/rv0043/AGENTS.md` in the next rules version if it causes regressions.
