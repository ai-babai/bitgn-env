# Rules proposal prop-001

- local_run_id: local_run_20260404T223656Z_89664
- rules_version: rv0016
- model: gpt-5.3-codex
- primary_task: t08
- affected_tasks: t08

## Focus
- problem: Task t08 fails with fail_group=clarification_missing. The instruction text was incomplete (`Create captur`), but the agent still executed a full capture workflow and reported `OUTCOME_OK`. Scoring expected `OUTCOME_NONE_CLARIFICATION`, so the miss is an instruction-clarity gate failure in rules, not a tooling/runtime execution failure.
- solution_type: rules

## Primary task proposal
- `t08` fail_group=`clarification_missing`
  - hypothesis: If the agent must verify that the instruction is semantically complete before any mutating workflow step, truncated or fragmentary commands will route to clarification instead of guessed execution.
  - change: Add a small pre-execution rule in local AGENTS policy: when instruction text is syntactically or semantically incomplete (e.g., truncated verb/object, unfinished imperative, missing target required by the requested action), do not infer intent from nearby files and do not perform mutations. Return `OUTCOME_NONE_CLARIFICATION` with a minimal disambiguation question, and proceed only after an explicit complete instruction is available.
  - files:
    - `codex-agent-analytics/rules_versions/rv0016/AGENTS.md`: Add 3-6 bullets in completion/decision guardrails defining an instruction-completeness check before file mutations and required clarification outcome on incomplete commands.
  - rollback: Remove the newly added instruction-completeness bullets from `rules_versions/rv0016/AGENTS.md`.
