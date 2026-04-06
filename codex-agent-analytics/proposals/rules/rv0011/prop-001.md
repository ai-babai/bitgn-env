# Rules proposal prop-001

- local_run_id: local_run_20260404T215632Z_82349
- rules_version: rv0011
- model: gpt-5.3-codex
- primary_task: t19
- affected_tasks: t19

## Focus
- problem: Task t19 fails with fail_group=filedeleted. The run completed the invoice resend steps but introduced an extra mutation by deleting an inbox file. The scorer reported `unexpected change FileDeleted`, and the tool trace includes `delete {"path":"inbox/msg_001.txt"}`. The failure is a workflow rule gap around inbox item lifecycle, not a runtime/tooling defect.
- solution_type: rules

## Primary task proposal
- `t19` fail_group=`filedeleted`
  - hypothesis: If rules explicitly treat `inbox/` items as immutable unless deletion/move is explicitly requested by instruction or docs, agents will avoid unexpected `FileDeleted` diffs while still completing inbox workflows.
  - change: Add one inbox lifecycle guardrail to local rules: during `process inbox` tasks, do not delete, move, or rename `inbox/msg_*.txt` unless an explicit instruction or policy line requires it; default behavior is to leave inbox source files untouched after producing required artifacts.
  - files:
    - `codex-agent-analytics/rules_versions/rv0011/AGENTS.md`: Append a concise guardrail bullet in the operational rules section defining inbox files as non-destructive by default and requiring explicit authorization for delete/move.
  - rollback: Remove the added inbox lifecycle bullet from `rules_versions/rv0011/AGENTS.md`.
