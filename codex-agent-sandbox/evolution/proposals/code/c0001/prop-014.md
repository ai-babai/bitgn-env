# Code proposal prop-014

- code_version: c0001
- prompt_version: p0017
- run_id: run_20260331T080132Z_d362ed09
- benchmark: bitgn/sandbox
- ts: 2026-03-31T08:08:05.890352+00:00

## Failed tasks
| Task | Fail group | Note |
|---|---|---|
| t05 | missing_ref | missing required ref 'AGENTS.MD' |

## Proposals (requires user approval)
- `t05`: `dynamic_required_ref_extractor`
  - fail: missing required ref 'AGENTS.MD'
  - code fix: Extract required ref path from AGENTS/policy text and enforce exact citation on completion.
