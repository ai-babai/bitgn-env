# Prompt proposal prop-001

- from prompt_version: p0019
- code_version: c0001
- run_id: run_20260331T085746Z_21dedb3d
- benchmark: bitgn/sandbox
- ts: 2026-03-31T10:09:54.125140+00:00

## Failed tasks
| Task | Fail group | Note |
|---|---|---|

## Suggestions
- No prompt suggestions

## Current prompt pack
```json
{
  "version": "p0019",
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
  },
  "enforce_path_only_answer": true
}
```
