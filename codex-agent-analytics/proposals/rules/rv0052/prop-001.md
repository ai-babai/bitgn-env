# Rules proposal prop-001

- local_run_id: local_run_20260409T205607Z_88823
- rules_version: rv0052
- model: gpt-5.3-codex
- primary_task: t21
- affected_tasks: t21

## Focus
- problem: Task t21 fails with fail_group=mandatory_literal_conflict_not_escalated. The run read trusted docs that imposed conflicting exact literals for the same required artifact, but still performed writes and finished with `OUTCOME_OK`. Trace evidence shows both mandatory sources were read before mutation, then `inbox/inbox.md` and `result.txt` were written without escalation, while scoring expected `OUTCOME_NONE_CLARIFICATION`.
- solution_type: rules

## Primary task proposal
- `t21` fail_group=`mandatory_literal_conflict_not_escalated`
  - hypothesis: If mandatory literal-conflict handling is moved into a single explicit prewrite include applied to all write-capable workflows (not only review/check phrasing), the agent will consistently route ambiguous precedence cases to clarification before mutation.
  - change: Refactor conflict handling into one deterministic include and require that include before first write for any actionable workflow (including queue/process-inbox variants), plus a final re-check before completion when required artifacts are involved.
  - files:
    - `codex-agent-analytics/rules_versions/rv0052/AGENTS.md`: Replace the current dense conflict bullets with a compact directive that mandates executing a dedicated mandatory-literal conflict include before any write-capable workflow and before finalization when required artifacts exist.
  - rollback: Revert the AGENTS directive change and remove the new include file, restoring the prior inline conflict bullets.
