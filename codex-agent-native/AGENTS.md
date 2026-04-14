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

## Historical context

- Original compact policy (`local-rules/AGENTS.md` <= 100 lines) reached rank #6 with `84/104` solved on `pac1-prod`: https://bitgn.com/l/pac1-prod
- Current `104/104` stabilization was achieved via rule-level generalization + risk-first ordering + fail-fast validation cycles.

## Leaderboard run mode

- Leaderboard mode is enabled only when `BITGN_API_KEY` is set (or provided by wrapper from `~/.bitgn/bitgn-api-key`).
- Run name is controlled by `BITGN_RUN_NAME`.
- If `BITGN_RUN_NAME` is empty, runner uses default `codex-native <CODEX_MODEL>`.
- Task execution order is exactly the order of task IDs passed to `run-codex-native.sh` / `runner.py`.
- `--fail-fast` is supported and should be used for risk-first gating before full leaderboard submit.

Environment mapping in wrapper (`run-codex-native.sh`):

- `--env pac1` -> `BENCHMARK_ID=bitgn/pac1-dev`
- `--env pac1-prod` -> `BENCHMARK_ID=bitgn/pac1-prod`
- `--env sandbox` -> `BENCHMARK_ID=bitgn/sandbox`

Blind-mode reminder for PROD:

- `bitgn/pac1-prod` may run in blind mode; local `passed/failed` and per-task `score` are not reliable quality signals.
- For blind PROD runs, treat operational success as: tasks resolved, `LEADERBOARD_SUBMIT` present, and no runtime infra failures.

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
BITGN_API_KEY='' BITGN_API_KEY_FILE='/tmp/bitgn-no-key' CODEX_BACKEND=omniroute CODEX_PROFILE='omni-codex-53-high' ./run-codex-native.sh --env pac1 t01

# full PAC1 set
BITGN_RUN_NAME='[@skifmax]-[codex]-[chiki-banboni]-[high]-[xNNN]' CODEX_BACKEND=omniroute CODEX_PROFILE='omni-codex-53-high' ./run-codex-native.sh --env pac1 -p 9 t{01..43}

# full PAC1 PROD set (when access is enabled)
BITGN_RUN_NAME='[@skifmax]-[codex]-[chiki-banboni]-[prod]-[xNNN]' CODEX_BACKEND=omniroute CODEX_PROFILE='omni-codex-53-high' ./run-codex-native.sh --env pac1-prod -p 9 t{01..43}
```

## Notes discipline

- Project notes belong to `/srv/aika-os/bitgn/notes`, not to this code directory.
- After meaningful runbook/process updates, add or update a note in `bitgn/notes` and refresh `bitgn/notes/INDEX.md`.
