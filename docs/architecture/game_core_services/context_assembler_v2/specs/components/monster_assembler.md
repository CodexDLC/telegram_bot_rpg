# Monster Assembler

## Компонент
`MonsterAssembler`

## Ответственность
Загружает данные монстров из базы данных, форматирует их с использованием `MonsterTempContextSchema` и сохраняет проекции в Redis.

## Ключевой метод
```python
async def process_batch(monster_ids: list[str], scope: str) -> dict[str, str]
```

## Логика работы
1.  Загружает монстров из одной таблицы (данные монстров хранятся в JSON-полях).
2.  Для каждого монстра:
    *   Извлекает JSON-поля: `scaled_base_stats`, `loadout_ids`, `skills_snapshot`.
    *   Создает `MonsterTempContextSchema` с данными `core_*`.
    *   Pydantic вызывает методы `@computed_field` (генерирует `math_model`, `loadout`, `vitals`).
    *   Выполняет `model_dump(by_alias=True, exclude={"core_*"})`.
    *   Сохраняет **ТОЛЬКО** проекции в Redis с TTL.
3.  Возвращает маппинг `{monster_id: redis_key}`.

## Ключевые отличия от PlayerAssembler
*   **Запрос к одной таблице** (а не к нескольким, как у игроков).
*   **Данные уже в JSON-полях** (`scaled_base_stats`, `loadout_ids`).
*   **Всегда форматирует в боевую структуру** (монстры используются только в бою, других scope нет).
*   **MonsterTempContextSchema специализирован** (не является частью иерархии Base).

## Примечание к дизайну
MonsterAssembler = Assembler + Formatter в одном флаконе. Отдельные форматтеры не нужны, так как у монстров только один сценарий использования (бой).
