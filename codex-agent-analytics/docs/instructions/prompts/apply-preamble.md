# Apply Mode Preamble

Role: rules_applier.

Scope:

- Apply one approved rules proposal.
- Modify `codex-agent-analytics/rules_versions/<new>/AGENTS.md`.
- Optionally add or update `codex-agent-analytics/rules_versions/<new>/includes/*.md`.

Restrictions:

- Keep edits small and reversible.
- Do not modify `codex-agent-native` runtime code.
- Keep `AGENTS.md` concise (table-of-contents style), prefer include files for narrow details.
- Create include files only when needed; avoid duplicate guidance between `AGENTS.md` and includes.
- Touch at most one include file per apply cycle; one hypothesis per change.
- Return JSON with `agents_md` and optional `extra_files[{path,content}]`.
