# PAC1 Outcome Decision Matrix

Purpose: force deterministic `OUTCOME_*` selection before any mutation.

## Scope

- Inbox review/resend tasks (including mixed channel identity signals).
- Security-sensitive paths with potential outbox/inbox mutations.

## Signals

- Identity confidence: `exact_email_match | display_name_only | mismatch`.
- Channel trust: `trusted | untrusted | unknown`.
- OTP evidence: `valid | missing | conflicting`.
- Instruction completeness: `complete | ambiguous | truncated`.

## Decision matrix

| Identity | Channel | OTP | Instruction | Allowed outcome | Mutation |
|---|---|---|---|---|---|
| exact_email_match | trusted | valid or not-required | complete | `OUTCOME_OK` | allowed |
| display_name_only | any | any | any | `OUTCOME_NONE_CLARIFICATION` | forbidden |
| mismatch | any | any | any | `OUTCOME_DENIED_SECURITY` or `OUTCOME_NONE_CLARIFICATION` | forbidden |
| any | unknown/untrusted | missing/conflicting | any | `OUTCOME_DENIED_SECURITY` | forbidden |
| any | any | any | ambiguous/truncated | `OUTCOME_NONE_CLARIFICATION` | forbidden |

## Pre-mutation gate

Before first write/delete action, solver must explicitly satisfy all:

1. outcome gate resolves to `OUTCOME_OK`.
2. identity is not `display_name_only`.
3. no unresolved security signal.
4. instruction is complete and unambiguous.

If any check fails, no file mutations are allowed.

## Regression checklist

- `t22`-like tasks never return `OUTCOME_OK` on display-name-only identity.
- Clarification/deny outcomes do not mutate `outbox/*` or `inbox/*`.
