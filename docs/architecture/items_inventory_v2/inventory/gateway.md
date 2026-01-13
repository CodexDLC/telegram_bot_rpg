# Inventory Gateway API

## 📋 Обзор

Описание публичного API модуля Inventory через `InventoryGateway` — единую точку входа для взаимодействия с инвентарём персонажа.

---

## 🏗️ InventoryGateway

**Назначение:** Единая точка входа для модуля Inventory. Обслуживает как внутренние вызовы (CoreRouter), так и внешние HTTP запросы (FastAPI).

**Расположение:** `apps/game_core/modules/inventory/inventory_gateway.py`

**Ответственность:**
- **Для CoreRouter:** реализация `get_entry_point(action, context)` — используется другими модулями (Combat, Items, etc.)
- **Для FastAPI Router:** публичные методы (`view_inventory`, `equip_item`, etc.) — вызываются напрямую из HTTP endpoints
- Валидация входных данных и обработка исключений
- Делегирование бизнес-логики в `InventoryService`

**Важно:** Inventory не нуждается в отдельном Orchestrator (в отличие от Combat), т.к. не создаёт сложные сессии — только управляет данными.

---

## 🎯 Два способа вызова

### 1. Через CoreRouter (рекомендуется)

```python
# Из другого модуля
result = await router.route(
    module="inventory",
    action="view",
    context={"char_id": 123}
)
```

**Gateway обрабатывает через:**
```python
async def get_entry_point(self, action: str, context: dict[str, Any]) -> Any:
    char_id = context.get("char_id")
    if not char_id:
        raise ValueError("char_id required")

    if action == "view":
        return await self.view_inventory(char_id)
    elif action == "equip":
        return await self.equip_item(char_id, context["item_id"], context.get("slot"))
    # ...
```

### 2. Прямой вызов (из bot handlers)

```python
# Прямой доступ к gateway
inventory_gateway = container.inventory.gateway()

result = await inventory_gateway.view_inventory(char_id=123)
```

---

## 📚 API Reference

### 1. view_inventory

**Назначение:** Получить полный инвентарь персонажа для отображения в UI.

**Сигнатура:**
```python
async def view_inventory(self, char_id: int) -> InventoryViewDTO
```

**Параметры:**
- `char_id` (int) — ID персонажа

**Возвращает:**
```python
InventoryViewDTO(
    equipped={
        "main_hand": WeaponDTO(...),
        "off_hand": ShieldDTO(...),
        "head": ArmorDTO(...),
        # ...
    },
    backpack=[
        InventoryItemDTO(id=1, name="Iron Sword", quantity=1, ...),
        InventoryItemDTO(id=2, name="Health Potion", quantity=5, ...),
    ],
    quick_slots=[
        ConsumableDTO(...),  # Слот 1
        None,                # Слот 2 пуст
        ConsumableDTO(...),  # Слот 3
    ],
    stats={
        "total_weight": 45.5,
        "max_weight": 100.0,
        "slots_used": 12,
        "max_slots": 50
    }
)
```

**Пример использования:**
```python
inventory = await gateway.view_inventory(char_id=123)

for item in inventory.backpack:
    print(f"{item.name} x{item.quantity}")
```

**Ошибки:**
- `ValueError` — если `char_id` не передан
- `CharacterNotFoundError` — если персонаж не существует

---

### 2. equip_item

**Назначение:** Экипировать предмет из рюкзака.

**Сигнатура:**
```python
async def equip_item(
    self,
    char_id: int,
    item_id: int,
    slot: str | None = None
) -> EquipResultDTO
```

**Параметры:**
- `char_id` (int) — ID персонажа
- `item_id` (int) — ID предмета в рюкзаке
- `slot` (str | None) — Целевой слот (опционально, авто-определяется)

**Возвращает:**
```python
EquipResultDTO(
    success=True,
    unequipped_item=WeaponDTO(...) | None,  # Если был предмет в слоте
    message="Iron Sword equipped to Main Hand"
)
```

**Логика:**
1. Проверка: предмет существует в рюкзаке
2. Определение слота (если не указан явно)
3. Снятие текущего предмета из слота (если есть)
4. Перемещение старого предмета в рюкзак
5. Экипировка нового предмета
6. Установка `dirty=True`

**Пример:**
```python
result = await gateway.equip_item(char_id=123, item_id=456, slot="main_hand")

if result.success:
    print(result.message)
    if result.unequipped_item:
        print(f"Unequipped: {result.unequipped_item.name}")
```

