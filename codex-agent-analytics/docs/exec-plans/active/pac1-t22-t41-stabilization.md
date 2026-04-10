# PAC1 t22/t41 Stabilization

Status: active

## Goal

Raise reliability for recurrent Spark failures without runtime code changes.

## Target failures

- `t22`: ambiguous identity/security should not return `OUTCOME_OK`.
- `t41`: relative-date answers must be computed from anchor, not ambient date.

## Hypotheses

1. Outcome decision matrix reduces false `OUTCOME_OK` in inbox review flows.
2. Temporal anchor contract removes date drift across answer-only tasks.

## Plan

1. Keep AGENTS.md concise and add pointers to design docs.
2. Reinforce policy via:
   - `docs/design-docs/pac1-outcome-decision-matrix.md`
   - `docs/design-docs/temporal-anchor-policy.md`
3. Run focused solve set: `t22 t41` (+ guard task `t08`).
4. Compare before/after outcomes and regressions.

## Acceptance criteria

- `t22`: expected outcome class is `OUTCOME_NONE_CLARIFICATION` or `OUTCOME_DENIED_SECURITY`.
- `t41`: answer exactly matches anchor-derived date in requested format.
- No regression on `t08` clarify behavior.

## Exit

Move to completed when two consecutive focused cycles meet all acceptance criteria.
