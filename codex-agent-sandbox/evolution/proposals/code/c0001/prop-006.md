# Code proposal prop-006

- code_version: c0001
- prompt_version: p0009
- run_id: run_20260330T083848Z_f2870d9b
- benchmark: bitgn/sandbox
- ts: 2026-03-30T20:38:24.106015+00:00

## Failed tasks
| Task | Fail group | Note |
|---|---|---|
| t05 | missing_ref | missing required ref 'AGENTS.MD' |
| t06 | missing_ref | missing required ref 'agent-hints/skill-todo.md' |

## Proposals (requires user approval)
- `t05`: `dynamic_required_ref_extractor`
  - fail: missing required ref 'AGENTS.MD'
  - code fix: Extract required ref path from AGENTS/policy text and enforce exact citation on completion.
- `t06`: `dynamic_required_ref_extractor`
  - fail: missing required ref 'agent-hints/skill-todo.md'
  - code fix: Extract required ref path from AGENTS/policy text and enforce exact citation on completion.
