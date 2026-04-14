# Rules and Prompt Evolution Principles

This document explains how we evolve native solver behavior in a controlled way.

## 1) What can evolve

Evolution is not limited to one file.

A rules version (`rvXXXX`) may include:

- `rules_versions/rvXXXX/AGENTS.md` (core policy)
- `rules_versions/rvXXXX/includes/*.md` (modular policy extensions)

`deploy` performs a full replace of native `local-rules/`, so behavior changes can come from both the core file and includes.

In rare blocking cases, evolution may escalate to code changes, but the default path is rules/prompt behavior.

## 2) The evolution unit

One iteration should target one primary failure mode.

Required unit fields:

- primary task,
- evidence-backed problem statement,
- one hypothesis,
- affected-task validation scope,
- rollback note.

This keeps causality clear: we can explain exactly which change fixed which failure.

## 3) Prompt evolution model

We evolve behavior across two prompt layers:

1. Runtime solver policy (native):

- local rules injected into the Codex session (`AGENTS.md` + optional includes),
- task instruction + tool contract.

2. Analyzer policy (analytics):

- analyze/apply/deploy prompt contracts in `codex-agent-analytics/docs/instructions/`.

Reference note:

- The harness engineering article/map is available as an optional reference (`codex-agent-analytics/docs/references/harness-engineering-structure-draft.md`).
- It is not mandatory policy input for every analysis run, but the analyzer can consult it when shaping higher-level recommendations.

Practical rule:

- If the solver made a bad decision on a valid tool path, evolve runtime rules first.
- If proposal quality/process is poor (bad diagnosis, oversized diffs, weak generalization), evolve analyzer prompts/contracts.

## 4) Core principles

1. Harness-first

- Prefer policy/rules changes over code changes.
- Escalate to code only when rules are proven insufficient.

2. Minimal and reversible

- Keep diffs small.
- Every proposal must have a clear rollback path.

3. Generalize, do not memorize

- No task-specific answers, IDs, or one-off hacks in policy text.
- Encode reusable decision gates (ambiguity, safety, scope, write discipline).

4. Safety and authorization precedence

- Security and scope checks outrank convenience completion.
- When uncertain on sensitive actions, prefer clarify/deny outcomes over unsafe `OUTCOME_OK`.

5. Deterministic completion discipline

- Task completion is valid only via `report_completion`.
- Rules should improve pre-completion decisions, not bypass the completion contract.

## 5) How we choose where to change

Use this decision order:

1. `AGENTS.md` when the fix is a global policy correction.
2. `includes/*.md` when the fix is narrow/modular and should be isolated.
3. Analyzer instruction docs when the issue is in diagnosis/proposal/apply behavior.
4. Code only for proven blocking constraints.

## 6) Validation ladder

After deploy, validate in this order:

1. targeted rerun (primary task),
2. risk cluster rerun (likely affected tasks),
3. full smoke run,
4. leaderboard run only after local green.

If any regression appears, start a new focused iteration from that regression.

## 7) Hard guardrails (current)

Runtime/local-rules limits (enforced by native runner):

- `local-rules/AGENTS.md` line limit is configurable via `LOCAL_RULES_MAX_AGENTS_LINES` (default `156`; historical baseline was `100`).
- include files must live under `includes/*.md`.
- max include files: 8.
- max lines per include file: 80.
- max total include lines: 220.

Operational run controls (native runner):

- Arbitrary task order is supported: tasks are executed in the exact CLI order.
- `--fail-fast` is supported: after first fail, new scheduling stops (inflight tasks complete when parallelism > 1).

Analytics apply limits (enforced in `apply` flow):

- changed-lines limit per apply:
  - <= 80 when no include file is produced,
  - <= 100 when include file(s) are produced.
- generated include files in one apply are capped (currently `includes_count <= 1`).

These limits are intentional: they keep each evolution step small, reviewable, and safer to roll back.

## 8) Acceptance criteria

A change is accepted when:

- primary failure is fixed,
- risk cluster does not regress,
- full smoke is green,
- artifacts are complete (`proposal -> apply -> deploy -> validation evidence`).

## 9) Source artifacts for decisions

- `run_manifest.jsonl`
- per-task `score.json`
- `tool_calls.jsonl`, `events.jsonl`
- analytics outputs in `analysis/`, `reports/`, `proposals/`, `applies/`, `deploy/`

## 10) Important non-regression caveat

Provider/model entitlement failures are not prompt/rules regressions.

If a model cannot start (model gate), compare quality only across runs that produced real task scores.
