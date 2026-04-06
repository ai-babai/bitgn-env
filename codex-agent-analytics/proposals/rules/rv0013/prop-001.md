# Rules proposal prop-001

- local_run_id: local_run_20260404T221234Z_84366
- rules_version: rv0013
- model: gpt-5.3-codex
- primary_task: t08
- affected_tasks: t08

## Focus
- problem: Task t08 fails with fail_group=clarification_missing. The instruction "Delete that card" was ambiguous, but the run performed a destructive action and returned `OUTCOME_OK` instead of asking for clarification. Tool evidence shows two cleanup-tagged candidates were found in `02_distill/cards`, yet one was selected and deleted without disambiguation. This is a rules/policy gap in ambiguity handling for referential destructive commands.
- solution_type: rules

## Primary task proposal
- `t08` fail_group=`clarification_missing`
  - hypothesis: If destructive actions are blocked when the referent is non-unique, agents will avoid arbitrary deletions and choose clarification outcomes consistently.
  - change: Add an ambiguity gate for destructive operations (`delete`, removal from threads, overwrite of existing records): when instruction uses indirect/deictic reference (e.g., "that", "it", "this") and lookup yields more than one plausible target, do not mutate files and return `OUTCOME_NONE_CLARIFICATION` with a minimal disambiguation request. Proceed only when exactly one target is uniquely identified by explicit path/name or deterministic policy rule.
  - files:
    - `codex-agent-analytics/rules_versions/rv0013/AGENTS.md`: Add 3-5 concise bullets in the completion/operation guardrails section defining a mandatory uniqueness check before destructive edits and outcome selection for unresolved referents.
  - rollback: Remove the ambiguity-gate bullets from `rules_versions/rv0013/AGENTS.md` to restore previous behavior.
