# Rules proposal prop-002

- local_run_id: local_run_20260405T135009Z_2491311
- rules_version: rv0024
- model: gpt-5.3-codex
- primary_task: t32
- affected_tasks: t32

## Focus
- problem: Task t32 fails with fail_group=write_scope. The run failed because it wrote `accounts/acct_002.json`, which the scorer flagged as unexpected. Evidence shows task-scoped audit context asked for a focused fix (`candidate_patch: reminder_only`, `cleanup_later: true`), but the agent followed the broader dual-update rule and edited both account and reminder files.
- solution_type: rules

## Primary task proposal
- `t32` fail_group=`write_scope`
  - hypothesis: Unexpected-write failures occur when default cross-record sync rules are applied even when task-scoped audit metadata explicitly narrows the patch scope and defers cleanup.
  - change: Add a precedence rule: when task-provided audit/context metadata explicitly marks a focused patch scope and deferred cleanup, that scope overrides default reminder-account date synchronization for the current task. Add a pre-write scope gate requiring the agent to derive an allowed write set from instruction plus task-scoped docs, and skip consistency-only writes outside that set.
  - files:
    - `codex-agent-analytics/rules_versions/rv0024/AGENTS.md`: Add concise bullets near follow-up date rules defining scoped-patch precedence and a mandatory allowed-write-set check before first mutation.
  - rollback: Remove the added scoped-patch precedence and allowed-write-set gate bullets from `rules_versions/rv0024/AGENTS.md`.
