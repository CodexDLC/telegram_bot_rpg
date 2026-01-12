# Integration Examples

## Combat System Integration

### Request
```python
response = await context_assembler.assemble(
    ContextRequestDTO(player_ids=[101], monster_ids=["uuid-1"], scope="combats")
)
```

### Usage
```python
# Чтение отформатированных проекций
temp_data = await redis.json().get(response.player[101])

# Использование готовых структур
math_model = temp_data["math_model"]      # структура v:raw
loadout = temp_data["loadout"]            # пояс, абилки, экипировка
vitals = temp_data["vitals"]              # hp_current, energy_current

# Копирование в боевую структуру
await redis.json().set(f"combat:rbc:{sid}:actor:{id}:raw", "$", math_model)
await redis.json().set(f"combat:rbc:{sid}:actor:{id}:loadout", "$", loadout)
```

---

## Inventory Service Integration

### Request
```python
response = await context_assembler.assemble(
    ContextRequestDTO(player_ids=[101], scope="inventory")
)
```

### Usage
```python
temp_data = await redis.json().get(response.player[101])

# Использование отформатированного инвентаря
equipped = temp_data["inventory_structured"]["equipped"]
consumables = temp_data["inventory_structured"]["consumables"]
materials = temp_data["inventory_structured"]["materials"]

# Использование отформатированного кошелька
gold = temp_data["wallet_structured"]["currency"]["gold"]
crystals = temp_data["wallet_structured"]["currency"]["crystals"]

# Рендеринг UI
await render_inventory_screen(user_id, equipped, consumables)
```

---

## Status Service Integration

### Request
```python
response = await context_assembler.assemble(
    ContextRequestDTO(player_ids=[101], scope="status")
)
```

### Usage
```python
temp_data = await redis.json().get(response.player[101])

# Использование отформатированных статов для UI
stats = temp_data["stats_display"]
# {"strength": {"value": 15, "label": "Сила"}, ...}

# Использование отформатированных ресурсов для UI
vitals = temp_data["vitals_display"]
# {"hp": {"current": 100, "max": 150, "percent": 66.7}, ...}

# Рендеринг экрана персонажа
await render_status_screen(user_id, stats, vitals)
```

---

## Key Points
*   Каждый `scope` возвращает разные проекции, подходящие для конкретного сценария использования.
*   Потребители получают готовые к использованию структуры, дополнительное форматирование не требуется.
*   Временные ключи имеют TTL 1 час, что достаточно для любой операции.
