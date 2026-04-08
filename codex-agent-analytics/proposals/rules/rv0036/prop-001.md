# Rules proposal prop-001

- local_run_id: local_run_20260408T150926Z_4108155
- rules_version: rv0036
- model: gpt-5.3-codex
- primary_task: t23
- affected_tasks: t23

## Focus
- problem: Task t23 fails with fail_group=unexpected_writes. The run correctly handled `inbox/msg_001.txt` first, but then continued processing later inbox items and performed extra mutations (`outbox/84515.json` write+delete and additional `outbox/seq.json` writes). Scoring is mutation-history based, so rollback did not remove the penalty. The missing guard is a strict one-item queue boundary after first-item resolution.
- solution_type: rules

## Primary task proposal
- `t23` fail_group=`unexpected_writes`
  - hypothesis: If queue-mode inbox tasks explicitly lock execution to the lowest pending message and require immediate finalization after that item is resolved, agents will avoid speculative/rollback writes on later messages and eliminate unexpected-write failures.
  - change: Add a compact inbox-queue rule: for instructions like process/work through inbox queue, select the lowest pending `inbox/msg_*.txt` as the only actionable item for the run. Build writes only for artifacts required by that item. After those writes are complete, immediately `report_completion`; do not write/delete artifacts for later inbox messages and do not perform rollback cleanup writes to `outbox/seq.json` or additional outbox IDs in the same run.
  - files:
    - `codex-agent-analytics/rules_versions/rv0036/AGENTS.md`: Add a 6-10 line queue-boundary gate in inbox workflow/completion guidance enforcing one actionable inbox item per run and prohibiting later-item/rollback mutations.
  - rollback: Remove the added inbox queue-boundary bullets from `rules_versions/rv0036/AGENTS.md`.
