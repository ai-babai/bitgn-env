# Rules proposal prop-001

- local_run_id: local_run_20260409T173301Z_54095
- rules_version: rv0047
- model: gpt-5.3-codex
- primary_task: t29
- affected_tasks: t29

## Focus
- problem: Task t29 fails with fail_group=one_short_token. The run passed (`score=1.0`) with the correct one-token response, but execution cost was disproportionate for a binary inbox review: 304875 prompt tokens and 15 tool calls. The active local rules file is 97 lines (over the 95-line pressure threshold), and the session also made an avoidable invalid tool call (`--help`). This indicates rules-structure density risk for short-token tasks even when this sample succeeds.
- solution_type: rules

## Primary task proposal
- `t29` fail_group=`one_short_token`
  - hypothesis: If dense short-answer/review guardrails are moved from the main AGENTS file into a focused include, the agent will keep the same decision quality with lower prompt pressure and fewer exploratory missteps.
  - change: Extract one focused, reusable section for read-only inbox review + exact-literal short responses into a single include file, and replace that section in active AGENTS with a compact pointer plus priority note. Keep the rule generic: for exact-literal review prompts, follow a minimal read-only path (required policy/docs -> target inbox item -> decisive artifact check -> single completion call) without extra exploratory steps.
  - files:
    - `codex-agent-analytics/rules_versions/rv0047/AGENTS.md`: Replace one dense short-answer/review block with a concise pointer to a new include, reducing AGENTS line pressure while preserving precedence.
  - rollback: Remove the include reference from `rv0047/AGENTS.md` and delete `includes/inbox-short-answer-review.md` in the next rules version.
