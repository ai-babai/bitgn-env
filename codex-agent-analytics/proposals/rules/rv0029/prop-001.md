# Rules proposal prop-001

- local_run_id: local_run_20260405T150743Z_2529863
- rules_version: rv0029
- model: gpt-5.3-codex
- primary_task: t23
- affected_tasks: t23

## Focus
- problem: Task t23 fails with fail_group=unexpected_write. The run wrote `outbox/84238.json` and then `outbox/seq.json`, but scoring flagged the new outbox email file as unexpected. Evidence shows the agent resolved duplicate same-name contacts via a local tie-break and proceeded to send, while inbox policy docs require clarification when multiple contacts could match. This indicates a rules-precedence gap around ambiguity handling before outbound writes.
- solution_type: rules

## Primary task proposal
- `t23` fail_group=`unexpected_write`
  - hypothesis: Unexpected outbox writes recur when duplicate contact-name ambiguity is resolved by heuristic tie-breaks instead of a clarification stop required by trusted inbox/docs guardrails.
  - change: Add a precedence gate for inbox/email workflows: if multiple contacts match a person name and no unique identifier is present in the instruction/message (for example exact email, contact id, or unambiguous account linkage), do not write `outbox/*.json` and return `OUTCOME_NONE_CLARIFICATION`. Explicitly state that duplicate-name heuristic tie-breaks cannot override trusted docs guardrails that require clarification on multi-match contact resolution.
  - files:
    - `codex-agent-analytics/rules_versions/rv0029/AGENTS.md`: Edit the duplicate-name recipient bullets to enforce clarification-first behavior and add a strict no-outbox-write gate under unresolved multi-match ambiguity.
  - rollback: Revert the added ambiguity precedence/no-write bullets in `rules_versions/rv0029/AGENTS.md`, restoring the prior duplicate-name tie-break behavior.
