# Rules proposal prop-002

- local_run_id: local_run_20260409T140110Z_18813
- rules_version: rv0039
- model: gpt-5.3-codex-spark
- primary_task: t26
- affected_tasks: t26

## Focus
- problem: Task t26 fails with fail_group=one_short_token. The requested email draft was written to `outbox/84968.json`, but scoring failed on `outbox/seq.json` JSON validity. In `tool_calls.jsonl` step 23, the write payload is logged as `{\n  "id": 84969\n}`, which is invalid JSON and matches the evaluator error `invalid character '\\' looking for beginning of object key string`.
- solution_type: rules

## Primary task proposal
- `t26` fail_group=`one_short_token`
  - hypothesis: If JSON write arguments are required to be raw JSON text and validated before each dependent write, agents will stop emitting escaped structural artifacts that corrupt `outbox/seq.json` and similar sequencing files.
  - change: Update the active rules AGENTS to add an explicit JSON write guard: for any `write` to `*.json` (especially `outbox/<id>.json` and `outbox/seq.json`), require final payload content to be raw JSON syntax (no escaped newlines/quotes that indicate serialized JSON strings), and require an immediate read/parse validation before the next write in the same artifact transaction. If validation fails, stop and do not proceed to `outbox/seq.json`.
  - files:
    - `codex-agent-analytics/rules_versions/rv0039/AGENTS.md`: Add a concise preflight rule in the existing JSON/write discipline section: ban escaped structural characters in write payloads, require parse validation immediately after each `*.json` write, and abort dependent writes on parse failure.
  - rollback: Remove the added JSON write-serialization guard bullets from `rules_versions/rv0039/AGENTS.md`, restoring prior write guidance.
