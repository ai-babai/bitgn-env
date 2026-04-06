# bitgn-env

Local workspace for BitGN sample runs via OmniRoute.

## Quick start

```bash
cd /Users/skif/develop/bitgn-env

# sandbox smoke (defaults to t01 t02)
./run-sandbox.sh --sync

# sandbox full benchmark
./run-sandbox.sh --all

# PAC1 single task
./run-pac1.sh --sync t01

# Codex-core sandbox single task
./run-codex-sandbox.sh --sync t01

# Codex evolution pipeline modes
./run-codex-evolve.sh solve --all
./run-codex-evolve.sh solve --parallelism 2 t01 t02
./run-codex-evolve.sh analyze
./run-codex-evolve.sh propose-prompts
./run-codex-evolve.sh propose-code
./run-codex-evolve.sh apply-prompts --hypothesis "..."
./run-codex-evolve.sh full-step --hypothesis "..."
./run-codex-evolve.sh full-step --env pac1 --parallelism 2 --hypothesis "..." t03 t22
./run-codex-evolve.sh autopilot --n 3 --no-improve-limit 2 --hypothesis "..."
./run-codex-evolve.sh autopilot --env pac1 --parallelism 2 --n 3 --no-improve-limit 999 --task-scope affected t03 t22

# run prompt evolution on affected tasks only
./run-codex-evolve.sh full-step --env pac1 --task-scope affected --affected-from last-apply --max-affected 6 --hypothesis "..."
./run-codex-evolve.sh autopilot --env pac1 --task-scope affected --affected-from last-apply --max-affected 8 --n 2 --no-improve-limit 2 --hypothesis "..."

# autopilot with fixed task ids (same tasks every step)
./run-codex-evolve.sh autopilot --env pac1 --n 3 --no-improve-limit 999 --hypothesis "pac1 fixed-4" t03 t22 t23 t25

# autopilot with fixed task ids + affected behavior
# (next iterations keep only still-failing tasks from this fixed set)
./run-codex-evolve.sh autopilot --env pac1 --task-scope affected --n 3 --no-improve-limit 999 --hypothesis "pac1 fixed-4 affected" t03 t22 t23 t25

# classic fixed-scope evolution (same 4 tasks, 3 sequential iterations)
./run-codex-evolve.sh full-step --env pac1 --hypothesis "pac1 fixed-4 step1" t03 t22 t23 t25
./run-codex-evolve.sh full-step --env pac1 --hypothesis "pac1 fixed-4 step2" t03 t22 t23 t25
./run-codex-evolve.sh full-step --env pac1 --hypothesis "pac1 fixed-4 step3" t03 t22 t23 t25

# same as above, wrapped in one script
./run-pac1-fixed4-evo3.sh

# run codex-agent against PAC1 env
./run-codex-evolve.sh solve --env pac1 --all

# codex-native MVP (one task, isolated workspace)
./run-codex-native.sh --env pac1 t01

# all CLI/report timestamps are shown in UTC and MSK (Europe/Moscow)

# show latest unified task-run table
./runlog-latest.sh
```

## Notes

- For Codex agents, use only `OMNIROUTE_API_KEY`.
- For Codex scripts (`run-codex-*.sh`) key resolution order is:
  1. `OMNIROUTE_API_KEY` from environment
  2. `BITGN_OMNIROUTE_KEY_FILE`
  3. `$HOME/.codex/omniroute-api-key`
- Recommended per-machine setup (local and server):
  - store key at `$HOME/.codex/omniroute-api-key`
  - `chmod 600 $HOME/.codex/omniroute-api-key`
- You can override model/base URL via env:
  - `MODEL_ID=codex/gpt-5.3-codex-high OPENAI_BASE_URL=https://omni.mipopkov.com/v1 ./run-sandbox.sh`
- For Codex-core runner:
  - `CODEX_MODEL=gpt-5.3-codex ./run-codex-sandbox.sh t01`
- For Codex-native MVP runner:
  - `CODEX_MODEL=gpt-5.3-codex ./run-codex-native.sh --env pac1 t01`
- Task parallelism inside solve/evolution is supported via `--parallelism N` (alias: `--parallels N`).
- Do not run multiple `full-step`/`autopilot` processes in parallel against one workspace because prompt/version artifacts are shared.

## Logging

- Runners write JSONL logs to `/Users/skif/develop/bitgn-env/logs/`
- Override log directory with `BITGN_LOG_DIR=/path/to/logs`
- Logged events include:
  - run/task start+finish
  - task instruction
  - prompt sections (system + steering)
  - agent reasoning/tool steps
  - submission payload
  - score details + expected hints (when parseable)

## Unified run registry (task-run as atomic unit)

- Registry home (default): `/Users/skif/develop/runlog-registry`
- Main files:
  - `/Users/skif/develop/runlog-registry/index/runs.jsonl`
  - `/Users/skif/develop/runlog-registry/index/task_runs.jsonl`
- Every task attempt is written as one `task_run` row (including partial runs)
- Quick view of latest run:
  - `./runlog-latest.sh`
