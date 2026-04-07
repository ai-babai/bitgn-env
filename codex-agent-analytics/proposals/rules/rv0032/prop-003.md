# Rules proposal prop-003

- local_run_id: local_run_20260406T162342Z_3061888
- rules_version: rv0032
- model: gpt-5.3-codex
- primary_task: t17
- affected_tasks: t17

## Focus
- problem: Task t17 fails with fail_group=write_redundancy. The run completed the email content correctly, but it wrote `outbox/seq.json` twice. In `tool_calls.jsonl`, step 26 bumps `seq.json` to the correct next id, then step 28 rewrites the same file with formatting-only change, which the scorer reports as `unexpected file write 'outbox/seq.json'`. This indicates a rules-discipline gap around post-validation rewrite lock, not a runtime code blocker.
- solution_type: rules

## Primary task proposal
- `t17` fail_group=`write_redundancy`
  - hypothesis: Unexpected-write failures recur when a valid `outbox/seq.json` bump is followed by a cosmetic second write during verification.
  - change: Add a strict outbox sequencing rule: after one successful write to `outbox/seq.json` (id increment validated by read-back), mark that path write-locked for the remainder of the task. Require all post-bump checks to be read-only and explicitly forbid formatting/newline normalization rewrites once semantic validity is confirmed.
  - files:
    - `codex-agent-analytics/rules_versions/rv0032/AGENTS.md`: Add concise bullets in JSON/outbox write-discipline section to prohibit any second write to `outbox/seq.json` after a validated increment.
  - rollback: Remove the added outbox `seq.json` write-lock bullets from `rules_versions/rv0032/AGENTS.md`, restoring previous behavior.
