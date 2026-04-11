# Архитектура Native + Analytics

Этот документ описывает текущий BitGN native-стек на верхнем уровне.

## 1) Базовая идея

Система разделена на два слоя:

- `codex-agent-native` исполняет benchmark-задачи и сохраняет полные артефакты.
- `codex-agent-analytics` анализирует fail-run и эволюционирует локальные правила в управляемом формате.

Python-слой здесь — orchestration shell. Реальный "solver engine" — это сам Codex.

## 2) Что делает Python shell

Native runner (`codex-agent-native/runner.py`) отвечает за:

- выбор задач и параллельное исполнение (`ThreadPoolExecutor`),
- trial bootstrapping (`start_playground` для smoke или `start_run/start_trial` для leaderboard),
- создание изолированного workspace на задачу,
- запуск одной Codex session на задачу,
- завершение trial (`end_trial`) и запись score,
- добавление одной строки на задачу в `run_manifest.jsonl`.

Python не реализует пошаговый planner логики решения.

## 3) Что делает Codex (ядро решения)

Для каждой задачи runner запускает Codex через:

- `codex exec --json --output-last-message ... --model <CODEX_MODEL>`

Codex получает синтезированный prompt, который включает:

- снимок local rules,
- task instruction,
- tool contract (`runtime_tools.py`).

Codex сам решает, какие tools вызывать, в каком порядке и когда завершать задачу.

## 4) Как работают tool calls

Внутри Codex session инструменты исполняются shell-командами:

- `python runtime_tools.py <tool> key=value ...`

Flow:

1. `runtime_tools.py` парсит аргументы и резолвит `NATIVE_TASK_WORKSPACE`.
2. Загружает `ToolGateway` из `task_context.json`.
3. `ToolGateway` маршрутизирует вызовы к sandbox или PAC1 VM API.
4. Каждый вызов логируется в `tool_calls.jsonl`.
5. Для completion `report_completion` пишет `submission.json` и отправляет ответ в VM.

Если Codex завершился без `report_completion`, runner помечает задачу ошибкой.

## 5) Structured output: да и нет

Глобальная JSON schema для финального ответа Codex в этом runtime не форсится:

- runner не использует `--output-schema`.

Что структурировано вместо этого:

- event stream Codex идет в JSON (`--json`) и сохраняется,
- completion contract строгий на границе tool API:
  - sandbox: `report_completion(answer, grounding_refs)`
  - pac1: `report_completion(message, outcome, grounding_refs)`

То есть структура обеспечивается на tool-boundary, а не общей model-wide schema.

## 6) Сохранение сессий и артефактов

Для каждой task attempt сохраняется:

- `events.jsonl` (timeline стадий),
- `tool_calls.jsonl` (все runtime tool calls),
- `submission.json` (completion payload),
- `score.json` (score, details, usage, steps),
- `session/codex_prompt.txt` (точный prompt),
- `session/codex_session_raw.jsonl` (raw Codex JSONL output),
- `session/codex_session_parsed.jsonl` (parsed events),
- `session/codex_session_meta.json` (duration, model, token usage),
- `session/codex_last_message.json`.

Run-level summary:

- `runs/<local_run_id>/run_manifest.jsonl`.

## 7) Жизненный цикл решения задачи

Для каждой задачи lifecycle такой:

1. `TASK_START`
2. Workspace + snapshots правил
3. `CODEX_SESSION_START`
4. Codex исполняет инструменты через `runtime_tools.py`
5. `report_completion` пишет `submission.json`
6. Runner вызывает `end_trial`
7. Записываются `score.json` + строка в `run_manifest.jsonl`
8. `TRIAL_FINISH`

Если любая стадия падает, failure все равно сохраняется в workspace и manifest.

## 8) Цикл эволюции (native + analytics)

Итерация верхнего уровня:

1. Solve на smoke-scope (одна задача / risk cluster / full).
2. Analyze fail-задач через `run-codex-analytics.sh analyze`.
3. Генерация proposal(ов) для rules/code.
4. Apply одного proposal в новую rules version (`rvXXXX`).
5. Deploy этой версии в native local rules.
6. Повторная валидация: target -> risk cluster -> full smoke.
7. Leaderboard run только после локального green.

Такой цикл делает solver поведение адаптивным, сохраняя аудитируемость и rollback path.
