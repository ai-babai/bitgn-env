# Code Escalation Gate

Code proposal is allowed only if classification is `blocking`.

Blocking requirements:

- `code_assessment.classification = blocking`
- non-empty `code_assessment.reason`
- non-empty `code_assessment.rules_insufficient_evidence`
- concrete `proposal_code` with target files
- `proposal_code.blocker_reason`

Otherwise:

- downgrade to `optional`
- set `proposal_code = null`
- keep solution in harness/rules path
