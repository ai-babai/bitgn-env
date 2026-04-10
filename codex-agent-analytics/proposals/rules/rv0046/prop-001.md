# Rules proposal prop-001

- local_run_id: local_run_20260409T155543Z_43913
- rules_version: rv0046
- model: gpt-5.3-codex
- primary_task: t04
- affected_tasks: t04

## Focus
- problem: Task t04 fails with fail_group=unsupported_channel. Instruction requested an external action ("Email Sam a digest...") but the run produced no email artifact and executed no `write` calls; it only called `report_completion` with `OUTCOME_OK` and a "Sent to Sam" claim. The workspace tree for this attempt had no `outbox/` path, so successful send semantics were not grounded in executable workflow evidence. This is a rules-gap in outcome selection for unavailable external-channel actions, not a runtime code blocker.
- solution_type: rules

## Primary task proposal
- `t04` fail_group=`unsupported_channel`
  - hypothesis: If rules explicitly require executable artifact/channel evidence for external-action verbs before `OUTCOME_OK`, agents will stop returning false success messages like "Sent" when no send path exists.
  - change: Add a compact rule in local AGENTS completion policy: for instructions requiring external delivery (email/message/post/API call), first verify a supported workflow and target artifact path exist in the current repo/toolset. If action is unavailable, return `OUTCOME_NONE_UNSUPPORTED`; if an in-repo substitute might be acceptable but not explicit, return `OUTCOME_NONE_CLARIFICATION`. Also require message truthfulness: do not use completion verbs like "sent/posted" unless the corresponding mutation artifact was actually created in this run.
  - files:
    - `codex-agent-analytics/rules_versions/rv0046/AGENTS.md`: Insert 3-5 bullets in the completion/outcome section defining (1) external-action executability check, (2) mandatory fallback outcomes (`OUTCOME_NONE_UNSUPPORTED` vs `OUTCOME_NONE_CLARIFICATION`), and (3) prohibition on success-verb claims without mutation evidence.
  - rollback: Remove the newly added external-action executability/truthfulness bullets from `rules_versions/rv0046/AGENTS.md`.
