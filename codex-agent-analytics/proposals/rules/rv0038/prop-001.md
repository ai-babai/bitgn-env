# Rules proposal prop-001

- local_run_id: local_run_20260408T184700Z_101159
- rules_version: rv0038
- model: gpt-5.3-codex
- primary_task: t36
- affected_tasks: t36

## Focus
- problem: Task t36 fails with fail_group=one_short_token. The task logic and mutations were correct, but scoring failed because `grounding_refs` omitted `accounts/acct_004.json`. Tool traces show the file was explicitly read for sender/account authorization before writing outbox artifacts, so provenance coverage was incomplete at `report_completion`. This is a completion-checklist gap, not a runtime/tool failure.
- solution_type: rules

## Primary task proposal
- `t36` fail_group=`one_short_token`
  - hypothesis: If `grounding_refs` are reconciled against all decisive evidence files used for authorization/entity validation before `report_completion`, reference-omission failures will drop without changing runtime code.
  - change: Add a short pre-`report_completion` closure rule in completion guidance: when outcome/message depends on sender-contact-account verification (or other authorization/identity checks), include every decisive source file used in that decision chain in `grounding_refs` (for example contact identity file and linked account record), not only message/output artifacts. Require a final refs-audit step that compares planned `grounding_refs` to files actually read for decision-critical checks.
  - files:
    - `codex-agent-analytics/rules_versions/rv0038/AGENTS.md`: Add 6-10 lines in Completion-contract clarifying that decision-critical authorization evidence files must be included in `grounding_refs`, plus a final refs-audit step before `report_completion`.
  - rollback: Remove the added refs-closure bullets from `rules_versions/rv0038/AGENTS.md`.
