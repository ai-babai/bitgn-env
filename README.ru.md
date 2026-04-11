# bitgn-env

Рабочее пространство для запусков BitGN с фокусом на native Codex solver и эволюцию правил через analytics.

[English version](./README.md) | Русская версия

## PAC leaderboard

- Страница челленджа: https://bitgn.com/challenge/PAC
- PAC — это benchmark, где агент выполняет inbox/ops workflow в ограниченных task-workspace и оценивается по точности outcome, мутациям файлов и grounding references.

## Быстрые ссылки

- Архитектура: [`ARCHITECTURE.ru.md`](./ARCHITECTURE.ru.md)
- Принципы эволюции правил: [`RULES_EVOLUTION_PRINCIPLES.ru.md`](./RULES_EVOLUTION_PRINCIPLES.ru.md)
- Активные локальные правила: [`codex-agent-native/local-rules/AGENTS.md`](./codex-agent-native/local-rules/AGENTS.md)

## Как это работает (кратко)

Эта схема выглядит почти как мем — но работает:

- `AGENTS.md` (<= 100 строк) — компактный policy brain.
- Codex CLI — запускает саму task-сессию.
- Tool wrapper — отдает Codex только PAC-релевантные инструменты.
- Модель: `gpt-5.3-codex` — текущий solver по умолчанию.

Итого: `100-line policy file -> Codex session -> constrained tools -> scored result`.

## Архитектура (верхний уровень)

В репозитории используется двухмодульный цикл:

- `codex-agent-native`: исполняет benchmark-задачи и сохраняет полные task-артефакты.
- `codex-agent-analytics`: читает артефакты native run, находит паттерны фейлов, предлагает обновления правил и деплоит новые версии.

Ключевая идея — разделить runtime solving и post-run analysis:

- native runner оптимизирован под надежное исполнение и трассируемость,
- analytics runner оптимизирован под управляемую, аудитируемую эволюцию policy.

## Основные компоненты

- `run-codex-native.sh`: entry wrapper для native run (sandbox/pac1, parallelism, model, leaderboard flags).
- `codex-agent-native/runner.py`: orchestration `start_playground/start_trial`, создание task-workspace, запуск Codex session, scoring, запись manifest.
- `codex-agent-native/runtime_tools.py`: tool gateway, доступный Codex во время solve.
- `codex-agent-native/local-rules/AGENTS.md`: активная локальная policy для native solver.
- `run-codex-analytics.sh`: entry wrapper для `analyze | apply | deploy`.
- `codex-agent-analytics/cli.py`: control plane analytics pipeline.
- `codex-agent-analytics/rules_versions/`: версионированные policy snapshots (`rvXXXX`).

## Цикл эволюции (верхний уровень)

Типичная итерация:

1. **Solve**: native run на нужном scope (одна задача, risk cluster или full benchmark).
2. **Analyze**: анализ fail-задач и генерация proposal.
3. **Apply**: применение одного одобренного proposal в новую версию правил.
4. **Deploy**: копирование выбранной версии в `codex-agent-native/local-rules/AGENTS.md`.
5. **Validate**: rerun фокусных задач и risk-cluster; если green — full smoke; затем опционально leaderboard.

Такой цикл дает быстрые локальные итерации с контролируемым blast radius до leaderboard submissions.

## Быстрые команды

### Native solve

```bash
cd bitgn-env

# одна задача PAC1
./run-codex-native.sh --env pac1 t01

# полный PAC1 (текущий benchmark: t01..t43)
./run-codex-native.sh --env pac1 -p 5 t{01..43}
```

### Выбор backend (Spark / OmniRoute)

```bash
# Spark/direct Codex backend (использует ChatGPT login или выбранный codex profile)
CODEX_BACKEND=spark ./run-codex-native.sh --env pac1 t01

# Spark + явный profile (если он настроен в ~/.codex/config.toml)
CODEX_BACKEND=spark CODEX_PROFILE=<your-spark-profile> ./run-codex-native.sh --env pac1 t01

# OmniRoute backend (текущий default)
CODEX_BACKEND=omniroute ./run-codex-native.sh --env pac1 t01
```

