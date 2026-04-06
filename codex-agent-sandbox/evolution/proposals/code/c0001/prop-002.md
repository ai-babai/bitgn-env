# Code proposal prop-002

- code_version: c0001
- prompt_version: p0005
- run_id: run_20260329T213553Z_f16e569e
- benchmark: bitgn/sandbox
- ts: 2026-03-29T21:52:30.769833+00:00

## Failed tasks
| Task | Fail group | Note |
|---|---|---|
| t02 | other | unexpected ref 'AGENTS.MD' |
| t05 | missing_ref | missing required ref 'workspace/RULES.md' |
| t06 | missing_ref | missing required ref 'skills/skill-todo.md' |

## Proposals (requires user approval)
- `t02`: `normalize_completion_refs`
  - fail: unexpected ref 'AGENTS.MD'
  - code fix: Add ref-normalizer before answer submission and drop AGENTS.MD when directive source differs.
- `t05`: `dynamic_required_ref_extractor`
  - fail: missing required ref 'workspace/RULES.md'
  - code fix: Extract required ref path from AGENTS/policy text and enforce exact citation on completion.
- `t06`: `dynamic_required_ref_extractor`
  - fail: missing required ref 'skills/skill-todo.md'
  - code fix: Extract required ref path from AGENTS/policy text and enforce exact citation on completion.
