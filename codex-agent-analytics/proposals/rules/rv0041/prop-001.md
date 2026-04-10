# Rules proposal prop-001

- local_run_id: local_run_20260409T142423Z_27815
- rules_version: rv0041
- model: gpt-5.3-codex-spark
- primary_task: t08
- affected_tasks: t08, t22, t41

## Focus
- problem: Task t08 fails with fail_group=one_short_token. The instruction was incomplete (`"Archive the thread and upd"` ends with a truncated action token), but the run executed a capture/card/thread workflow and reported `OUTCOME_OK`. Scoring expected `OUTCOME_NONE_CLARIFICATION`, indicating the harness did not enforce the explicit ambiguity gate before taking actions.
- solution_type: rules

## Primary task proposal
- `t08` fail_group=`one_short_token`
  - hypothesis: If an instruction ends with a dangling verb fragment, unresolved shorthand, or missing action object, the correct default in review/edit workflows is clarifying-outcome with no mutations.
  - change: In the active rules AGENTS file, add a higher-priority pre-mutation guard that treats unfinished command endings (including abbreviated tokens like `upd`, `upd...`, trailing conjunctions, or missing target nouns) as non-clarified. Require `OUTCOME_NONE_CLARIFICATION` and halt before any `read`/`write`/filesystem actions when triggered.
  - files:
    - `codex-agent-analytics/rules_versions/rv0041/AGENTS.md`: Add a short explicit ambiguity checklist entry under the instruction-completeness section defining truncated/incomplete phrases as blocking clarification cases and requiring immediate clarification outcome.
  - rollback: Delete the new ambiguity checklist lines from the active AGENTS rules file in a new rules version if false positives increase.
