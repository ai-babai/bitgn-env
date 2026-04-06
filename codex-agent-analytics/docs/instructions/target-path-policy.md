# Target Path Policy

Purpose: keep proposal target files deterministic and valid.

Rules targets whitelist:

- `codex-agent-analytics/rules_versions/<active>/AGENTS.md`
- `codex-agent-analytics/rules_versions/<active>/includes/*.md`
- existing `codex-agent-analytics/docs/instructions/*.md`

Rules normalization:

- missing/unknown rules path -> normalize to active `rules_versions/<active>/AGENTS.md`
- `docs/instructions/local-rules.md` -> normalize to active `rules_versions/<active>/AGENTS.md`
- rules include paths from other versions -> normalize to active `rules_versions/<active>/includes/*.md`

Atomicity guardrails:

- one apply cycle should modify at most one include file
- prefer AGENTS-only change unless include is required by line-budget or clarity

Code targets whitelist:

- `codex-agent-native/runner.py`
- `codex-agent-native/runtime_tools.py`
- `codex-agent-native/tool_gateway.py`
- `codex-agent-native/workspace.py`
- `codex-agent-native/harness_seed.py`

Code rule:

- if blocking code proposal has no whitelisted targets, downgrade to `optional` and set `proposal_code = null`
