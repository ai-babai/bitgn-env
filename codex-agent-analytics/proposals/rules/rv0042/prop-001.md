# Rules proposal prop-001

- local_run_id: local_run_20260409T143239Z_30398
- rules_version: rv0042
- model: gpt-5.3-codex
- primary_task: t41
- affected_tasks: t41, t22

## Focus
- problem: Task t41 fails with fail_group=one_short_token. The agent called `context` and received `2026-03-03T00:00:00Z`, but still reported `2026-04-11`, which matches an external/system-date baseline rather than runtime context. This is a relative-date anchoring failure in final answer construction, not a tool availability problem.
- solution_type: rules

## Primary task proposal
- `t41` fail_group=`one_short_token`
  - hypothesis: If relative-date prompts must be resolved from the latest `context.time` with an explicit pre-completion anchor/result check, the agent will stop drifting to ambient/system date.
  - change: In active rules, add one mandatory guard for relative-date language (`today`, `tomorrow`, `day after tomorrow`, `yesterday`, `in N days/weeks`, similar): derive answer only from explicit instruction anchor or latest `context.time` (default). Before `report_completion`, perform a deterministic self-check `anchor=<YYYY-MM-DD> expression=<relative phrase> result=<YYYY-MM-DD>` and require the submitted date to equal that computed result, including read-only answer-only tasks.
  - files:
    - `codex-agent-analytics/rules_versions/rv0042/AGENTS.md`: Add a compact relative-date anchor rule that applies to all completion paths (not only write workflows) and requires context-derived date verification before final response.
  - rollback: Remove the added relative-date anchor/verification bullets from `rules_versions/rv0042/AGENTS.md` in the next rules version.
