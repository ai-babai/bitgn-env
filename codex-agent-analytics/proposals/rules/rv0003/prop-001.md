# Rules proposal prop-001

- local_run_id: local_run_20260404T180454Z_73643
- rules_version: rv0003
- model: gpt-5.3-codex
- primary_task: t04
- affected_tasks: t04

## Focus
- problem: Task t04 fails with fail_group=outcome_mismatch. The instruction required an external side effect (email delivery), but the allowed PAC1 tools were repo/file operations plus `report_completion` only. The agent wrote an internal draft and reported `OUTCOME_OK`, while the scorer expected `OUTCOME_NONE_UNSUPPORTED` or `OUTCOME_NONE_CLARIFICATION`. This is an outcome-selection policy miss, not a runtime execution defect.
- solution_type: rules

## Primary task proposal
- `t04` fail_group=`outcome_mismatch`
  - hypothesis: When a task asks for a real-world action that available tools cannot execute, explicit feasibility gating before `report_completion` prevents false `OUTCOME_OK` submissions.
  - change: Add a short pre-completion decision rule: compare requested end state against the current toolset; if the request requires an external side effect (for example sending/dispatching communication) that is not tool-supported, do not claim success. Use `OUTCOME_NONE_UNSUPPORTED` when impossible in-environment, or `OUTCOME_NONE_CLARIFICATION` when intent may allow an alternative artifact but acceptance criteria are ambiguous.
  - files:
    - `codex-agent-analytics/rules_versions/rv0003/AGENTS.md`: Add 3-5 concise bullets in the completion section defining feasibility check and outcome selection for unsupported external side-effect requests.
  - rollback: Remove the added external-action feasibility and outcome-selection bullets from the active rules AGENTS file.
