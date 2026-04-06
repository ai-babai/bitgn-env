# Code proposal prop-008

- code_version: c0001
- prompt_version: p0011
- run_id: run_20260330T204441Z_fa221bf4
- benchmark: bitgn/sandbox
- ts: 2026-03-30T21:12:21.467569+00:00

## Failed tasks
| Task | Fail group | Note |
|---|---|---|
| t05 | missing_ref | missing required ref 'docs/cleanup-policy.md' |
| t06 | missing_ref | missing required ref 'docs/skill-todo.md' |

## Proposals (requires user approval)
- `t05`: `dynamic_required_ref_extractor`
  - fail: missing required ref 'docs/cleanup-policy.md'
  - code fix: Extract required ref path from AGENTS/policy text and enforce exact citation on completion.
- `t06`: `dynamic_required_ref_extractor`
  - fail: missing required ref 'docs/skill-todo.md'
  - code fix: Extract required ref path from AGENTS/policy text and enforce exact citation on completion.
