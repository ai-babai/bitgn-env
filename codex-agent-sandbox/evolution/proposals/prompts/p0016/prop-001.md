# Prompt proposal prop-001

- from prompt_version: p0016
- code_version: c0001
- run_id: run_20260331T071318Z_2e520b48
- benchmark: bitgn/sandbox
- ts: 2026-03-31T08:01:32.328393+00:00

## Failed tasks
| Task | Fail group | Note |
|---|---|---|
| t05 | other | answer contains expected answer but is not precise. Expected: 'notes/staging/cleanup-me.md' |
| t06 | missing_ref | missing required ref 'skills/skill-todo.md' |

## Suggestions
- `t05`: `general_prompt_tightening`
  - fail: answer contains expected answer but is not precise. Expected: 'notes/staging/cleanup-me.md'
  - prompt fix: Tighten planning and completion checklist for this failure pattern.
- `t06`: `dynamic_policy_ref_grounding`
  - fail: missing required ref 'skills/skill-todo.md'
  - prompt fix: Derive required policy/skill ref from AGENTS instruction (scan folder -> read policy -> cite that exact path).

## Current prompt pack
```json
{
  "version": "p0016",
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
  },
  "structured_output_policy": {
    "require_non_empty_decision": true,
    "fallback_to_safe_completion_on_parse_failure": true
  }
}
```
