# 📦 InventoryManager

⬅️ [Назад к Managers](../managers.md)

---

## 📋 Overview

**File:** `backend/database/redis/manager/inventory_manager.py`

**Role:** Управление сессией инвентаря персонажа.

**Key Features:**
- RedisJSON для хранения `ac:{char_id}:inventory`
- Точечные обновления (добавление/удаление предмета)
- Фильтрация на стороне Redis (JSONPath) для выборки предметов
- Sliding TTL (3600s) - сессия живет 1 час без активности

---

## 🔑 Redis Keys

### Primary Key

#### `ac:{char_id}:inventory`
**Type:** RedisJSON
**TTL:** 3600 seconds (1 hour) - Sliding Expiration
**Structure:**
```json
{
  "char_id": 123,
  "equipped": { ... },
  "bag": { ... },
  "wallet": {
    "currency": { "dust": 150 },
    "resources": { "wood": 50 },
    "components": { "gear": 2 }
  },
  "stats": { ... },
  "is_dirty": false,
  "updated_at": 1715000000.0
}
```

---

## 🛠️ Methods

### Core Session Operations

#### `save_session(char_id: int, session_data: dict[str, Any]) -> None`
Сохраняет полную сессию инвентаря.

**Redis Command:** `JSON.SET ac:{char_id}:inventory $ {data}` + `EXPIRE 3600`

**Used by:**
- `InventorySessionService.load_session()` (после загрузки из БД)

---

#### `get_session(char_id: int) -> dict[str, Any] | None`
Получает полную сессию. Продлевает TTL.

**Redis Command:** `JSON.GET ac:{char_id}:inventory $` + `EXPIRE 3600`

**Returns:** Полный JSON или `None`

---

#### `exists(char_id: int) -> bool`
Проверяет наличие активной сессии.

---

### View Operations (Optimized)

#### `get_equipped(char_id: int) -> dict[str, Any] | None`
Получает только надетые предметы (для отрисовки Куклы).

**Redis Command:** `JSON.GET ac:{char_id}:inventory $.equipped`

**Returns:** Словарь `{"head_armor": {...}, ...}`

---

#### `get_bag_filtered(char_id: int, item_type: str | None = None, subtype: str | None = None) -> list[dict]`
Получает предметы из сумки с фильтрацией на стороне Redis.

**Redis Command:**
- No filters: `JSON.GET ac:{char_id}:inventory $.bag`
- Type filter: `JSON.GET ac:{char_id}:inventory $.bag.*[?(@.item_type=='{type}')]`

**Returns:** Список предметов.

---

#### `get_wallet(char_id: int) -> dict[str, Any] | None`
Получает кошелек (валюта, ресурсы, компоненты).

**Redis Command:** `JSON.GET ac:{char_id}:inventory $.wallet`

---

### Item Operations (Atomic)

#### `get_item(char_id: int, item_id: int) -> dict | None`
Ищет предмет по ID (сначала в сумке, потом в экипировке).
*Примечание: JSONPath позволяет искать везде, но это может быть медленно. Лучше знать контекст.*

**Redis Command:** `JSON.GET ac:{char_id}:inventory $.bag.{item_id}`

---

#### `add_item_to_bag(char_id: int, item_data: dict) -> None`
Добавляет предмет в сумку.

**Redis Command:** `JSON.SET ac:{char_id}:inventory $.bag.{item_id} {item_data}`

---

#### `remove_item(char_id: int, item_id: int, location: str) -> None`
Удаляет предмет.

**Redis Command:**
- Bag: `JSON.DEL ac:{char_id}:inventory $.bag.{item_id}`
- Equipped: `JSON.DEL ac:{char_id}:inventory $.equipped.{slot}`

---

#### `move_item_json(char_id: int, item_id: int, from_path: str, to_path: str) -> None`
Перемещает JSON-объект предмета (например, из сумки в слот).
Требует Lua скрипта или транзакции (Get + Del + Set), так как нативного `JSON.MOVE` нет.

---

## 🔄 Integration Points

### Inventory Domain
- **InventorySessionService** - основной клиент. Использует менеджер для всех операций с данными.

### Other Domains
- **Shop Domain** - может добавлять предметы через `add_item_to_bag` (если сессия активна).
- **Loot Domain** - может добавлять лут.

---

## 📊 Performance Considerations

### RedisJSON Benefits
- **Фильтрация:** `get_bag_filtered` возвращает только нужные данные, экономя трафик.
- **Частичное чтение:** `get_equipped` читает < 1KB данных, даже если сумка весит 100KB.

### TTL Strategy
- **Sliding Expiration:** Каждое чтение/запись продлевает жизнь сессии на 1 час.
- Если игрок AFK, сессия удаляется, освобождая память. При возвращении - Lazy Load из БД.

---

## 🚨 Error Handling

### Missing Session
- Все методы возвращают `None` или вызывают исключение, если ключа нет.
- `InventorySessionService` должен перехватить это и вызвать `load_session` (через Assembler).

### JSONPath Errors
- Если фильтр некорректен, Redis вернет ошибку. Менеджер должен логировать это.

---

## 📝 Usage Examples

### Open Inventory (Main Menu)
```python
# 1. Check & Load
if not await manager.exists(char_id):
    # Load from DB...
    await manager.save_session(char_id, full_data)

# 2. Get Equipped & Wallet
equipped = await manager.get_equipped(char_id)
wallet = await manager.get_wallet(char_id)
```

### Filter Items (Bag View)
```python
# Получить только оружие
weapons = await manager.get_bag_filtered(char_id, item_type="weapon")
```

### Equip Item
```python
# 1. Get Item from Bag
item = await manager.get_item(char_id, 101)

# 2. Remove from Bag
await manager.remove_item(char_id, 101, "bag")

# 3. Add to Equipped
await manager.add_item_to_equipped(char_id, "main_hand", item)
```
