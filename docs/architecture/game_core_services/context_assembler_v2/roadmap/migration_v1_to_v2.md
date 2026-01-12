# Migration from v1 to v2

## Что меняется

### 1. Файлы схем (Schema Files)
**Удалить:**
- `schemas/temp_context.py` (старая монолитная `TempContextSchema`)

**Добавить:**
- `schemas/base.py` (`BaseTempContext`)
- `schemas/combat.py` (`CombatTempContext`)
- `schemas/inventory.py` (`InventoryTempContext`)
- `schemas/status.py` (`StatusTempContext`)
- `schemas/monster.py` (`MonsterTempContextSchema` - обновленная)

### 2. Сервисный слой (Service Layer)
**Обновить:**
- `service.py` → `orchestrator.py` (переименовать + добавить параметр `scope`)
- Добавить `player_assembler.py`
- Добавить `monster_assembler.py`
- Добавить `query_plan_builder.py` (или словарь `QUERY_PLANS`)

### 3. Интеграция с боевой системой (Combat System Integration)
**Было (v1):**
```python
response = await context_assembler.assemble(player_ids, monster_ids)
```

**Стало (v2):**
```python
response = await context_assembler.assemble(
    ContextRequestDTO(player_ids=player_ids, monster_ids=monster_ids, scope="combats")
)
```

### 4. Структура Redis
**Без изменений** - по-прежнему `temp:setup:{uuid}` с TTL 1 час.

**Изменения контента** - v2 содержит **ТОЛЬКО** отформатированные проекции (без полей `core_*`).

### 5. Стратегия тестирования
1.  Реализовать компоненты v2.
2.  Проверить выходные данные в Redis (структуру и значения) на тестовых данных.
3.  Проверить, что боевая система корректно инициализируется с новыми данными.
4.  Мониторить производительность (v2 должна быть на ~50% быстрее).
5.  Полный переход на v2.

## Критические изменения (Breaking Changes)
- `ContextRequestDTO` теперь требует параметр `scope`.
- Структура временного контекста различается в зависимости от `scope` (больше не универсальная).
- Поля `core_*` больше недоступны в Redis.

## План отката (Rollback Plan)
Сохранять код v1 в отдельной ветке (или backup) до полной валидации v2.