Примечания:

- `CODEX_PROFILE` опционален; если задан, прокидывается в `codex exec --profile <name>`.
- Если `CODEX_BACKEND=spark` и `CODEX_PROFILE` пустой, wrappers форсят direct provider через `-c model_provider=openai`.
- OmniRoute ключ нужен только при `CODEX_BACKEND=omniroute`.

### Smoke режим (без leaderboard)

```bash
BITGN_API_KEY='' BITGN_API_KEY_FILE='/tmp/bitgn-no-key' \
BITGN_RUN_NAME='[@skifmax]-[codex]-[chiki-banboni]-[smoke]' \
./run-codex-native.sh --env pac1 -p 5 t{01..43}
```

### Leaderboard режим

```bash
BITGN_RUN_NAME='[@skifmax]-[codex]-[chiki-banboni]-[xNNN]' \
./run-codex-native.sh --env pac1 -p 5 t{01..43}
```

См. leaderboard и сравнение run на странице PAC: https://bitgn.com/challenge/PAC.

### Analytics evolution

```bash
# анализ одной fail-задачи из local run
./run-codex-analytics.sh analyze --env pac1 --run-id <local_run_id> -p 1 --focus-task t36 t36

# применить выбранный proposal из существующей версии правил
./run-codex-analytics.sh apply --proposal-id prop-001 --from-version rv0038

# задеплоить новую версию правил в native local-rules
./run-codex-analytics.sh deploy --rules-version rv0039 --yes
```

## Артефакты и наблюдаемость

- Корень native run: `codex-agent-native/runs/<local_run_id>/`
- Per-task workspace: `codex-agent-native/runs/<local_run_id>/<task_id>/attempt_<timestamp>_<id>/`
- Run manifest: `codex-agent-native/runs/<local_run_id>/run_manifest.jsonl`
- Per-task score: `.../score.json` (pass/fail, детали score, tokens, steps)

Артефакты analytics:

- analysis summary: `codex-agent-analytics/analysis/aXXXX.json`
- report: `codex-agent-analytics/reports/rXXXX.md`
- proposals: `codex-agent-analytics/proposals/rules/<rv>/prop-XXX.md`
- apply/deploy reports: `codex-agent-analytics/applies/aXXXX.md`, `codex-agent-analytics/deploy/dXXXX.md`

## Конфигурация

- Переключатель backend: `CODEX_BACKEND=omniroute|spark` (default: `omniroute`).
- Опциональный profile override для Codex CLI: `CODEX_PROFILE=<profile-name>`.
- OmniRoute ключ для Codex flow: `OMNIROUTE_API_KEY` (только для `CODEX_BACKEND=omniroute`).
- Порядок резолва ключа в wrapper:
  1. `OMNIROUTE_API_KEY` env
  2. `BITGN_OMNIROUTE_KEY_FILE`
  3. `$HOME/.codex/omniroute-api-key`
- Override модели: `CODEX_MODEL` (default `gpt-5.3-codex`).
- Native parallelism: `-p` / `--parallelism` или `NATIVE_PARALLELISM`.

## Связанные документы

- Native details: [`codex-agent-native/README.md`](./codex-agent-native/README.md)
- Analytics details: [`codex-agent-analytics/README.md`](./codex-agent-analytics/README.md)
- Architecture deep dive: [`ARCHITECTURE.ru.md`](./ARCHITECTURE.ru.md)
- Rule design and evolution policy: [`RULES_EVOLUTION_PRINCIPLES.ru.md`](./RULES_EVOLUTION_PRINCIPLES.ru.md)
- Active local rules: [`codex-agent-native/local-rules/AGENTS.md`](./codex-agent-native/local-rules/AGENTS.md)
- BitGN runs dashboard: [`bitgn-dash`](https://github.com/ai-babai/bitgn-dash) — статический matrix dashboard для анализа pass/fail native run
- Provider reference: [`OmniRoute`](https://github.com/diegosouzapw/OmniRoute/) — часто используемый backend provider для `CODEX_BACKEND=omniroute`
- Root-level navigation/rules on this machine: [`AGENTS.md`](./AGENTS.md)
