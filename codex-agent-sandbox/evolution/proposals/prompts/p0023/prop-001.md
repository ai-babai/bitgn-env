# Prompt proposal prop-001

- from prompt_version: p0023
- code_version: c0001
- run_id: run_20260402T085850Z_57b85a6b
- benchmark: bitgn/pac1-dev
- ts: 2026-04-02T09:22:06.790957+00:00

## Failed tasks
| Task | Fail group | Note |
|---|---|---|
| t02 | no_answer | no answer provided |
| t03 | missing_file_write | missing file write '02_distill/cards/2026-03-23__hn-walmart-chatgpt-checkout.md' |

## Suggestions
- `t02`: `code:experience`
  - fail: no answer provided
  - prompt fix: When model decision fails or is empty, always emit deterministic fallback completion payload with valid contract fields.
- `t03`: `action_before_completion`
  - fail: missing file write '02_distill/cards/2026-03-23__hn-walmart-chatgpt-checkout.md'
  - prompt fix: Require one concrete tool action matching task intent before report_completion.

## Current prompt pack
```json
{
  "version": "p0023",
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
