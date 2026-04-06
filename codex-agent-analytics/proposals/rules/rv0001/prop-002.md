# Rules proposal prop-002

- local_run_id: local_run_20260403T212858Z_55860
- rules_version: rv0001
- model: gpt-5.3-codex
- primary_task: t03
- affected_tasks: t03

## Focus
- problem: Task t03 fails with fail_group=path_typo. The task failed because the required capture write target was `01_capture/influential/...`, but the agent created and wrote `01_capture/influental/...`. Evidence: scorer reported missing write at `01_capture/influential/2026-03-23__hn-agent-kernel-stateful-agents.md`, while tool calls show `mkdir` and `write` under the misspelled directory.
- solution_type: rules

## Primary task proposal
- `t03` fail_group=`path_typo`
  - hypothesis: When destination folders are referenced with typos or ambiguous naming, agents can create near-match paths that pass local checks but fail evaluator-required writes; an explicit canonical-path check before write and before completion prevents this class of failure.
  - change: Add a short rule: before any `write` to a new or user-named folder, list sibling directories and prefer exact existing canonical buckets; if a near-match exists, use the canonical one. Add a pre-completion checklist item that verifies required output paths exactly (not approximately) and rejects completion if any required path was not written verbatim.
  - files:
    - `codex-agent-analytics/rules_versions/rv0001/AGENTS.md`: Add 2-4 concise bullets for exact destination-path reuse and mandatory exact-path verification before `report_completion`.
  - rollback: Remove the added canonical-path and exact-path verification bullets from the rules file.
