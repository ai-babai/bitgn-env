# Prompt proposal prop-001

- from prompt_version: p0003
- code_version: c0001
- run_id: run_20260329T210530Z_c8710ffb
- benchmark: bitgn/sandbox
- ts: 2026-03-29T21:20:04.114384+00:00

## Failed tasks
| Task | Fail group | Note |
|---|---|---|
| t02 | other | unexpected ref 'AGENTS.MD' |
| t05 | missing_ref | missing required ref 'docs/cleanup-policy.md' |
| t06 | missing_ref | missing required ref 'docs/skill-todo.md' |

## Suggestions
- `t05`: `add_mandatory_ref` — missing required ref 'docs/cleanup-policy.md'
- `t06`: `add_mandatory_ref` — missing required ref 'docs/skill-todo.md'

## Current prompt pack
```json
{
  "version": "p0003",
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
  "mandatory_refs": [
    "AGENTS.MD",
    "agent-hints/skill-todo.md"
  ],
  "required_refs_on_completion": [
    "AGENTS.MD",
    "agent-hints/skill-todo.md"
  ],
  "enforce_forced_answer": true,
  "answer_exact_patterns": [
    "always respond with",
    "answer with exactly",
    "answer with"
  ]
}
```
