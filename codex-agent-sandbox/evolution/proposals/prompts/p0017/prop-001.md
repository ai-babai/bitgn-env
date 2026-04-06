# Prompt proposal prop-001

- from prompt_version: p0017
- code_version: c0001
- run_id: run_20260331T080132Z_d362ed09
- benchmark: bitgn/sandbox
- ts: 2026-03-31T08:08:05.887894+00:00

## Failed tasks
| Task | Fail group | Note |
|---|---|---|
| t05 | missing_ref | missing required ref 'AGENTS.MD' |

## Suggestions
- `t05`: `dynamic_policy_ref_grounding`
  - fail: missing required ref 'AGENTS.MD'
  - prompt fix: Derive required policy/skill ref from AGENTS instruction (scan folder -> read policy -> cite that exact path).

## Current prompt pack
```json
{
  "version": "p0017",
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
