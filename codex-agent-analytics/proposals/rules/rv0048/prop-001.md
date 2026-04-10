# Rules proposal prop-001

- local_run_id: local_run_20260409T174324Z_54982
- rules_version: rv0048
- model: gpt-5.3-codex
- primary_task: t19
- affected_tasks: t19

## Focus
- problem: Task t19 fails with fail_group=workflow_misclassification. The run correctly resolved sender identity and invoice intent, but it ended with `report_completion` without creating required outbox artifacts. Scoring failed only on missing `outbox/<id>.json` and `outbox/seq.json`, which indicates the task was treated as read-only review instead of executable inbox processing.
- solution_type: rules

## Primary task proposal
- `t19` fail_group=`workflow_misclassification`
  - hypothesis: If the short-answer inbox review profile requires a mandatory actionability check before finalization, agents will avoid false read-only completions and execute required artifact writes for actionable inbox requests.
  - change: Update the inbox short-answer review include to require an explicit gate: when the pending inbox item maps to a trusted documented workflow that requires mutations (for example outbound email artifacts), the agent must exit the read-only shortcut and run the full processing workflow before allowing `OUTCOME_OK`. Keep the read-only shortcut only for explicitly informational/check-only requests.
  - files:
    - `codex-agent-analytics/rules_versions/rv0048/AGENTS.md`: Add a brief 'Actionability gate' section and tighten scope language so queue/review wording alone does not authorize read-only completion when trusted docs define required writes.
  - rollback: Revert the new actionability-gate section in the include file to restore prior read-only shortcut behavior.
