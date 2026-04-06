# Rules proposal prop-001

- local_run_id: local_run_20260405T161316Z_2570309
- rules_version: rv0030
- model: gpt-5.3-codex
- primary_task: t23
- affected_tasks: t23

## Focus
- problem: Task t23 fails with fail_group=outcome_mismatch. The run returned `OUTCOME_NONE_CLARIFICATION` while scoring expected `OUTCOME_OK`. Evidence shows the agent stopped immediately on duplicate same-name contacts because active rules explicitly forbid tie-break disambiguation, even for routine inbox outreach where repository workflow/account signals can reduce to a single recipient.
- solution_type: rules

## Primary task proposal
- `t23` fail_group=`outcome_mismatch`
  - hypothesis: If duplicate-name recipient handling requires a deterministic repository-evidence disambiguation pass before clarification, the agent will avoid false `OUTCOME_NONE_CLARIFICATION` on resolvable inbox outreach tasks.
  - change: Revise the duplicate-recipient bullets so clarification is a post-disambiguation fallback, not an immediate stop. Require a deterministic pass using message workflow cues plus contact->account linkage and account/notes metadata; proceed only when exactly one candidate remains, otherwise return `OUTCOME_NONE_CLARIFICATION`. Keep existing strict security gates for sensitive data-transfer/invoice flows unchanged.
  - files:
    - `codex-agent-analytics/rules_versions/rv0030/AGENTS.md`: Replace the current 'no tie-break on multi-match name' wording with a short two-step rule: deterministic disambiguation first, clarification only if unresolved.
  - rollback: Revert the edited duplicate-recipient bullets in `rules_versions/rv0030/AGENTS.md` to restore immediate clarification on any same-name multi-match.
