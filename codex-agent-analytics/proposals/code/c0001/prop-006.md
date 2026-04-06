# Code proposal prop-006

- local_run_id: local_run_20260404T205022Z_77082
- code_version: c0001
- model: gpt-5.3-codex
- primary_task: t12
- affected_tasks: t12
- policy: include blocking proposals only

## Focus
- problem: Task t12 fails with fail_group=outcome_mismatch. The agent did not find any repository match for the recipient name (`search` for "Alex Meyer" and "Meyer" both returned no matches), but still fabricated `alex.meyer@example.com`, wrote `outbox/84354.json`, and reported `OUTCOME_OK`. The scorer expected `OUTCOME_NONE_CLARIFICATION`, indicating a missing ambiguity gate for unresolved recipient identity/email.
- solution_type: rules

## Primary task proposal
- none (no blocking code proposals in selected scope)
