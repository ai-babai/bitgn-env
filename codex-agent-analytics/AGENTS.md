# AGENTS.md - codex-agent-analytics

Purpose: run Codex analysis/apply/deploy stages around native solve artifacts.

## Scope

- `analyze` is read-only toward `../codex-agent-native/runs/`.
- `apply` only modifies `rules_versions/*/AGENTS.md` in this project.
- `deploy` only updates `../codex-agent-native/local-rules/AGENTS.md` with backup.
- Do not apply runtime code changes automatically.

## Analyze contract

- Work per task workspace from source local run.
- Produce improvement proposals only.
- Proposal types:
  - `rules` (harness/local-rules guidance improvements)
  - `code` (runner/tooling/runtime bug fixes)

## Modes

- `analyze`: generate focused rules-first proposals from native runs.
- `apply`: apply one selected rules proposal into a new rules version.
- `deploy`: deploy selected rules version to native local-rules.

Instruction map:

- Start with `docs/instructions/index.md`.
- Keep policy details in docs; avoid embedding policy text in code where possible.
- Follow `docs/instructions/target-path-policy.md` for target file validation and normalization.

Harness-first policy:

- Default to harness/rules proposals.
- Treat each iteration as one focused problem -> one focused harness solution.
- Escalate to code only when analyzer explicitly proves harness is insufficient.

Code proposal policy:

- Always classify code need as `blocking` or `optional`.
- If `optional`, do not emit a code proposal item.
- If `blocking`, include explicit `blocker_reason` linked to run evidence and why rules are insufficient.

## Proposal quality gates

- Rules proposals must be generalizable.
- Avoid task-specific literals (task ids, exact expected values, one-off file paths).
- Prefer small reversible steps.
- Each proposal must include hypothesis and rollback plan.

## Output discipline

- Save machine artifacts (`analysis/*.json`, `*_PROPOSALS.jsonl`).
- Save readable artifacts (`reports/*.md`, `proposals/*/*.md`).
- Keep text concise and evidence-linked to source task artifacts.
