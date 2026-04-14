# AGENTS.md — bitgn-env

Purpose: local workspace for BitGN challenge preparation.

## Scope

- Keep changes focused on BitGN setup and experiments.
- Use this project as a sandbox; avoid mixing unrelated work.

## Entry Points

- Sample repository: `sample-agents/`
- Platform: `https://bitgn.com/`
- PAC challenge: `https://bitgn.com/challenge/PAC`
- API info: `https://api.bitgn.com`

## Working Notes

- Start from `sample-agents/README.md`.
- For PAC runtime examples, check `sample-agents/pac1-py/`.
- For local dry runs without API key, check `sample-agents/sandbox-py/`.

## Native quick start

- Native runner wrapper: `./run-codex-native.sh`.
- Envs:
  - `--env pac1` -> `bitgn/pac1-dev`
  - `--env pac1-prod` -> `bitgn/pac1-prod` (requires contest access)
- Smoke rule: run without leaderboard (`BITGN_API_KEY=''` and `BITGN_API_KEY_FILE='/tmp/bitgn-no-key'`).
- PROD note: `bitgn/pac1-prod` can be blind mode; do not judge run quality by local `passed/failed` alone.
- Native wrapper supports explicit custom task order and `--fail-fast` mode.
- Historical baseline: <=100-line `AGENTS.md` policy reached rank #6 with `84/104` solved on `pac1-prod`: https://bitgn.com/l/pac1-prod
- Current trajectory to `104/104` came from rule-level generalization + risk-first ordering + fail-fast validation loop.

Examples:

```bash
cd /srv/aika-os/bitgn/code/bitgn-env

# dev smoke single task
BITGN_API_KEY='' BITGN_API_KEY_FILE='/tmp/bitgn-no-key' CODEX_BACKEND=omniroute CODEX_PROFILE='omni-codex-53-high' ./run-codex-native.sh --env pac1 t01

# full dev leaderboard
BITGN_RUN_NAME='[@skifmax]-[codex]-[chiki-banboni]-[high]-[xNNN]' CODEX_BACKEND=omniroute CODEX_PROFILE='omni-codex-53-high' ./run-codex-native.sh --env pac1 --all -p 9
```
