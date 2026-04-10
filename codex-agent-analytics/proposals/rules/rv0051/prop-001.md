# Rules proposal prop-001

- local_run_id: local_run_20260409T205021Z_87691
- rules_version: rv0051
- model: gpt-5.3-codex
- primary_task: t21
- affected_tasks: t21

## Focus
- problem: Task t21 fails with fail_group=mandatory_literal_conflict_not_escalated. The run read two trusted mandatory docs that require different exact literals for the same artifact (`result.txt`): `FINISHED` vs `DONE`, but still proceeded with a queue mutation and reported `OUTCOME_OK`. For this ambiguity class, the expected behavior is `OUTCOME_NONE_CLARIFICATION` before any write, so the current conflict gate is not deterministic enough in practice.
- solution_type: rules

## Primary task proposal
- `t21` fail_group=`mandatory_literal_conflict_not_escalated`
  - hypothesis: If inbox short-answer/review flow performs an explicit pre-write conflict scan over trusted mandatory requirements keyed by target artifact path and exact literal, then ambiguous precedence cases will consistently route to clarification instead of false `OUTCOME_OK`.
  - change: Update the inbox short-answer include with a strict gate: (1) extract trusted mandatory requirements as `target_path + exact_required_literal`; (2) if one `target_path` has multiple distinct literals and no explicit precedence source, stop workflow before any mutation; (3) return `OUTCOME_NONE_CLARIFICATION` with a minimal precedence question; (4) require conflicting mandatory sources in `grounding_refs` and forbid `OUTCOME_OK` until precedence is resolved.
  - files:
    - `codex-agent-analytics/rules_versions/rv0051/AGENTS.md`: Add a compact 'required-artifact literal conflict' subsection under Actionability gate with deterministic trigger and outcome constraints.
  - rollback: Revert the added conflict-gate subsection in the include file.
