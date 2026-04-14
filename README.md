# bitgn-env

Workspace for BitGN runs with focus on the native Codex solver and analytics-driven evolution.

English | [Русская версия](./README.ru.md)

## PAC leaderboard

- Challenge page: https://bitgn.com/challenge/PAC
- PAC is a benchmark where the agent executes inbox/ops workflows inside constrained task workspaces and is scored on exact outcome correctness, file mutations, and grounding references.

Current public status:

- Competition-day blind run baseline: <=100-line `AGENTS.md`, 6th place, `84/104` (84 points) on `pac1-prod`: https://bitgn.com/l/pac1-prod
- Current stabilized setup: default 156-line cap (`LOCAL_RULES_MAX_AGENTS_LINES=156`) and `104/104` solved.

## Quick links

- Architecture: [`ARCHITECTURE.md`](./ARCHITECTURE.md)
- Rules evolution policy: [`RULES_EVOLUTION_PRINCIPLES.md`](./RULES_EVOLUTION_PRINCIPLES.md)
- Active local rules: [`codex-agent-native/local-rules/AGENTS.md`](./codex-agent-native/local-rules/AGENTS.md)

## How It Works (short)

This setup is almost a meme - but it works:

- `AGENTS.md` policy brain - compact and operator-controlled (historical baseline used <=100 lines; current native default limit is 156).
- Codex CLI - runs the actual task session.
- Tool wrapper - exposes only the PAC-relevant tools to Codex.
- Model: `gpt-5.3-codex` - current default solver.

In short: `100-line policy file -> Codex session -> constrained tools -> scored result`.

Historical baseline:

- The original <=100-line `AGENTS.md` setup reached 6th place with `84/104` solved on `pac1-prod`: https://bitgn.com/l/pac1-prod
- The current loop reached `104/104` by improving rule quality and run orchestration (not by task-specific answer hardcoding).

## Architecture (high level)

This repo uses a two-module loop:

- `codex-agent-native`: executes benchmark tasks and produces full task artifacts.
- `codex-agent-analytics`: reads native artifacts, finds failure patterns, proposes rule updates, and deploys new rule versions.

The key idea is to keep runtime solving and post-run analysis separated:

- native runner optimizes for reliable execution and traceability,
- analytics runner optimizes for controlled, auditable policy evolution.

## Main components

- `run-codex-native.sh`: entry wrapper for native runs (sandbox/pac1, parallelism, model, leaderboard flags).
- `codex-agent-native/runner.py`: orchestrates `start_playground/start_trial`, per-task workspace creation, Codex session execution, scoring, and manifest writing.
- `codex-agent-native/runtime_tools.py`: tool gateway exposed to Codex during solve.
- `codex-agent-native/local-rules/AGENTS.md`: active local policy used by native solver.
- `run-codex-analytics.sh`: entry wrapper for `analyze | apply | deploy` workflows.
- `codex-agent-analytics/cli.py`: analytics pipeline control plane.
- `codex-agent-analytics/rules_versions/`: versioned policy snapshots (`rvXXXX`).

## Evolution cycle (top level)

Typical iteration:

1. **Solve**: run native on selected scope (single task, risk cluster, or full benchmark).
2. **Analyze**: inspect failed tasks and generate proposals.
3. **Apply**: apply one approved proposal into a new rules version.
4. **Deploy**: copy selected rules version to `codex-agent-native/local-rules/AGENTS.md`.
5. **Validate**: rerun targeted tasks and risk cluster; if green, run full smoke; then optional leaderboard run.

This loop gives fast local iteration with controlled blast radius before leaderboard submissions.

## Quick commands

### Native solve

```bash
cd bitgn-env

# single PAC1 task
./run-codex-native.sh --env pac1 t01

# full PAC1 (auto-resolve all tasks from benchmark)
./run-codex-native.sh --env pac1 --all -p 5

# full PAC1 (explicit task list)
./run-codex-native.sh --env pac1 -p 5 t{01..43}

# full PAC1 with custom order + fail-fast
./run-codex-native.sh --env pac1 --fail-fast -p 9 t03 t17 t28 t01 t02
```

Notes:

- Native runner executes tasks in the exact order passed in CLI.
- `--fail-fast` stops scheduling after the first failed task (inflight tasks finish when parallelism > 1).

### Backend selection (Spark / OmniRoute)

