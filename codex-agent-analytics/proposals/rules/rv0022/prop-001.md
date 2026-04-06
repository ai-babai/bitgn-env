# Rules proposal prop-001

- local_run_id: local_run_20260405T114558Z_2444197
- rules_version: rv0022
- model: gpt-5.3-codex
- primary_task: t26
- affected_tasks: t26

## Focus
- problem: Task t26 fails with fail_group=outcome_mismatch. The run produced malformed JSON in both `outbox/84027.json` and `outbox/seq.json` by writing escaped quote artifacts (`\"`) on first write, then reported `OUTCOME_NONE_UNSUPPORTED` instead of completing the requested outbox action. Evidence is in `tool_calls.jsonl` write args and post-write reads showing escaped content. This is a behavior/rules-execution reliability issue, not a proven runtime capability gap, because other runs of the same task pattern wrote valid JSON and passed.
- solution_type: rules

## Primary task proposal
- `t26` fail_group=`outcome_mismatch`
  - hypothesis: Malformed `*.json` outputs recur when the agent composes write payloads with pre-escaped quotes; under single-write constraints this converts a recoverable formatting mistake into hard task failure.
  - change: Add a short mandatory preflight rule for every `*.json` write: finalize payload in literal JSON form (no `\"` artifacts), perform a pre-write escape scan, and only then execute the first write. For multi-file outbox updates, require sequential gating: validate email payload first, then validate and write `seq.json`; never issue both JSON writes before payload preflight passes.
  - files:
    - `codex-agent-analytics/rules_versions/rv0022/AGENTS.md`: Insert a concise preflight checklist near existing JSON write constraints to enforce literal-JSON payload validation before any `write`, plus ordered gating for outbox email/seq writes.
  - rollback: Remove the added preflight and ordered-gating bullets from `rules_versions/rv0022/AGENTS.md`, restoring previous JSON write guidance.
