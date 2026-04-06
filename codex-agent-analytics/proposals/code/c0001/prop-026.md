# Code proposal prop-026

- local_run_id: local_run_20260405T142759Z_2511442
- code_version: c0001
- model: gpt-5.3-codex
- primary_task: t40
- affected_tasks: t40
- policy: include blocking proposals only

## Focus
- problem: Task t40 fails with fail_group=ref_mismatch. The answer text was correct, but scoring failed because `grounding_refs` omitted the required canonical manager reference `contacts/mgr_001.json`. Tool traces show the run only searched/read `accounts/*` and then completed without reading/citing a `contacts/*` identity source for the person filter.
- solution_type: rules

## Primary task proposal
- none (no blocking code proposals in selected scope)
