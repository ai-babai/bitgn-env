# Code proposal prop-007

- code_version: c0001
- prompt_version: p0010
- run_id: run_20260330T203824Z_8d778e50
- benchmark: bitgn/sandbox
- ts: 2026-03-30T20:44:41.514954+00:00

## Failed tasks
| Task | Fail group | Note |
|---|---|---|
| t06 | missing_ref | missing required ref 'skills/skill-todo.md' |

## Proposals (requires user approval)
- `t06`: `dynamic_required_ref_extractor`
  - fail: missing required ref 'skills/skill-todo.md'
  - code fix: Extract required ref path from AGENTS/policy text and enforce exact citation on completion.
