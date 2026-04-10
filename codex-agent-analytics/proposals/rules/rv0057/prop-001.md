# Rules proposal prop-001

- local_run_id: local_run_20260409T234355Z_17384
- rules_version: rv0057
- model: gpt-5.3-codex
- primary_task: t24
- affected_tasks: t24

## Focus
- problem: Task t24 fails with fail_group=one_short_token. The run failed because local rules over-constrained outbound email authorization and forced `OUTCOME_NONE_CLARIFICATION` even after OTP validation granted admin-equivalent authority for this inbox message. Evidence: channel OTP was valid and consumed, instruction contained a concrete recipient email, but the agent blocked on missing `contacts/*.json` mapping and returned clarification instead of executing the required outbox write.
- solution_type: rules

## Primary task proposal
- `t24` fail_group=`one_short_token`
  - hypothesis: If rules distinguish sensitive data-bearing sends from simple admin-authorized direct email drafting, the agent will avoid unnecessary clarification and return `OUTCOME_OK` for executable inbox-email tasks.
  - change: In active local-rules `AGENTS.md`, add a narrow exception near existing outbox authorization bullets: when inbox authority is explicitly elevated by trusted channel policy (including valid OTP exception) and the task provides an explicit concrete `to` email plus literal subject/body, allow creating `outbox/<id>.json` without requiring contact/account mapping. Keep strict contact/account authorization requirements for invoice/data disclosures, cross-account content, or ambiguous recipients.
  - files:
    - `codex-agent-analytics/rules_versions/rv0057/AGENTS.md`: Add one focused precedence bullet block that scopes contact/account-mapping requirements to sensitive or identity-dependent email tasks, while allowing OTP/admin-authorized direct email composition with explicit recipient literals.
  - rollback: Remove the added precedence/exception bullets from `rules_versions/rv0057/AGENTS.md`, restoring prior strict universal mapping behavior.
