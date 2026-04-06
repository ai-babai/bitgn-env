# Prompt proposal prop-001

- from prompt_version: p0008
- code_version: c0001
- run_id: run_20260329T220754Z_b24f21cb
- benchmark: bitgn/sandbox
- ts: 2026-03-30T08:38:48.078732+00:00

## Failed tasks
| Task | Fail group | Note |
|---|---|---|
| t05 | no_answer | no answer provided |
| t06 | no_answer | no answer provided |
| t07 | no_answer | no answer provided |

## Suggestions
- `t05`: `general_prompt_tightening`
  - fail: no answer provided
  - prompt fix: Tighten planning and completion checklist for this failure pattern.
- `t06`: `general_prompt_tightening`
  - fail: no answer provided
  - prompt fix: Tighten planning and completion checklist for this failure pattern.
- `t07`: `general_prompt_tightening`
  - fail: no answer provided
  - prompt fix: Tighten planning and completion checklist for this failure pattern.

## Current prompt pack
```json
{
  "version": "p0008",
  "system_prompt": "You are the core planner for a BitGN sandbox agent.",
  "must_bootstrap_tools": [
    {
      "tool": "tree",
      "args": {
        "path": "/"
      }
    },
    {
      "tool": "read",
      "args": {
        "path": "AGENTS.MD"
      }
    }
  ],
  "mandatory_refs": [],
  "required_refs_on_completion": [],
  "enforce_forced_answer": true,
  "answer_exact_patterns": [
    "always respond with",
    "answer with exactly",
    "answer with"
  ],
  "ref_policy": {
    "mode": "dynamic",
    "strict_ref_minimization": true,
    "source_of_truth": "derive required refs from AGENTS + discovered policy/skill files",
    "do_not_pin_env_specific_paths": true
  }
}
```
