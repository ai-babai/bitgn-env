# Принципы эволюции правил и prompt

Этот документ описывает, как мы эволюционируем поведение native solver в управляемом режиме.

## 1) Что может эволюционировать

Эволюция не ограничивается одним файлом.

Версия правил (`rvXXXX`) может включать:

- `rules_versions/rvXXXX/AGENTS.md` (core policy)
- `rules_versions/rvXXXX/includes/*.md` (модульные policy-расширения)

`deploy` делает полную замену native `local-rules/`, поэтому поведение может меняться и из core-файла, и из includes.

В редких блокирующих случаях эволюция может переходить к code-changes, но путь по умолчанию — rules/prompt behavior.

## 2) Единица эволюции

Одна итерация должна таргетировать один primary failure mode.

Обязательные поля unit:

- primary task,
- problem statement на базе evidence,
- одна гипотеза,
- affected-task validation scope,
- rollback note.

Так сохраняется причинность: можно объяснить, какое изменение исправило какой фейл.

## 3) Модель prompt-эволюции

Мы эволюционируем поведение в двух prompt-слоях:

1. Runtime solver policy (native):

- локальные правила, инжектируемые в Codex session (`AGENTS.md` + optional includes),
- task instruction + tool contract.

2. Analyzer policy (analytics):

- analyze/apply/deploy prompt contracts в `codex-agent-analytics/docs/instructions/`.

Reference note:

- engineering article/map harness доступен как optional reference (`codex-agent-analytics/docs/references/harness-engineering-structure-draft.md`).
- это не mandatory policy input для каждого analyze run, но analyzer может его использовать для более системных рекомендаций.

Практическое правило:

- если solver сделал неверное решение при корректном tool path, сначала эволюционируем runtime rules;
- если страдает качество proposal/process (слабая диагностика, oversized diff, плохая генерализация), эволюционируем analyzer prompts/contracts.

## 4) Базовые принципы

1. Harness-first

- Предпочитать policy/rules изменения code-изменениям.
- К коду переходить только если доказано, что rules недостаточно.

2. Минимальность и обратимость

- Держать diff небольшим.
- У каждого proposal должен быть понятный rollback path.

3. Генерализация, а не memorization

- Никаких task-specific ответов, ID или one-off hack в policy-тексте.
- Кодировать переиспользуемые decision-gates (ambiguity, safety, scope, write-discipline).

4. Приоритет safety и authorization

- Security и scope checks важнее convenience completion.
- При неопределенности в sensitive-action сценариях предпочитать clarify/deny outcome вместо небезопасного `OUTCOME_OK`.

5. Детерминированная completion-дисциплина

- Валидное завершение задачи только через `report_completion`.
- Rules должны улучшать решения до completion, а не обходить completion contract.

## 5) Как выбираем точку изменения

Порядок принятия решения:

1. `AGENTS.md`, если это глобальная policy-коррекция.
2. `includes/*.md`, если фикc узкий/модульный и его нужно изолировать.
3. Analyzer instruction docs, если проблема в diagnose/proposal/apply поведении.
4. Code только для доказанных блокирующих ограничений.

## 6) Validation ladder

После deploy валидируем строго в таком порядке:

1. targeted rerun (primary task),
2. risk cluster rerun (вероятно затронутые задачи),
3. full smoke run,
4. leaderboard run только после локального green.

Если есть regression — запускаем новую focused-итерацию от этой regression.

## 7) Жесткие guardrails (текущие)

Ограничения runtime/local-rules (проверяются native runner):

- Лимит строк для `local-rules/AGENTS.md` конфигурируется через `LOCAL_RULES_MAX_AGENTS_LINES` (по умолчанию `156`; исторический baseline — `100`).
- include-файлы должны находиться в `includes/*.md`.
- максимум include-файлов: 8.
- максимум строк на include-файл: 80.
- максимум суммарных include-строк: 220.

Операционные режимы native runner:

- Поддерживается произвольный порядок задач: исполнение идет ровно в порядке task-id из CLI.
- Поддерживается `--fail-fast`: после первого фейла планирование новых задач останавливается (при `parallelism > 1` inflight задачи дорабатываются).

Ограничения analytics apply (проверяются в `apply` flow):

- лимит changed-lines на один apply:
  - <= 80, когда include-файл не создан,
  - <= 100, когда include-файл(ы) создан(ы).
- количество generated include-файлов в одном apply ограничено (сейчас `includes_count <= 1`).

Эти лимиты намеренные: они делают каждый шаг эволюции компактным, reviewable и безопасным для rollback.

## 8) Критерии приемки

Изменение считается принятым, когда:

- primary failure исправлен,
- risk cluster не деградировал,
- full smoke зеленый,
- артефакты полные (`proposal -> apply -> deploy -> validation evidence`).

## 9) Исходные артефакты для решений

- `run_manifest.jsonl`
- per-task `score.json`
- `tool_calls.jsonl`, `events.jsonl`
- analytics outputs в `analysis/`, `reports/`, `proposals/`, `applies/`, `deploy/`

## 10) Важное caveat по non-regression

Provider/model entitlement failures не являются prompt/rules regression.

Если модель не стартует (model gate), качество сравниваем только между run, где есть реальные task scores.
