# ⚙️ Inventory Service Layer

[⬅️ Назад: Inventory Domain](../README.md)

---

## 🎯 Описание
Слой бизнес-логики и управления данными.

---

## 🧩 Компоненты

### 1. InventoryService
**File:** `inventory/services/inventory_service.py`

**Ответственность:**
*   Реализация правил игры.
*   Формирование View DTO.
*   Делегирование эффектов через `DispatcherBridge`.

**Зависимости:**
*   `InventorySessionService`
*   `InventoryResources`
*   `InventoryDispatcherBridge`

---

### 2. InventorySessionService
**File:** `inventory/services/inventory_session_service.py`

**Ответственность:**
*   **Lazy Loading:** Загрузка данных только по требованию.
*   **Redis Management:** Чтение/Запись сессии.
*   **DB Fallback:** Использование `ContextAssembler` для восстановления сессии из БД.

**Логика `load_session(char_id)`:**
```python
async def load_session(self, char_id: int) -> InventorySessionDTO:
    # 1. Try Redis
    session = await self.redis_manager.get_session(char_id)
    if session:
        return session

    # 2. Fallback to DB (ContextAssembler)
    assembler = ContextAssembler() # Stateless
    data = await assembler.build_inventory_context(char_id)
    
    # 3. Create & Cache Session
    session = InventorySessionDTO.from_context(data)
    await self.redis_manager.save_session(char_id, session)
    
    return session
```

---

### 3. ContextAssembler (External Utility)
**File:** `backend/domains/internal_systems/context_assembler/`
*   Используется внутри `InventorySessionService` для "холодного старта".
