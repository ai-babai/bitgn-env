# Rules proposal prop-001

- local_run_id: local_run_20260405T122453Z_2465862
- rules_version: rv0024
- model: gpt-5.3-codex
- primary_task: t26
- affected_tasks: t26

## Focus
- problem: Task t26 fails with fail_group=write_redundancy. Tool traces show two writes to the same new file path (`outbox/84400.json`): an initial escaped-quote JSON write followed by a corrective rewrite. The scorer then reported `unexpected file write 'outbox/84400.json'`, so the task failed despite correct final email content and `seq.json` bump.
- solution_type: rules

## Primary task proposal
- `t26` fail_group=`write_redundancy`
  - hypothesis: Unexpected-write failures recur when multiline JSON is passed via shell-escaped inline `content=...`, causing malformed first writes and corrective rewrites on the same new outbox file.
  - change: Add a strict outbox JSON write rule: for creating new `outbox/<number>.json`, pass write args via a transport-safe JSON object to `runtime_tools.py write` (stdin/object form), not inline shell-escaped multiline `content="..."`. Keep preflight validation before first write and enforce one-pass create semantics for new outbox numbered files; if validation fails after creation, do not rewrite that same path and finish with a non-OK outcome.
  - files:
    - `codex-agent-analytics/rules_versions/rv0024/AGENTS.md`: Add 4-6 bullets in the JSON/outbox write section defining transport-safe invocation for JSON payloads and one-pass create behavior for new outbox numbered files.
  - rollback: Remove the added transport-safe invocation and one-pass outbox-create bullets from `rules_versions/rv0024/AGENTS.md`.
