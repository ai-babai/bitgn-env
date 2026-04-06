# Code proposal prop-003

- code_version: c0001
- prompt_version: p0006
- run_id: run_20260329T215328Z_fb426d26
- benchmark: bitgn/sandbox
- ts: 2026-03-29T22:07:54.558890+00:00

## Failed tasks
| Task | Fail group | Note |
|---|---|---|
| t05 | missing_ref | missing required ref 'ops/retention.md' |
| t06 | missing_ref | missing required ref 'docs/skill-todo.md' |

## Proposals (requires user approval)
- `t05`: `dynamic_required_ref_extractor`
  - fail: missing required ref 'ops/retention.md'
  - code fix: Extract required ref path from AGENTS/policy text and enforce exact citation on completion.
- `t06`: `dynamic_required_ref_extractor`
  - fail: missing required ref 'docs/skill-todo.md'
  - code fix: Extract required ref path from AGENTS/policy text and enforce exact citation on completion.
