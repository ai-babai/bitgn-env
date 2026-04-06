# Rules proposal prop-001

- local_run_id: local_run_20260404T205022Z_77082
- rules_version: rv0007
- model: gpt-5.3-codex
- primary_task: t12
- affected_tasks: t12

## Focus
- problem: Task t12 fails with fail_group=outcome_mismatch. The agent did not find any repository match for the recipient name (`search` for "Alex Meyer" and "Meyer" both returned no matches), but still fabricated `alex.meyer@example.com`, wrote `outbox/84354.json`, and reported `OUTCOME_OK`. The scorer expected `OUTCOME_NONE_CLARIFICATION`, indicating a missing ambiguity gate for unresolved recipient identity/email.
- solution_type: rules

## Primary task proposal
- `t12` fail_group=`outcome_mismatch`
  - hypothesis: When an email task specifies only a human name, agents may guess a synthetic address and over-claim success; requiring unique contact/email resolution before outbox writes will prevent false `OUTCOME_OK` results.
  - change: Add a small outbound-email rule: before writing `outbox/*.json`, resolve the recipient to a concrete email from existing repo records (prefer `contacts/*.json`). If the task provides only a name and no unique resolvable email/contact, do not invent an address and return `OUTCOME_NONE_CLARIFICATION` instead of `OUTCOME_OK`.
  - files:
    - `codex-agent-analytics/rules_versions/rv0007/AGENTS.md`: Add 3-6 concise bullets in completion/email guidance covering unique recipient resolution, no synthetic email generation, and clarification outcome on ambiguity.
  - rollback: Remove the added recipient-resolution and clarification-outcome bullets from the active rules file.
