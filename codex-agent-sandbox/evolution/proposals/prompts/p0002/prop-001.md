# Prompt proposal prop-001

- from prompt_version: p0002
- code_version: c0001
- run_id: run_20260329T203429Z_a3f5fc3b
- benchmark: bitgn/sandbox
- ts: 2026-03-29T20:51:09.089798+00:00

## Failed tasks
| Task | Fail group | Note |
|---|---|---|
| t05 | missing_ref | missing required ref 'AGENTS.MD' |
| t06 | missing_ref | missing required ref 'agent-hints/skill-todo.md' |

## Suggestions
- `t05`: `add_mandatory_ref` — missing required ref 'AGENTS.MD'
- `t06`: `add_mandatory_ref` — missing required ref 'agent-hints/skill-todo.md'

## Current prompt pack
```json
{
  "version": "p0002",
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
