# codex-agent-native (MVP)

Минимальный подпроект для автономного контура:

- 1 local run = набор выбранных задач, и у каждой задачи свой уникальный task workspace
- Python НЕ крутит пошаговый loop за Codex
- Запускается одна Codex-сессия на задачу (`codex exec`)
- Codex сам вызывает runtime tools через `python runtime_tools.py ...`
- Completion отправляется через `report_completion`, затем `end_trial`
- Полные task-артефакты сохраняются в `runs/...`
- Правила разделены: `local-rules` (наши) и `bitgn-rules` (снимок runtime)

## Что такое "без wrapper-цикла"

- Wrapper отвечает только за orchestration: `start_playground` -> запуск сессии -> `end_trial`.
- Внутри сессии Codex сам решает:
  - какие tools вызывать,
  - в каком порядке,
  - когда завершать задачу.
- `runtime_tools.py` — это runtime-шлюз и логгер инструментов.

## Текущий режим запуска Codex

- Для отладки tool-calls Codex запускается без sandbox-ограничений (`--dangerously-bypass-approvals-and-sandbox`).
- Fallback completion в runner отключен: если агент не отправил `report_completion`, run падает с ошибкой.

## Live logs в CLI

- Runner печатает стадии: `TASK_START`, `WORKSPACE_READY`, `LOCAL_RULES_SNAPSHOT`, `BITGN_RULES_HYDRATION`, `CODEX_SESSION_START/END`, `TRIAL_FINISH`.
- Во время Codex-сессии отображаются события turn/tool start/tool done.
- `runtime_tools.py` печатает `TOOL_CALL`, `TOOL_OK`, `TOOL_ERR` для каждого tool-вызова.
- Уровень подробности: `NATIVE_LOG_LEVEL=info|debug`.
- Полная сессия Codex сохраняется в workspace (`codex_session_raw.jsonl`, `codex_session_parsed.jsonl`, `codex_session_meta.json`, `codex_prompt.txt`).

## Local rules / BitGN rules

- Локальная папка: `codex-agent-native/local-rules/`
- Обязательный файл: `codex-agent-native/local-rules/AGENTS.md` (не более 100 строк)
- Дополнительные правила: `codex-agent-native/local-rules/includes/*.md` через директивы `!include includes/<name>.md` в `AGENTS.md`
- Включения не могут быть вложенными; используются только файлы внутри `includes/`
- В runtime ничего не записываем для правил (BitGN не уведомляется об этом)
- В системной инструкции Codex локальные правила вшиты как default context
- Для визуальной проверки в run-артефактах пишется `initial_files/local-rules/`
- Снимок BitGN policy-файлов пишется отдельно в `initial_files/bitgn-rules/`

## Запуск одной задачи

```bash
cd /Users/skif/develop/bitgn-env
./run-codex-native.sh --env pac1 t01
```

или напрямую:

```bash
cd /Users/skif/develop/bitgn-env/codex-agent-native
BENCHMARK_ID=bitgn/pac1-dev AGENT_ENV=pac1 uv run python runner.py t01
```

## Запуск нескольких задач в одном local run

```bash
cd /Users/skif/develop/bitgn-env
./run-codex-native.sh --env pac1 t01 t02 t03
```

С параллелизмом (короткий флаг):

```bash
./run-codex-native.sh --env pac1 -p 2 t01 t02 t03 t04
```

- Все задачи запуска будут объединены одним `local_run_id`.
- Для каждой задачи создается отдельный workspace:
  - `runs/<local_run_id>/<task_id>/attempt_<...>/`
- Сводка по local run пишется в:
  - `runs/<local_run_id>/run_manifest.jsonl`
- По умолчанию `parallelism=2` (можно изменить `-p` или `NATIVE_PARALLELISM`).

## Снять контекст задачи без Codex

```bash
cd /Users/skif/develop/bitgn-env/codex-agent-native
uv run python snapshot_task_context.py t03 --env pac1
```

Скрипт не запускает агента: он сохраняет instruction, структуру файлов, ключевые policy/docs и краткое summary в `task-context-snapshots/`.

## Артефакты задачи

По умолчанию:

`/Users/skif/develop/bitgn-env/codex-agent-native/runs/<local_run_id>/<task>/<attempt>/`

Содержимое:

- `instruction.txt`
- `initial_files/` (разделенный снимок: `local-rules/` и `bitgn-rules/`; при ограничениях чтения добавляется `TASK_INSTRUCTION.md`)
- `events.jsonl`
- `tool_calls.jsonl`
- `agent_session.jsonl`
- `task_context.json`
- `submission.json`
- `score.json`
- `meta.json`
- `session/codex_last_message.json`
- `session/codex_prompt.txt`
- `session/codex_session_raw.jsonl`
- `session/codex_session_parsed.jsonl`
- `session/codex_session_meta.json`

## Важные env

- `OMNIROUTE_API_KEY` (обязателен для Codex)
- `BITGN_OMNIROUTE_KEY_FILE` (опционально: путь к key file, если не задан env)
- `CODEX_MODEL` (по умолчанию `gpt-5.3-codex`)
- `BENCHMARK_HOST` (по умолчанию `https://api.bitgn.com`)
- `BENCHMARK_ID` (`bitgn/sandbox` или `bitgn/pac1-dev`)
- `AGENT_ENV` (`sandbox` или `pac1`)
- `NATIVE_SESSION_TIMEOUT_SEC` (по умолчанию `420`)
- `NATIVE_RUNS_DIR` (база для task workspaces)

Рекомендация: хранить ключ в `$HOME/.codex/omniroute-api-key` с правами `600`.
