# Rules proposal prop-001

- local_run_id: local_run_20260405T120138Z_2451877
- rules_version: rv0023
- model: gpt-5.3-codex
- primary_task: t26
- affected_tasks: t26

## Focus
- problem: Task t26 fails with fail_group=json_rewrite_lockout. The run wrote `outbox/84535.json` with escaped quotes (`\\\"`) on first write (tool step 30), and the immediate read-back showed the same escaped content (step 31), leaving invalid JSON for the outbox contract. Local rules then blocked any corrective rewrite on the same `*.json` path and required a non-OK finish, which led to `OUTCOME_NONE_UNSUPPORTED` and no `seq.json` bump.
- solution_type: rules

## Primary task proposal
- `t26` fail_group=`json_rewrite_lockout`
  - hypothesis: Strict no-rewrite rules for `*.json` convert occasional first-write escaping mistakes into avoidable hard failures in otherwise supported workflows.
  - change: Replace the absolute `*.json` rewrite ban with a narrow exception: allow one immediate corrective rewrite on the same JSON path only when post-write validation shows syntax-invalid JSON or escape-artifact corruption (for example `\\\"`). Keep the existing preflight requirement, require validation read-back after the corrective write, and for multi-file sequences (such as outbox payload + sequence counter) prohibit downstream writes until the current JSON file is validated.
  - files:
    - `codex-agent-analytics/rules_versions/rv0023/AGENTS.md`: Edit JSON write policy bullets to permit a single validation-gated corrective rewrite for malformed first writes, while preserving one-shot behavior for valid writes and keeping sequential gating for dependent JSON files.
  - rollback: Revert the updated JSON rewrite bullets in `rules_versions/rv0023/AGENTS.md` to restore the prior absolute no-corrective-rewrite behavior.
