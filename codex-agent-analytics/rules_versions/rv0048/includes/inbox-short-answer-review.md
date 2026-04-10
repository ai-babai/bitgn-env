# Inbox Short-Answer Review

Применяй этот профиль для exact-literal review/check и коротких lookup-запросов с ожидаемым единственным ответом.

Минимальный read-only путь:
- Прочитай только обязательные trusted policy/docs, требуемые для решения.
- Открой целевой inbox-элемент (или самый ранний pending для queue/review инструкций).
- Выполни один решающий artifact-check по условию задачи (например, sender/contact/account scope или cardinality exact match).
- Сразу выбери outcome и сделай один `report_completion`.

Ограничения:
- Не делай лишние exploratory шаги (`tree`/`list`/`find`/`search`), если ответ уже разрешим по обязательным источникам.
- Для read-only review/lookup задач не используй мутационные инструменты.
