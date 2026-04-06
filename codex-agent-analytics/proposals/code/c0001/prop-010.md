# Code proposal prop-010

- local_run_id: local_run_20260404T215632Z_82349
- code_version: c0001
- model: gpt-5.3-codex
- primary_task: t19
- affected_tasks: t19
- policy: include blocking proposals only

## Focus
- problem: Task t19 fails with fail_group=filedeleted. The run completed the invoice resend steps but introduced an extra mutation by deleting an inbox file. The scorer reported `unexpected change FileDeleted`, and the tool trace includes `delete {"path":"inbox/msg_001.txt"}`. The failure is a workflow rule gap around inbox item lifecycle, not a runtime/tooling defect.
- solution_type: rules

## Primary task proposal
- none (no blocking code proposals in selected scope)
