# Codex Analyzer Prompt Policy

Return JSON only.

Policy:

- Harness-first: default to rules/process solution.
- Keep rules proposal small, reversible, and generalizable.
- Prefer compact `AGENTS.md` and targeted includes over monolithic rule growth.
- Treat `AGENTS.md` > 145 lines as offload pressure (aligned with native default cap 156): propose include/harness-file extraction instead of piling more bullets into AGENTS.
- You may propose new documentation files when missing harness structure is the blocker.
- New file creation is optional and must be justified: repeated signal (>=2 runs/tasks), expected generalization, and explicit rollback.
- If justification is weak, update existing files instead of creating new structure.
- New files should follow the map in `docs/references/harness-engineering-structure-draft.md`.
- Prefer minimal additions: one focused file or one focused section per hypothesis.
- Avoid task-specific literals.
- Include exact target file paths with change summaries.

Code policy:

- Always set `code_assessment.classification`.
- If `optional`, set `proposal_code = null`.
- If `blocking`, include `blocker_reason` and `rules_insufficient_evidence`.
- If unsure, choose `optional`.
