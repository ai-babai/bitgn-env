# Rules proposal prop-001

- local_run_id: local_run_20260405T114558Z_2444194
- rules_version: rv0021
- model: gpt-5.3-codex
- primary_task: t23
- affected_tasks: t23

## Focus
- problem: Task t23 fails with fail_group=outcome_mismatch. The run returned `OUTCOME_NONE_CLARIFICATION` instead of the expected `OUTCOME_OK`. Evidence shows the agent stopped at duplicate full-name matching in `contacts/` and did not apply account-level disambiguation, even though a passing `t23` run resolved the same pattern by using workflow/account signals and proceeded with an outbox write. The current rule set over-triggers clarification for name collisions that are still deterministically resolvable.
- solution_type: rules

## Primary task proposal
- `t23` fail_group=`outcome_mismatch`
  - hypothesis: When an inbox outreach request names a person and multiple contacts share that name, immediate clarification is unnecessary if account-level workflow markers can deterministically select one candidate; adding a required tie-breaker step will reduce false clarification outcomes.
  - change: Refine recipient-resolution rules before `OUTCOME_NONE_CLARIFICATION`: for duplicate name matches, require a deterministic tie-break pass using repository signals (account flags/metadata, workflow cues in message text, and contact-account linkage). If exactly one candidate remains after this pass, proceed with outbox write; request clarification only when ambiguity remains after tie-breakers.
  - files:
    - `codex-agent-analytics/rules_versions/rv0021/AGENTS.md`: Replace the strict 'name-only ambiguity => clarification' bullet with a short two-step rule: mandatory deterministic tie-break by account/workflow signals first, clarification only if unresolved.
  - rollback: Revert the added tie-breaker bullets in `rules_versions/rv0021/AGENTS.md`, restoring immediate-clarification behavior on duplicate-name matches.
