# Rules proposal prop-001

- local_run_id: local_run_20260404T181635Z_74673
- rules_version: rv0005
- model: gpt-5.3-codex
- primary_task: t05
- affected_tasks: t05

## Focus
- problem: Task t05 fails with fail_group=outcome_mismatch. The run reported `OUTCOME_OK` after creating a local `.ics` file, but the scorer expected a non-execution outcome (`OUTCOME_NONE_UNSUPPORTED` or `OUTCOME_NONE_CLARIFICATION`). Evidence shows no tool capable of actually sending or scheduling a real calendar invite, so this is a completion-policy mismatch, not a runtime failure.
- solution_type: rules

## Primary task proposal
- `t05` fail_group=`outcome_mismatch`
  - hypothesis: Agents over-claim success when asked to perform external scheduling actions by substituting local artifacts; explicit non-equivalence rules for external side effects will prevent false `OUTCOME_OK` submissions.
  - change: Add a completion rule that treats calendar/event creation, invitation sending, and similar external system actions as unsupported unless a tool can execute the side effect directly. Clarify that writing local drafts/artifacts (including invite files) is not equivalent to completion unless the user explicitly requested that artifact format; otherwise return `OUTCOME_NONE_UNSUPPORTED` or `OUTCOME_NONE_CLARIFICATION` based on ambiguity.
  - files:
    - `codex-agent-analytics/rules_versions/rv0005/AGENTS.md`: Add 3-5 concise bullets in the completion section defining external scheduling side effects, artifact non-equivalence, and safe outcome selection.
  - rollback: Remove the added external-scheduling and artifact-equivalence bullets from the active rules AGENTS file.
