# Codex Analyzer Prompt Policy

Return JSON only.

Policy:

- Harness-first: default to rules/process solution.
- Keep rules proposal small, reversible, and generalizable.
- Prefer compact `AGENTS.md` and targeted includes over monolithic rule growth.
- Avoid task-specific literals.
- Include exact target file paths with change summaries.

Code policy:

- Always set `code_assessment.classification`.
- If `optional`, set `proposal_code = null`.
- If `blocking`, include `blocker_reason` and `rules_insufficient_evidence`.
- If unsure, choose `optional`.
