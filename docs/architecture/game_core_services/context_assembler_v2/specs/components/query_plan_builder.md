# Query Plan Builder

## Компонент
`QueryPlanBuilder` (или простой словарь `QUERY_PLANS`)

## Ответственность
Сопоставляет `scope` со списком таблиц/источников данных, которые необходимо загрузить.

## Структура
```python
QUERY_PLANS = {
    "combats": ["attributes", "inventory", "skills", "vitals", "symbiote"],
    "inventory": ["inventory", "wallet"],
    "status": ["attributes", "vitals", "symbiote"],
    "exploration": ["attributes", "skills", "vitals"],  # будущее
    "trade": ["attributes", "inventory", "wallet"],      # будущее
}
```

## Использование
```python
query_plan = QUERY_PLANS[scope]
# Возвращает: ["attributes", "inventory", "skills", ...]

# PlayerAssembler использует это для определения, какие запросы к БД выполнять
if "attributes" in query_plan:
    data["core_stats"] = await db.get_attributes(player_ids)
if "inventory" in query_plan:
    data["core_inventory"] = await db.get_inventory(player_ids)
```

## Примечание к дизайну
Может быть простой константой-словарем или классом с логикой валидации. Начинаем со словаря, рефакторим в класс, если потребуется более сложная логика.

## Добавление нового Scope
1.  Добавить запись в словарь `QUERY_PLANS`.
2.  Создать соответствующую схему `TempContext`.
3.  Добавить маппинг `scope` → `TempContext class` в `PlayerAssembler`.
