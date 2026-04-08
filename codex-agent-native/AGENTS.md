# AGENTS.md — codex-agent-native

Purpose: native runner for BitGN tasks (`sandbox` and `pac1`) with isolated task workspaces.

## Scope

- Keep changes focused on native runner flow: `runner.py`, `runtime_tools.py`, `tool_gateway.py`, local rules, and run artifacts.
- Do not mix unrelated project work in this directory.

## Main paths

- Runner: `runner.py`
- Runtime tool bridge: `runtime_tools.py`
- Local rules: `local-rules/AGENTS.md`
- Run artifacts: `runs/<local_run_id>/<task_id>/attempt_*/`

## Leaderboard run mode

- Leaderboard mode is enabled only when `BITGN_API_KEY` is set (or provided by wrapper from `~/.bitgn/bitgn-api-key`).
- Run name is controlled by `BITGN_RUN_NAME`.
- If `BITGN_RUN_NAME` is empty, runner uses default `codex-native <CODEX_MODEL>`.

Run-name convention for this workspace:

- regular: `[@skifmax]-[codex]-[Chiki-Banboni]`
- smoke: `[@skifmax]-[codex]-[Chiki-Banboni]-[smoke]`
- do not use `aika` suffix.

Smoke execution rule:

- smoke means targeted run only;
- smoke must run without leaderboard flow;
- for smoke, explicitly set `BITGN_API_KEY=''` and `BITGN_API_KEY_FILE='/tmp/bitgn-no-key'`.

Quick command examples:

```bash
cd /srv/aika-os/bitgn/code/bitgn-env

# single PAC1 task
BITGN_RUN_NAME='[@skifmax]-[codex]-[Chiki-Banboni]-[smoke]' ./run-codex-native.sh --env pac1 t01

# full PAC1 set
BITGN_RUN_NAME='[@skifmax]-[codex]-[Chiki-Banboni]' ./run-codex-native.sh --env pac1 -p 2 t{01..40}
```

## Notes discipline

- Project notes belong to `/srv/aika-os/bitgn/notes`, not to this code directory.
- After meaningful runbook/process updates, add or update a note in `bitgn/notes` and refresh `bitgn/notes/INDEX.md`.
