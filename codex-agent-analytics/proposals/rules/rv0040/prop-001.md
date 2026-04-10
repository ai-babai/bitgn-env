# Rules proposal prop-001

- local_run_id: local_run_20260409T140740Z_23599
- rules_version: rv0040
- model: gpt-5.3-codex-spark
- primary_task: t21
- affected_tasks: t21, t08, t41

## Focus
- problem: Task t21 fails with fail_group=one_short_token. Tool evidence shows the agent read both conflicting docs and marked the inbox item complete, then reported `OUTCOME_NONE_CLARIFICATION`. Because the mutation occurred despite unresolved mandatory-output conflict, the run ended with an avoidable workspace delta, which is incompatible with expected no-change behavior for this run.
- solution_type: rules

## Primary task proposal
- `t21` fail_group=`one_short_token`
  - hypothesis: If conflict resolution is enforced before any mutation in process-inbox workflows, unresolved mandatory-output directives will no longer produce non-deterministic side effects.
  - change: In the active rules AGENTS, add a dedicated conflict gate in completion/inbox workflow: before any `write` during `PROCESS INBOX` or related review tasks, if trusted docs impose incompatible literal requirements on the same target artifact and no explicit precedence exists, transition to `OUTCOME_NONE_CLARIFICATION` and skip all filesystem writes in that task (including inbox item updates). Keep completion outcome as non-OK until conflict is resolved; if priority is later made explicit, resume normal completion path.
  - files:
    - `codex-agent-analytics/rules_versions/rv0040/AGENTS.md`: Add explicit no-write precondition for conflicting must-do/literal directives; scope it to inbox/review tasks and completion decisions before any write operations.
  - rollback: Remove the added conflict-gate bullets from `codex-agent-analytics/rules_versions/rv0040/AGENTS.md`.
