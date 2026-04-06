# Code proposal prop-013

- code_version: c0001
- prompt_version: p0016
- run_id: run_20260331T071318Z_2e520b48
- benchmark: bitgn/sandbox
- ts: 2026-03-31T08:01:32.330175+00:00

## Failed tasks
| Task | Fail group | Note |
|---|---|---|
| t05 | other | answer contains expected answer but is not precise. Expected: 'notes/staging/cleanup-me.md' |
| t06 | missing_ref | missing required ref 'skills/skill-todo.md' |

## Proposals (requires user approval)
- `t05`: `runner_safety_improvement`
  - fail: answer contains expected answer but is not precise. Expected: 'notes/staging/cleanup-me.md'
  - code fix: Tighten runtime checks and completion gating for this failure type.
- `t06`: `dynamic_required_ref_extractor`
  - fail: missing required ref 'skills/skill-todo.md'
  - code fix: Extract required ref path from AGENTS/policy text and enforce exact citation on completion.
