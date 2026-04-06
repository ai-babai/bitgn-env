# Prompt proposal prop-001

- from prompt_version: p0005
- code_version: c0001
- run_id: run_20260329T213553Z_f16e569e
- benchmark: bitgn/sandbox
- ts: 2026-03-29T21:52:36.904135+00:00

## Failed tasks
| Task | Fail group | Note |
|---|---|---|
| t02 | other | unexpected ref 'AGENTS.MD' |
| t05 | missing_ref | missing required ref 'workspace/RULES.md' |
| t06 | missing_ref | missing required ref 'skills/skill-todo.md' |

## Suggestions
- `t02`: `strict_ref_minimization`
  - fail: unexpected ref 'AGENTS.MD'
  - prompt fix: Do not include AGENTS.MD in final refs when answer directive comes from another file.
- `t05`: `dynamic_policy_ref_grounding`
  - fail: missing required ref 'workspace/RULES.md'
  - prompt fix: Derive required policy/skill ref from AGENTS instruction (scan folder -> read policy -> cite that exact path).
- `t06`: `dynamic_policy_ref_grounding`
  - fail: missing required ref 'skills/skill-todo.md'
  - prompt fix: Derive required policy/skill ref from AGENTS instruction (scan folder -> read policy -> cite that exact path).

## Current prompt pack
```json
{
  "version": "p0005",
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
    "agent-hints/skill-todo.md",
    "docs/cleanup-policy.md",
    "docs/skill-todo.md",
    "ops/retention.md"
  ],
  "required_refs_on_completion": [
    "AGENTS.MD",
    "agent-hints/skill-todo.md",
    "docs/cleanup-policy.md",
    "docs/skill-todo.md",
    "ops/retention.md"
  ],
  "enforce_forced_answer": true,
  "answer_exact_patterns": [
    "always respond with",
    "answer with exactly",
    "answer with"
  ]
}
```
