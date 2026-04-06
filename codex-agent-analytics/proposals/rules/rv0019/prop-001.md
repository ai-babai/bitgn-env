# Rules proposal prop-001

- local_run_id: local_run_20260405T105916Z_2421379
- rules_version: rv0019
- model: gpt-5.3-codex
- primary_task: t26
- affected_tasks: t26

## Focus
- problem: Task t26 fails with fail_group=write_redundancy. The run failed because `outbox/84207.json` was written twice in one task. Tool traces show a malformed first JSON write (escaped quotes) followed by a corrective rewrite to the same path, and the scorer flagged this as `unexpected file write 'outbox/84207.json'`.
- solution_type: rules

## Primary task proposal
- `t26` fail_group=`write_redundancy`
  - hypothesis: Unexpected-write failures recur when a malformed first JSON write triggers a corrective rewrite to the same file; forcing pre-write payload validation and aborting instead of rewriting prevents this class of failures.
  - change: Add a concise high-priority rule: before any `write` to `*.json`, finalize literal JSON payload and verify it has no escaped-quote artifacts; execute exactly one write per target path; if a first attempt would need correction, do not rewrite that path and exit with a non-OK outcome instead of mutating again.
  - files:
    - `codex-agent-analytics/rules_versions/rv0019/AGENTS.md`: Add 3-5 bullets in the write-discipline section that make same-path JSON corrective rewrites a hard stop and require pre-write payload validation.
  - rollback: Remove the added JSON pre-write/abort bullets from `rules_versions/rv0019/AGENTS.md`.
