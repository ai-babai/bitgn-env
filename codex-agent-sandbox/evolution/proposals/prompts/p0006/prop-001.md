# Prompt proposal prop-001

- from prompt_version: p0006
- code_version: c0001
- run_id: run_20260329T215328Z_fb426d26
- benchmark: bitgn/sandbox
- ts: 2026-03-29T22:07:54.557745+00:00

## Failed tasks
| Task | Fail group | Note |
|---|---|---|
| t05 | missing_ref | missing required ref 'ops/retention.md' |
| t06 | missing_ref | missing required ref 'docs/skill-todo.md' |

## Suggestions
- `t05`: `dynamic_policy_ref_grounding`
  - fail: missing required ref 'ops/retention.md'
  - prompt fix: Derive required policy/skill ref from AGENTS instruction (scan folder -> read policy -> cite that exact path).
- `t06`: `dynamic_policy_ref_grounding`
  - fail: missing required ref 'docs/skill-todo.md'
  - prompt fix: Derive required policy/skill ref from AGENTS instruction (scan folder -> read policy -> cite that exact path).

## Current prompt pack
```json
{
  "version": "p0006",
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
