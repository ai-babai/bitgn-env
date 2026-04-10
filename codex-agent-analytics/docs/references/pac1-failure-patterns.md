# PAC1 Failure Patterns

Purpose: reusable failure archetypes for analyze/apply cycles.

## Pattern: identity-ambiguity-outcome-ok

- Symptom: solver emits `OUTCOME_OK` when sender identity is unresolved or mismatch exists.
- Typical score detail: expected `OUTCOME_NONE_CLARIFICATION` or `OUTCOME_DENIED_SECURITY`, got `OUTCOME_OK`.
- Preferred fix type: rules/harness decision matrix and pre-mutation gate.

## Pattern: relative-date-system-drift

- Symptom: solver calls `context` but computes result from ambient date.
- Typical score detail: incorrect date answer for relative expression.
- Preferred fix type: temporal anchor policy with mandatory self-check.

## Pattern: truncated-instruction-mutation

- Symptom: truncated command still leads to mutations and `OUTCOME_OK`.
- Typical score detail: expected clarification outcome.
- Preferred fix type: ambiguity gate before any write/delete.
