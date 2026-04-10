# Mandatory Literal Conflict Gate

Применяй этот include для любого write-capable workflow (включая `PROCESS INBOX`, queue/review и другие actionable сценарии), где trusted policy/instruction задают required artifacts.

Prewrite gate (обязательный до первого `write`):
- Собери mandatory требования из trusted источников в пары `target_path + exact_required_literal`.
- Сгруппируй пары по `target_path` и проверь distinct literal значения.
- Если для одного `target_path` найдено более одного literal и нет explicit precedence source, немедленно останови workflow до любых мутаций.
- Выбери `OUTCOME_NONE_CLARIFICATION`, задай минимальный вопрос о precedence и включи все конфликтующие mandatory-источники в `grounding_refs`.
- `OUTCOME_OK` и любые мутации запрещены до явного precedence из trusted policy/instruction.

Final required-artifact re-check (обязательный перед `report_completion`):
- Если итог зависит от required artifacts, повторно выполни conflict-проверку по тем же trusted источникам.
- При неразрешенном literal-конфликте `OUTCOME_OK` запрещен; выбирай `OUTCOME_NONE_CLARIFICATION` с минимальным вопросом о precedence и конфликтующими источниками в `grounding_refs`.
