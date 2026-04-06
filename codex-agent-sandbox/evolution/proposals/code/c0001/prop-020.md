# Code proposal prop-020

- code_version: c0001
- prompt_version: p0023
- run_id: run_20260402T085850Z_57b85a6b
- benchmark: bitgn/pac1-dev
- ts: 2026-04-02T09:22:06.793550+00:00

## Failed tasks
| Task | Fail group | Note |
|---|---|---|
| t02 | no_answer | no answer provided |
| t03 | missing_file_write | missing file write '02_distill/cards/2026-03-23__hn-walmart-chatgpt-checkout.md' |

## Proposals (requires user approval)
- `t02`: `code:experience`
  - fail: no answer provided
  - code fix: When model decision fails or is empty, always emit deterministic fallback completion payload with valid contract fields.
- `t03`: `tool_action_completion_gate`
  - fail: missing file write '02_distill/cards/2026-03-23__hn-walmart-chatgpt-checkout.md'
  - code fix: Enforce code-level completion gate requiring task-aligned file action before completion.