**Ошибки:**
- `ItemNotFoundError` — предмет не найден в рюкзаке
- `InvalidSlotError` — слот не подходит для этого типа предмета
- `RequirementsNotMetError` — персонаж не соответствует требованиям предмета

---

### 3. unequip_item

**Назначение:** Снять предмет и поместить в рюкзак.

**Сигнатура:**
```python
async def unequip_item(self, char_id: int, slot: str) -> UnequipResultDTO
```

**Параметры:**
- `char_id` (int) — ID персонажа
- `slot` (str) — Слот для снятия (например, "main_hand")

**Возвращает:**
```python
UnequipResultDTO(
    success=True,
    item=WeaponDTO(...),
    message="Iron Sword unequipped from Main Hand"
)
```

**Логика:**
1. Проверка: слот не пустой
2. Проверка: есть место в рюкзаке
3. Перемещение предмета в рюкзак
4. Освобождение слота
5. Установка `dirty=True`

**Ошибки:**
- `SlotEmptyError` — в слоте нет предмета
- `InventoryFullError` — рюкзак переполнен

---

### 4. use_consumable

**Назначение:** Использовать расходник (зелье, свиток).

**Сигнатура:**
```python
async def use_consumable(
    self,
    char_id: int,
    item_id: int,
    source: Literal["backpack", "quick_slot"] = "backpack",
    slot_index: int | None = None
) -> UseConsumableResultDTO
```

**Параметры:**
- `char_id` (int) — ID персонажа
- `item_id` (int) — ID расходника
- `source` (str) — Источник ("backpack" или "quick_slot")
- `slot_index` (int | None) — Индекс quick slot (если source="quick_slot")

**Возвращает:**
```python
UseConsumableResultDTO(
    success=True,
    effects=[
        EffectDTO(type="heal", value=50, target="hp"),
        EffectDTO(type="buff", value=10, target="strength", duration=300)
    ],
    remaining_quantity=4,  # Осталось в стаке
    message="Health Potion used. Restored 50 HP."
)
```

**Логика:**
1. Найти предмет в указанном источнике
2. Проверка: предмет является расходником
3. Применить эффекты через `EffectService`
4. Уменьшить количество (или удалить, если quantity=0)
5. Установка `dirty=True`

**Пример:**
```python
result = await gateway.use_consumable(char_id=123, item_id=789)

print(result.message)
for effect in result.effects:
    print(f"  {effect.type}: +{effect.value} to {effect.target}")
```

**Ошибки:**
- `ItemNotFoundError` — предмет не найден
- `NotConsumableError` — предмет не является расходником
- `CannotUseInCombatError` — нельзя использовать в бою (если флаг установлен)

---

### 5. move_to_quick_slot

**Назначение:** Переместить расходник в быстрый слот.

**Сигнатура:**
```python
async def move_to_quick_slot(
    self,
    char_id: int,
    item_id: int,
    slot_index: int
) -> QuickSlotResultDTO
```

**Параметры:**
- `char_id` (int) — ID персонажа
- `item_id` (int) — ID расходника из рюкзака
- `slot_index` (int) — Индекс слота (0-9, например)

**Возвращает:**
```python
QuickSlotResultDTO(
    success=True,
    replaced_item=ConsumableDTO(...) | None,  # Если слот был занят
    message="Health Potion placed in Quick Slot 1"
)
```

**Логика:**
1. Проверка: предмет является расходником
2. Проверка: индекс слота валиден
3. Если слот занят → переместить старый предмет обратно в рюкзак
4. Поместить новый предмет в слот
5. Установка `dirty=True`

**Ошибки:**
- `NotConsumableError` — предмет не является расходником
- `InvalidSlotIndexError` — индекс слота вне диапазона

---

### 6. drop_item

**Назначение:** Выбросить предмет из инвентаря (удалить навсегда).

**Сигнатура:**
```python
async def drop_item(self, char_id: int, item_id: int) -> DropResultDTO
```

**Параметры:**
- `char_id` (int) — ID персонажа
- `item_id` (int) — ID предмета

**Возвращает:**
```python
DropResultDTO(
    success=True,
    item_name="Rusty Dagger",
    message="Rusty Dagger dropped"
)
```

**Логика:**
1. Найти предмет в рюкзаке
2. Удалить из рюкзака
3. Установка `dirty=True`

**Примечание:** Если предмет экипирован, сначала нужно вызвать `unequip_item()`.

