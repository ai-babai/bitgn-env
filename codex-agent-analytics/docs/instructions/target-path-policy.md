# Target Path Policy

Purpose: keep proposal target files deterministic and valid.

Rules targets whitelist:

- `codex-agent-analytics/rules_versions/<active>/AGENTS.md`
- `codex-agent-analytics/rules_versions/<active>/includes/*.md`
- `codex-agent-analytics/docs/instructions/**/*.md` (existing only)
- harness-structure docs aligned to `docs/references/harness-engineering-structure-draft.md`:
  - `codex-agent-analytics/ARCHITECTURE.md`
  - `codex-agent-analytics/docs/design-docs/**`
  - `codex-agent-analytics/docs/exec-plans/**`
  - `codex-agent-analytics/docs/generated/**`
  - `codex-agent-analytics/docs/product-specs/**`
  - `codex-agent-analytics/docs/references/**`
  - `codex-agent-analytics/docs/DESIGN.md`
  - `codex-agent-analytics/docs/FRONTEND.md`
  - `codex-agent-analytics/docs/PLANS.md`
  - `codex-agent-analytics/docs/PRODUCT_SENSE.md`
  - `codex-agent-analytics/docs/QUALITY_SCORE.md`
  - `codex-agent-analytics/docs/RELIABILITY.md`
  - `codex-agent-analytics/docs/SECURITY.md`

Rules normalization:

- missing/unknown rules path -> normalize to active `rules_versions/<active>/AGENTS.md`
- `docs/instructions/local-rules.md` -> normalize to active `rules_versions/<active>/AGENTS.md`
- rules include paths from other versions -> normalize to active `rules_versions/<active>/includes/*.md`
- new docs outside allowed harness map -> normalize to active `rules_versions/<active>/AGENTS.md`
- non-existing `docs/instructions/**` path -> normalize to active `rules_versions/<active>/AGENTS.md`

Atomicity guardrails:

- one apply cycle should modify at most one include file
- one apply cycle should modify at most one harness doc file
- prefer AGENTS-only change unless include is required by line-budget or clarity
- if AGENTS exceeds 95 lines, prefer include/harness offload over new AGENTS bullets
- adding a new harness file requires explicit evidence in analyze report: repeated pattern (>=2 runs), expected generalization, and rollback note
- if this evidence is weak, prefer updating existing files instead of adding new structure

Code targets whitelist:

- `codex-agent-native/runner.py`
- `codex-agent-native/runtime_tools.py`
- `codex-agent-native/tool_gateway.py`
- `codex-agent-native/workspace.py`
- `codex-agent-native/harness_seed.py`

Code rule:

- if blocking code proposal has no whitelisted targets, downgrade to `optional` and set `proposal_code = null`
