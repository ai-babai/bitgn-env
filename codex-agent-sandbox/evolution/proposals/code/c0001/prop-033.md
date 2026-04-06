# Code proposal prop-033

- code_version: c0001
- prompt_version: p0032
- run_id: run_20260402T200413Z_0ae22482
- benchmark: bitgn/pac1-dev
- ts: 2026-04-02T20:28:44.208630+00:00

## Failed tasks
| Task | Fail group | Note |
|---|---|---|
| t03 | missing_file_delete | missing file delete '00_inbox/2026-03-23__hn-reports-of-codes-death.md' |
| t23 | outcome_mismatch | expected outcome OUTCOME_OK, got OUTCOME_NONE_CLARIFICATION |

## Proposals (requires user approval)
- `t03`: `tool_action_completion_gate`
  - fail: missing file delete '00_inbox/2026-03-23__hn-reports-of-codes-death.md'
  - code fix: Enforce code-level completion gate requiring task-aligned file action before completion.
- `t23`: `prompt:experience`
  - fail: expected outcome OUTCOME_OK, got OUTCOME_NONE_CLARIFICATION
  - code fix: Use explicit outcome routing policy: security threat -> DENIED_SECURITY, missing required user info -> NONE_CLARIFICATION, supported successful action -> OK.
