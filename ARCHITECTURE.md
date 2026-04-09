# Native + Analytics Architecture

This document explains how the current BitGN native stack works at a high level.

## 1) Core idea

The system is split into two layers:

- `codex-agent-native` executes benchmark tasks and records full artifacts.
- `codex-agent-analytics` analyzes failed runs and evolves local rules in a controlled way.

The Python layer is an orchestration shell. The actual task-solving "engine" is Codex itself.

## 2) What the Python shell does

Native runner (`codex-agent-native/runner.py`) handles:

- task selection and parallel execution (`ThreadPoolExecutor`),
- trial bootstrapping (`start_playground` for smoke or `start_run/start_trial` for leaderboard),
- per-task isolated workspace creation,
- launching one Codex session per task,
- finishing trial (`end_trial`) and writing scores,
- appending one row per task into `run_manifest.jsonl`.

It does not implement a Python step-by-step planner for solving logic.

## 3) What Codex does (solver core)

Per task, runner starts Codex via:

- `codex exec --json --output-last-message ... --model <CODEX_MODEL>`

Codex receives a synthesized prompt that includes:

- local rules snapshot,
- task instruction,
- tool contract (`runtime_tools.py`).

Codex decides which tools to call, in what order, and when to finish.

## 4) How tool calls work

Inside the Codex session, tool execution is done through shell commands:

- `python runtime_tools.py <tool> key=value ...`

Flow:

1. `runtime_tools.py` parses args and resolves `NATIVE_TASK_WORKSPACE`.
2. It loads `ToolGateway` from `task_context.json`.
3. `ToolGateway` dispatches calls to sandbox or PAC1 VM APIs.
4. Every call is logged to `tool_calls.jsonl`.
5. For completion, `report_completion` writes `submission.json` and sends VM answer.

If Codex exits without `report_completion`, runner marks the task as error.

## 5) Structured output: yes and no

There is no global JSON schema enforced for Codex final response in this runtime:

- runner does not use `--output-schema`.

What is structured instead:

- Codex event stream is JSON (`--json`) and is persisted,
- completion contract is strict via tool API:
  - sandbox: `report_completion(answer, grounding_refs)`
  - pac1: `report_completion(message, outcome, grounding_refs)`

So structure is enforced at the tool boundary, not as a model-wide output schema.

## 6) Session and artifact persistence

For each task attempt:

- `events.jsonl` (stage timeline),
- `tool_calls.jsonl` (all runtime tool calls),
- `submission.json` (completion payload),
- `score.json` (score, details, usage, steps),
- `session/codex_prompt.txt` (exact prompt),
- `session/codex_session_raw.jsonl` (raw Codex JSONL output),
- `session/codex_session_parsed.jsonl` (parsed events),
- `session/codex_session_meta.json` (duration, model, token usage),
- `session/codex_last_message.json`.

Run-level summary:

- `runs/<local_run_id>/run_manifest.jsonl`.

## 7) Task solve lifecycle

For each task, high-level lifecycle is:

1. `TASK_START`
2. Workspace + rules snapshots
3. `CODEX_SESSION_START`
4. Codex executes tools through `runtime_tools.py`
5. `report_completion` writes `submission.json`
6. Runner calls `end_trial`
7. `score.json` + `run_manifest.jsonl` append
8. `TRIAL_FINISH`

If any stage fails, failure is still persisted in workspace and manifest.

## 8) Evolution loop (native + analytics)

High-level iteration:

1. Solve on smoke scope (single task / risk cluster / full).
2. Analyze failures with `run-codex-analytics.sh analyze`.
3. Generate proposal(s) for rules/code.
4. Apply one proposal into a new rules version (`rvXXXX`).
5. Deploy that version to native local rules.
6. Re-validate targeted tasks, then risk cluster, then full smoke.
7. Submit leaderboard run only after local green.

This keeps solver behavior adaptive while preserving auditability and rollback paths.
