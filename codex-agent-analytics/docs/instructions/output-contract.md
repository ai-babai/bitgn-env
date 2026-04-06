# Output Contract

Task-level required fields:

- `task_id`, `status`, `fail_group`, `diagnosis`
- `code_assessment.classification` (`blocking` or `optional`)
- `code_assessment.reason`
- `proposal_rules` with `hypothesis`, `change`, `target_files`, `rollback`

When blocking:

- `code_assessment.rules_insufficient_evidence`
- `proposal_code` object with `blocker_reason`, `target_files`

When optional:

- `proposal_code = null`

Run-level required fields:

- `focus.primary_task_id`
- `focus.problem`
- `focus.solution_type`
- `focus.affected_tasks`

Apply mode artifacts:

- `applies/aXXXX.md`
- `APPLY_LOG.jsonl`
- `RULES_CHANGELOG.jsonl`

Deploy mode artifacts:

- `deploy/dXXXX.md`
- `DEPLOY_LOG.jsonl`

Target-path validation fields:

- `rules_target_validation[]` with `status`, `original_path`, `final_path`, `reason`
- `code_target_validation[]` with `status`, `original_path`, `final_path`, `reason`
