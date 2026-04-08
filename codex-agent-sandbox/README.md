# codex-agent-sandbox

First version of BitGN sandbox agent where Codex CLI is the core reasoning engine.

## Architecture

- `runner.py` orchestrates benchmark/trial lifecycle via BitGN harness.
- `codex_bridge.py` invokes `codex exec` with strict JSON schema for each decision step.
- Runtime tool calls (`tree/read/write/...`) are executed by harness client only.

This keeps Codex CLI as the planner/decision-maker while Python remains execution control plane.

## Run

```bash
cd /Users/skif/develop/bitgn-env/codex-agent-sandbox
uv run python runner.py t01
```

## Evolution modes

Use wrapper from project root:

```bash
cd /Users/skif/develop/bitgn-env

# 1) solve
./run-codex-evolve.sh solve --all
./run-codex-evolve.sh solve --parallelism 2 t01 t02

# 2) analyze latest run
./run-codex-evolve.sh analyze

# analyze now also includes fixability assessment per failed task:
# prompt potential, prompt-only likelihood, code-need, blocker flag

# 3) prompt proposals
./run-codex-evolve.sh propose-prompts

# 4) code proposals (no auto-apply)
./run-codex-evolve.sh propose-code

# 5) apply prompts and switch prompt version
./run-codex-evolve.sh apply-prompts --hypothesis "Increase pass rate on missing-ref failures"

# full evolution step (analyze -> propose -> apply-prompts -> solve -> analyze)
./run-codex-evolve.sh full-step --hypothesis "..."
./run-codex-evolve.sh full-step --env pac1 --parallelism 2 --hypothesis "..." t03 t22

# if selected tasks are marked as code blockers, prompt evolution is stopped by default
# override only for investigation:
./run-codex-evolve.sh full-step --env pac1 --allow-blocked-prompt --hypothesis "force prompt check" t03 t23

# full evolution step with affected-task scope
./run-codex-evolve.sh full-step --env pac1 --task-scope affected --affected-from last-apply --max-affected 6 --hypothesis "..."

# autonomous N evolution steps (prompt-only)
./run-codex-evolve.sh autopilot --n 3 --no-improve-limit 2 --hypothesis "..."
./run-codex-evolve.sh autopilot --env pac1 --parallelism 2 --n 3 --no-improve-limit 999 --task-scope affected t03 t22

# autonomous evolution on affected tasks only
./run-codex-evolve.sh autopilot --env pac1 --task-scope affected --affected-from last-apply --max-affected 8 --n 2 --no-improve-limit 2 --hypothesis "..."

# autonomous evolution on fixed task ids (same tasks each step)
./run-codex-evolve.sh autopilot --env pac1 --n 3 --no-improve-limit 999 --hypothesis "pac1 fixed-4" t03 t22 t23 t25

# fixed task ids + affected behavior: rerun only still-failing tasks in next iterations
./run-codex-evolve.sh autopilot --env pac1 --task-scope affected --n 3 --no-improve-limit 999 --hypothesis "pac1 fixed-4 affected" t03 t22 t23 t25

# classic fixed-scope evolution (same 4 tasks, 3 sequential iterations)
./run-codex-evolve.sh full-step --env pac1 --hypothesis "pac1 fixed-4 step1" t03 t22 t23 t25
./run-codex-evolve.sh full-step --env pac1 --hypothesis "pac1 fixed-4 step2" t03 t22 t23 t25
./run-codex-evolve.sh full-step --env pac1 --hypothesis "pac1 fixed-4 step3" t03 t22 t23 t25

# same modes for PAC1 environment
./run-codex-evolve.sh solve --env pac1 --all
./run-codex-evolve.sh full-step --env pac1 --hypothesis "..."
./run-codex-evolve.sh autopilot --env pac1 --n 2 --no-improve-limit 2 --hypothesis "..."
```

Artifacts:

- active prompt version: `prompts/active_version.txt`
- prompt packs: `prompts/versions/*.json`
- prompt changelog: `CHANGELOG_PROMPTS.jsonl`
- code proposals queue: `CODE_PROPOSALS.jsonl`
- code version marker: `CODE_VERSION`

Environment:

- `OMNIROUTE_API_KEY` (required for Codex)
- `BITGN_OMNIROUTE_KEY_FILE` (optional key file path if env is not set)
- `CODEX_MODEL` (default: `gpt-5.3-codex`)
- `BENCHMARK_HOST` (default: `https://api.bitgn.com`)
- `BENCHMARK_ID` (default: `bitgn/sandbox`)
- `BITGN_API_KEY` (optional: enables leaderboard run flow `start_run/start_trial/submit_run`)
- `BITGN_RUN_NAME` (optional: leaderboard run display name)

Recommended key location per machine: `$HOME/.codex/omniroute-api-key` (`chmod 600`).

Time display:
- Run summaries and analyze reports include UTC plus MSK (`Europe/Moscow`) start/end timestamps.

## Known limitation

- Use `--parallelism N` (or alias `--parallels N`) to parallelize task execution inside each solve step.
- Do not run multiple `full-step`/`autopilot` processes in parallel against one workspace because they share prompt/version artifacts.
