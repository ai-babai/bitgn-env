# Rules proposal prop-001

- local_run_id: local_run_20260405T141258Z_2504781
- rules_version: rv0026
- model: gpt-5.3-codex
- primary_task: t32
- affected_tasks: t32

## Focus
- problem: Task t32 fails with fail_group=missing_account_write. The run updated only `reminders/rem_005.json` and reported success, but scoring required a write to `accounts/acct_005.json`. Evidence shows root `AGENTS.md` explicitly requires updating both reminder and owning account when both carry the follow-up date, and both records were read with matching date fields before mutation. The failure is a harness-rule precedence issue, not a runtime/tooling limitation.
- solution_type: rules

## Primary task proposal
- `t32` fail_group=`missing_account_write`
  - hypothesis: If local rules treat task-scoped audit hints as advisory unless explicitly marked authoritative by trusted policy, agents will preserve required reminder-account date alignment and avoid under-scoped writes.
  - change: In follow-up reschedule guidance, replace the current scoped-audit precedence bullet with a stricter rule: advisory audit/context fields (for example candidate patch or deferred cleanup hints) cannot override mandatory cross-record invariants from root policy and schema docs. Add a pre-write gate for follow-up date changes: when both owning account and reminder contain the workflow date field, include both files in the allowed write set and update them in one focused patch.
  - files:
    - `codex-agent-analytics/rules_versions/rv0026/AGENTS.md`: Edit the follow-up precedence section to demote advisory audit scope hints and enforce dual-record sync when both account and reminder store the date.
  - rollback: Revert the follow-up precedence edit in `rules_versions/rv0026/AGENTS.md` to restore prior scoped-audit override behavior.
