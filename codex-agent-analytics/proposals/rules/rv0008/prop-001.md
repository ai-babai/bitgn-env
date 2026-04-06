# Rules proposal prop-001

- local_run_id: local_run_20260404T210342Z_78099
- rules_version: rv0008
- model: gpt-5.3-codex
- primary_task: t13
- affected_tasks: t13

## Focus
- problem: Task t13 fails with fail_group=date_anchor. The agent called `context` and got `time=2026-01-08`, but then rescheduled by adding two weeks to the existing overdue field value (`2025-12-31 -> 2026-01-14`) instead of anchoring to runtime "today". Scorer evidence expects `next_follow_up_on=2026-01-22`, which is two weeks from the context date. This is a rules/prompting guidance miss on relative-date anchoring, not a runtime tool limitation.
- solution_type: rules

## Primary task proposal
- `t13` fail_group=`date_anchor`
  - hypothesis: When instructions use relative timing (for example, "in two weeks"), agents can incorrectly anchor to stale record dates unless rules explicitly require using runtime context date as the default anchor.
  - change: Add a concise scheduling rule: for relative-time requests, compute the new date from `context.time` (runtime "today") unless the instruction explicitly names another anchor date; do not anchor to existing overdue `due_on`/`next_follow_up_on` values by default. Keep existing rule to update both reminder and owning account when both carry the follow-up date.
  - files:
    - `codex-agent-analytics/rules_versions/rv0008/AGENTS.md`: Add 3-5 bullets in scheduling/completion guidance defining relative-date anchor precedence (`context.time` first), explicit-anchor override, and consistency updates across reminder/account.
  - rollback: Remove the added relative-date anchor bullets from the active rules AGENTS file.
