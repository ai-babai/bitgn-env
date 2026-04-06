# Rules proposal prop-001

- local_run_id: local_run_20260405T142759Z_2511442
- rules_version: rv0027
- model: gpt-5.3-codex
- primary_task: t40
- affected_tasks: t40

## Focus
- problem: Task t40 fails with fail_group=ref_mismatch. The answer text was correct, but scoring failed because `grounding_refs` omitted the required canonical manager reference `contacts/mgr_001.json`. Tool traces show the run only searched/read `accounts/*` and then completed without reading/citing a `contacts/*` identity source for the person filter.
- solution_type: rules

## Primary task proposal
- `t40` fail_group=`ref_mismatch`
  - hypothesis: Reference-mismatch failures recur when agents derive rows from downstream records but do not include the canonical identity record used to bind an entity/person filter.
  - change: Add a pre-`report_completion` rule for entity/person-filtered answers: first resolve the filter using the canonical identity source (CRM: relevant `contacts/*.json` manager/contact file), then gather matching result rows (for example `accounts/*.json`). Require `grounding_refs` to include both (1) the canonical identity source and (2) the row-source files backing returned outputs.
  - files:
    - `codex-agent-analytics/rules_versions/rv0027/AGENTS.md`: Add concise grounding/provenance bullets near completion rules that enforce canonical identity citation plus row-evidence citation for entity-filtered queries.
  - rollback: Remove the added grounding/provenance gate bullets from `rules_versions/rv0027/AGENTS.md`.
