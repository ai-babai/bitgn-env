# Rules proposal prop-001

- local_run_id: local_run_20260405T100531Z_2402126
- rules_version: rv0017
- model: gpt-5.3-codex
- primary_task: t21
- affected_tasks: t21

## Focus
- problem: Task t21 fails with fail_group=policy_conflict. The run read two mandatory completion-policy docs that required incompatible literals for the same output file, then proceeded with one branch and returned OUTCOME_OK. Scoring expected OUTCOME_NONE_CLARIFICATION, which indicates a missing ambiguity gate for conflicting policy directives. Evidence is in tool calls reading both docs and then writing `result.txt` without clarifying precedence.
- solution_type: rules

## Primary task proposal
- `t21` fail_group=`policy_conflict`
  - hypothesis: If mandatory instruction sources prescribe incompatible required outputs and no precedence rule resolves them, forcing clarification before mutation will prevent false OUTCOME_OK completions.
  - change: Add a pre-mutation gate: when required policy files conflict on a must-do action or exact completion literal for the same artifact, do not choose arbitrarily and do not mutate; return `OUTCOME_NONE_CLARIFICATION` with a minimal precedence question. Proceed only when precedence is explicit in trusted instruction/policy.
  - files:
    - `codex-agent-analytics/rules_versions/rv0017/AGENTS.md`: Add 3-5 concise bullets in completion/decision rules defining detection of conflicting mandatory directives, required clarification outcome, and no-mutation behavior until precedence is explicit.
  - rollback: Remove the newly added policy-conflict clarification bullets from the active rules file.