**Ошибки:**
- `ItemNotFoundError` — предмет не найден
- `CannotDropEquippedError` — нельзя выбросить экипированный предмет

---

### 7. get_item_details

**Назначение:** Получить детальную информацию о предмете (для tooltip).

**Сигнатура:**
```python
async def get_item_details(self, char_id: int, item_id: int) -> ItemDetailsDTO
```

**Параметры:**
- `char_id` (int) — ID персонажа
- `item_id` (int) — ID предмета

**Возвращает:**
```python
ItemDetailsDTO(
    id=456,
    name="Flaming Longsword of the Bear",
    type="weapon",
    subtype="sword",
    rarity="rare",
    description="A masterwork longsword imbued with fire magic...",
    stats={
        "damage": "15-20",
        "accuracy": 85,
        "crit_chance": 10
    },
    bonuses=[
        "+5 Fire Damage",
        "+10 Strength"
    ],
    requirements={
        "strength": 12,
        "level": 5
    },
    durability={
        "current": 80,
        "max": 100
    },
    value=350,  # Цена продажи
    weight=4.5
)
```

**Пример:**
```python
details = await gateway.get_item_details(char_id=123, item_id=456)

print(f"{details.name} ({details.rarity})")
print(f"Damage: {details.stats['damage']}")
for bonus in details.bonuses:
    print(f"  + {bonus}")
```

---

### 8. sync_inventory

**Назначение:** Принудительная синхронизация инвентаря с БД.

**Сигнатура:**
```python
async def sync_inventory(self, char_id: int) -> SyncResultDTO
```

**Параметры:**
- `char_id` (int) — ID персонажа

**Возвращает:**
```python
SyncResultDTO(
    success=True,
    changes_saved=True,  # Были ли изменения
    message="Inventory synchronized"
)
```

**Когда использовать:**
- Перед началом боя (чтобы не потерять изменения)
- Перед выходом из игры
- По таймеру для долгих сессий

**Логика:**
1. Вызов `SessionManager.sync_to_db(char_id)`
2. Проверка `dirty` флага
3. Сохранение в БД (если dirty=True)
4. Сброс флага

---

## 🔄 Взаимодействие с другими модулями

### Из боевой системы

```python
# Перед началом боя — синхронизируем инвентарь
await router.route("inventory", "sync", {"char_id": char_id})

# Получаем экипированное оружие для расчёта урона
inventory = await router.route("inventory", "view", {"char_id": char_id})
weapon = inventory.equipped.get("main_hand")
```

### Из системы крафта

```python
# После создания предмета — добавляем в инвентарь
await router.route("inventory", "add_item", {
    "char_id": char_id,
    "item_id": new_item_id
})
```

### Из торговли

```python
# Проверка наличия предмета
inventory = await router.route("inventory", "view", {"char_id": char_id})
item_exists = any(item.id == item_id for item in inventory.backpack)
```

---

## 🛡️ Обработка ошибок

Gateway перехватывает и обрабатывает исключения, возвращая унифицированные ошибки:

```python
try:
    result = await gateway.equip_item(char_id, item_id, slot)
except ItemNotFoundError as e:
    # Обработка: показать сообщение игроку
    return {"error": str(e)}
except InvalidSlotError as e:
    # Обработка: подсветить правильный слот
    return {"error": str(e), "valid_slots": e.valid_slots}
```

---

## 🎯 Ключевые принципы Gateway

1. **Unified Entry Point**
   - Gateway обслуживает ДВА типа вызовов:
     - CoreRouter (внутренние, от других модулей)
     - FastAPI Router (HTTP endpoints)
   - Это **единственный класс**, не нужен отдельный Orchestrator

2. **Thin Gateway**
   - Не содержит бизнес-логики
   - Только маршрутизация и валидация
   - Вся логика делегируется в `InventoryService`

3. **Validation First**
   - Проверка обязательных параметров
   - Валидация типов данных
   - Ранний возврат ошибок (до вызова Service)

4. **Error Handling**
   - Перехват исключений из Service
   - Преобразование в унифицированные DTO-ошибки
   - Логирование для отладки

---

## 📚 Связанная документация

- **Inventory Architecture:** [./inventory_architecture.md](./inventory_architecture.md)
- **Session Management:** [./session_management.md](./session_management.md)
- **Formatting and UI:** [./formatting_and_ui.md](./formatting_and_ui.md)

---

**Последнее обновление:** Январь 2026
**Статус:** Архитектурная фаза
