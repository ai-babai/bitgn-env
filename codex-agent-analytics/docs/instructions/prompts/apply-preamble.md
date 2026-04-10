# Apply Mode Preamble

Role: rules_applier.

Scope:

- Apply one approved rules proposal.
- Modify `codex-agent-analytics/rules_versions/<new>/AGENTS.md`.
- Optionally add or update `codex-agent-analytics/rules_versions/<new>/includes/*.md`.
- Optionally add or update one harness doc file under `codex-agent-analytics/docs/**` or `codex-agent-analytics/ARCHITECTURE.md` when the proposal explicitly requires structure-level clarification.

Restrictions:

- Keep edits small and reversible.
- Do not modify `codex-agent-native` runtime code.
- Keep `AGENTS.md` concise (table-of-contents style), prefer include files for narrow details.
- Runtime hard cap: `AGENTS.md` must remain <= 100 lines.
- Soft budget: if `AGENTS.md` would exceed 95 lines, offload details into one include file or one harness doc in this cycle.
- Create include files only when needed; avoid duplicate guidance between `AGENTS.md` and includes.
- Touch at most one include file per apply cycle; one hypothesis per change.
- Touch at most one harness doc file per apply cycle.
- Do not create new `docs/instructions/**` files in apply. Only existing instruction docs may be edited.
- Create a new harness doc file only with explicit evidence from analyze report (repeated signal, generalization, rollback).
- Return JSON with `agents_md`, optional `extra_files[{path,content}]`, and optional `harness_docs[{path,content}]`.
