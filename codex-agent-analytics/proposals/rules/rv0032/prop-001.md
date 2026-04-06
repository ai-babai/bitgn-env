# Rules proposal prop-001

- local_run_id: local_run_20260405T215418Z_2700233
- rules_version: rv0032
- model: gpt-5.3-codex
- primary_task: t13
- affected_tasks: t13

## Focus
- problem: Task t13 fails with fail_group=date_anchor. The failure is an anchor-date selection error, not a sync error. In `tool_calls.jsonl`, `context` returned `2026-11-15T00:00:00Z`, but the agent used `2026-04-05` from session timing and wrote `2026-04-19` instead of expected `2026-11-29`. Account/reminder cross-record alignment was handled correctly; the incorrect anchor drove the wrong result.
- solution_type: rules

## Primary task proposal
- `t13` fail_group=`date_anchor`
  - hypothesis: If the agent must explicitly read and restate `context.time` as the working anchor before any relative-date mutation, it will avoid accidental use of host/session timestamps and prevent anchor drift.
  - change: Add a compact rule in AGENTS date-handling section: for any instruction with relative time (`in N days/weeks`, `next week`, etc.), call `context` and capture the returned `time` value as the only default anchor; do not use shell/system/session timestamps. If tool payload visibility is limited, re-run with visible output mode before computing dates. Require a pre-write self-check line that states `anchor=<YYYY-MM-DD>, delta=<...>, result=<YYYY-MM-DD>`; if anchor cannot be verified, stop mutations and return clarification.
  - files:
    - `codex-agent-analytics/rules_versions/rv0032/AGENTS.md`: Add 6-10 lines under relative-date rules to mandate verified `context.time` anchoring, prohibit host/session date fallback, and require pre-write anchor/delta/result check.
  - rollback: Revert the added relative-date anchor-check block from `rules_versions/rv0032/AGENTS.md`.