```bash
# Spark/direct Codex backend (uses ChatGPT login or selected codex profile)
CODEX_BACKEND=spark ./run-codex-native.sh --env pac1 t01

# Spark + explicit profile (if you configured one in ~/.codex/config.toml)
CODEX_BACKEND=spark CODEX_PROFILE=<your-spark-profile> ./run-codex-native.sh --env pac1 t01

# OmniRoute backend (current default)
CODEX_BACKEND=omniroute ./run-codex-native.sh --env pac1 t01
```

Notes:

- `CODEX_PROFILE` is optional; if set, it is passed to `codex exec --profile <name>`.
- If `CODEX_BACKEND=spark` and `CODEX_PROFILE` is empty, wrappers force direct provider via `-c model_provider=openai`.
- OmniRoute key is required only when `CODEX_BACKEND=omniroute`.

### Smoke mode (no leaderboard)

```bash
BITGN_API_KEY='' BITGN_API_KEY_FILE='/tmp/bitgn-no-key' \
BITGN_RUN_NAME='[@skifmax]-[codex]-[chiki-banboni]-[smoke]' \
./run-codex-native.sh --env pac1 -p 5 t{01..43}
```

### Leaderboard mode

```bash
BITGN_RUN_NAME='[@skifmax]-[codex]-[chiki-banboni]-[xNNN]' \
./run-codex-native.sh --env pac1 --all -p 5
```

See leaderboard standings and run comparisons at https://bitgn.com/challenge/PAC.

### Analytics evolution

```bash
# analyze one failed task from a local run
./run-codex-analytics.sh analyze --env pac1 --run-id <local_run_id> -p 1 --focus-task t36 t36

# apply selected proposal from an existing rules version
./run-codex-analytics.sh apply --proposal-id prop-001 --from-version rv0038

# deploy resulting rules version to native local-rules
./run-codex-analytics.sh deploy --rules-version rv0039 --yes
```

## Artifacts and observability

- Native run root: `codex-agent-native/runs/<local_run_id>/`
- Per-task workspace: `codex-agent-native/runs/<local_run_id>/<task_id>/attempt_<timestamp>_<id>/`
- Run manifest: `codex-agent-native/runs/<local_run_id>/run_manifest.jsonl`
- Per-task score: `.../score.json` (pass/fail, score details, tokens, steps)

Analytics artifacts:

- analysis summary: `codex-agent-analytics/analysis/aXXXX.json`
- report: `codex-agent-analytics/reports/rXXXX.md`
- proposals: `codex-agent-analytics/proposals/rules/<rv>/prop-XXX.md`
- apply/deploy reports: `codex-agent-analytics/applies/aXXXX.md`, `codex-agent-analytics/deploy/dXXXX.md`

## Configuration notes

- Backend switch: `CODEX_BACKEND=omniroute|spark` (default: `omniroute`).
- Optional profile override for Codex CLI: `CODEX_PROFILE=<profile-name>`.
- OmniRoute key for Codex flows: `OMNIROUTE_API_KEY` (required only for `CODEX_BACKEND=omniroute`).
- Wrapper key resolution order:
  1. `OMNIROUTE_API_KEY` env
  2. `BITGN_OMNIROUTE_KEY_FILE`
  3. `$HOME/.codex/omniroute-api-key`
- Native model override: `CODEX_MODEL` (default `gpt-5.3-codex`).
- Native parallelism: `-p` / `--parallelism` or `NATIVE_PARALLELISM`.
- Native local-rules line cap: `LOCAL_RULES_MAX_AGENTS_LINES` (default `156`).

## Related docs

- Native details: [`codex-agent-native/README.md`](./codex-agent-native/README.md)
- Analytics details: [`codex-agent-analytics/README.md`](./codex-agent-analytics/README.md)
- Architecture deep dive: [`ARCHITECTURE.md`](./ARCHITECTURE.md)
- Rule design and evolution policy: [`RULES_EVOLUTION_PRINCIPLES.md`](./RULES_EVOLUTION_PRINCIPLES.md)
- Active local rules: [`codex-agent-native/local-rules/AGENTS.md`](./codex-agent-native/local-rules/AGENTS.md)
- BitGN runs dashboard: https://preview.mipopkov.com
- Provider reference: [`OmniRoute`](https://github.com/diegosouzapw/OmniRoute/) — commonly used backend provider for `CODEX_BACKEND=omniroute`
- Root-level navigation/rules on this machine: [`AGENTS.md`](./AGENTS.md)

## Contact

- Maksim Popkov
- Telegram: `@skifmax`
- Email: `contact.popkov@yandex.com`
- Sites: https://mipopkov.com, https://mipopkov.ru
