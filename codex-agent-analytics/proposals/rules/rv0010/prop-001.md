# Rules proposal prop-001

- local_run_id: local_run_20260404T214134Z_80903
- rules_version: rv0010
- model: gpt-5.3-codex
- primary_task: t17
- affected_tasks: t17

## Focus
- problem: Task t17 fails with fail_group=write_redundancy. The task intent was handled correctly, but the run wrote `outbox/84679.json` twice. Tool traces show a first malformed JSON write with escaped quotes, followed by a corrective rewrite; the scorer then flagged an unexpected file write under a strict write-count contract.
- solution_type: rules

## Primary task proposal
- `t17` fail_group=`write_redundancy`
  - hypothesis: Unexpected-write failures recur when agents perform corrective rewrites after avoidable malformed first writes; enforcing a pre-write JSON payload check prevents second writes.
  - change: Tighten write discipline for JSON targets: before any `write`, prepare the exact final payload in literal JSON form, verify it has unescaped field quotes (no `\\\"` key/value artifacts), and execute exactly one write per target path. If uncertain, re-check schema/README before writing rather than fixing the same file with a second write.
  - files:
    - `codex-agent-analytics/rules_versions/rv0010/AGENTS.md`: Add 2-4 concise bullets refining the existing single-pass rule with an explicit pre-write JSON validity/escaping check and a no-corrective-rewrite constraint.
  - rollback: Remove the added pre-write JSON gate bullets and revert to the prior single-pass wording.
