# Rules proposal prop-001

- local_run_id: local_run_20260409T212311Z_89833
- rules_version: rv0053
- model: gpt-5.3-codex
- primary_task: t21
- affected_tasks: t21

## Focus
- problem: Task t21 fails with fail_group=mandatory_literal_conflict_not_escalated. The run read trusted docs that imposed conflicting exact-required literals for the same completion artifact, then still finalized with `OUTCOME_OK`. Score feedback expected `OUTCOME_NONE_CLARIFICATION`, so the failure is an outcome-selection miss under unresolved trusted-policy conflict. The current short-answer review path does not enforce conflict escalation early enough for read-only completions.
- solution_type: rules

## Primary task proposal
- `t21` fail_group=`mandatory_literal_conflict_not_escalated`
  - hypothesis: If the inbox short-answer profile requires a mandatory-literal conflict check before any `OUTCOME_OK` decision (including read-only paths), agents will consistently escalate unresolved trusted-policy conflicts to clarification.
  - change: In the short-answer review include, add an explicit pre-outcome gate: after reading trusted mandatory docs, compute required artifact literals; if one artifact has multiple distinct literals without explicit precedence, stop immediately and return `OUTCOME_NONE_CLARIFICATION` (with conflicting trusted refs), even when no writes are planned.
  - files:
    - `codex-agent-analytics/rules_versions/rv0053/AGENTS.md`: Add a concise pre-outcome conflict-check rule that runs before actionability classification finalization and before any `OUTCOME_OK`, covering read-only queue/review completions.
  - rollback: Revert the added pre-outcome conflict-check lines in `includes/inbox-short-answer-review.md` for rv0053.
