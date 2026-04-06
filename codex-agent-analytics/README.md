# codex-agent-analytics

Analysis-only companion project for `codex-agent-native`.

It reads solve artifacts from native runs and runs Codex analysis sessions per task workspace to produce proposals.

## Principles

- Separate module from solver runtime.
- Read-only access to `../codex-agent-native/runs`.
- No automatic code changes.
- Proposal artifacts are traceable and reversible.
- Best-practice harness map is tracked as draft in `docs/references/harness-engineering-structure-draft.md`.
- Harness-first by default: prefer rules and process updates; code proposals only for proven blockers.

## Modes

- `analyze`: run Codex analysis on selected tasks from a chosen local run.
- `apply`: apply one approved rules proposal into a new rules version.
- `deploy`: deploy selected rules version into native local-rules (full replace).

## Instruction docs

- `docs/instructions/index.md` - entrypoint for analyzer behavior rules.

## Run

```bash
cd /Users/skif/develop/bitgn-env
./run-codex-analytics.sh analyze --env pac1 --run-id local_run_20260403T212858Z_55860 -p 2 t01 t03
./run-codex-analytics.sh apply --proposal-id prop-001 --from-version rv0001
./run-codex-analytics.sh deploy --rules-version rv0002 --dry-run
```

## Artifacts

- `analysis/aXXXX.json` - machine summary for one analytics run
- `reports/rXXXX.md` - readable summary
- `proposals/rules/<rules_version>/prop-XXX.md` - rules proposals
- `rules_versions/<rules_version>/includes/*.md` - optional modular rule extensions
- `proposals/code/<code_version>/prop-XXX.md` - code proposals
- `RULES_PROPOSALS.jsonl` - queue of rules proposals
- `CODE_PROPOSALS.jsonl` - queue of code proposals
- `applies/aXXXX.md` - apply reports/plans
- `APPLY_LOG.jsonl` - apply event log
- `deploy/dXXXX.md` - deploy reports/plans
- `DEPLOY_LOG.jsonl` - deploy event log
