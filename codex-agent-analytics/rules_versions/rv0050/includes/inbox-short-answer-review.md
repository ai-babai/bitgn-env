# Inbox Short-Answer Review

Применяй этот профиль только для exact-literal review/check и коротких lookup-запросов с ожидаемым единственным ответом, когда не требуются обязательные writes.

Минимальный read-only путь:
- Прочитай только обязательные trusted policy/docs, требуемые для решения.
- Открой целевой inbox-элемент (или самый ранний pending для queue/review инструкций).
- Выполни один решающий artifact-check по условию задачи (например, sender/contact/account scope или cardinality exact match).
- Сразу выбери outcome и сделай один `report_completion`.

Actionability gate (обязательный):
- До финализации классифицируй запрос: informational/check-only или actionable workflow.
- Если trusted policy/docs для текущего inbox-item требуют mutation artifacts (например `outbox/<id>.json` и `outbox/seq.json`), read-only shortcut прекращается.
- В таком случае перейди к полному workflow и разрешай `OUTCOME_OK` только после создания required artifacts.
- Формулировки queue/review сами по себе не разрешают read-only completion при наличии trusted must-write требований.

Ограничения:
- Не делай лишние exploratory шаги (`tree`/`list`/`find`/`search`), если ответ уже разрешим по обязательным источникам.
- Для read-only review/lookup задач не используй мутационные инструменты.
