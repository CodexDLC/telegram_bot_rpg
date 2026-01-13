# Inventory Module: Architecture

## 📋 Обзор

Детальное описание архитектуры модуля Inventory, компонентов и их взаимодействия.

---

## 🏗️ Компоненты системы

### 1. InventoryGateway

**Назначение:** Единая точка входа для модуля. Реализует протокол `CoreOrchestratorProtocol`.

**Расположение:** `apps/game_core/modules/inventory/inventory_gateway.py`

**Ответственность:**
- Реализация `get_entry_point(action, context)` для CoreRouter
- Публичные методы для прямого вызова (`view_inventory`, `equip_item`)
- Делегирование бизнес-логики в `InventoryService`
- Обработка исключений

**Пример:**
```python
class InventoryGateway:
    def __init__(self, service: InventoryService):
        self.service = service
    
    async def get_entry_point(self, action: str, context: dict[str, Any]) -> Any:
        """Вход для CoreRouter"""
        char_id = context.get("char_id")
        if not char_id:
            raise ValueError("char_id required")
            
        if action == "view":
            return await self.view_inventory(char_id)
        elif action == "equip":
            return await self.equip_item(char_id, context["item_id"], context.get("slot"))
        # ...
        
    async def view_inventory(self, char_id: int) -> dict:
        """Прямой вызов"""
        return await self.service.get_inventory_view(char_id)
        
    async def equip_item(self, char_id: int, item_id: int, slot: str | None = None) -> dict:
        return await self.service.equip_item(char_id, item_id, slot)
```

---

### 2. InventoryService (Logic)

**Назначение:** Основная бизнес-логика управления инвентарём.

**Расположение:** `apps/game_core/modules/inventory/inventory/logic/inventory_service.py`

**Ответственность:**
- Управление потоком данных (Session -> Logic -> Save)
- Запрос snapshots через router (если сессии нет)
- Валидация операций
- Вызов Formatter для UI

**Методы:**
```python
class InventoryService:
    def __init__(self, session_manager, formatter, router):
        self.session_manager = session_manager
        self.formatter = formatter
        self.router = router
    
    async def get_inventory_view(self, char_id: int) -> dict:
        # 1. Получить сессию (или загрузить из temp)
        session = await self._ensure_session(char_id)
        
        # 2. Форматировать
        return self.formatter.format_for_ui(session)
    
    async def equip_item(self, char_id: int, item_id: int, slot: str | None) -> dict:
        # 1. Получить сессию
        session = await self.session_manager.get_session(char_id)
        
        # 2. Логика перестановки (внутри метода или отдельного класса Logic)
        self._perform_equip(session, item_id, slot)
        
        # 3. Сохранить и пометить dirty
        await self.session_manager.save_session(char_id, session, dirty=True)
        
        return {"success": True}

    async def _ensure_session(self, char_id: int) -> dict:
        """Загружает сессию из Redis или запрашивает snapshot у ContextAssembler"""
        session = await self.session_manager.get_session(char_id)
        if session:
            return session
            
        # Запрос snapshot
        snapshot = await self.router.route("context_assembler", "assemble", ...)
        return await self.session_manager.create_session_from_snapshot(char_id, snapshot)
```

---

### 3. InventorySessionManager

**Назначение:** Работа с Redis.

**Расположение:** `apps/game_core/modules/inventory/inventory/logic/inventory_session_manager.py`

**Ответственность:**
- CRUD операций с Redis
- Управление TTL
- Dirty Flags
- Синхронизация с БД (через Repository)

---

### 4. InventoryFormatter

**Назначение:** Подготовка данных для клиента.

**Расположение:** `apps/game_core/modules/inventory/inventory/logic/inventory_formatter.py`

**Ответственность:**
- Группировка, сортировка, фильтрация.
- Генерация tooltip'ов.

---

## 🔄 Флоу работы

1.  **Gateway** получает запрос.
2.  **Gateway** вызывает **Service**.
3.  **Service** получает данные через **SessionManager**.
4.  **Service** выполняет логику (Equip/Use).
5.  **Service** сохраняет изменения через **SessionManager** (Dirty=True).
6.  **Service** возвращает результат (через **Formatter**, если нужно).

## 🎯 Ключевые принципы

- **Gateway as Orchestrator:** Гейтвей сам является точкой входа для роутера.
- **Thin Gateway:** Гейтвей не содержит логики, только делегирует.
- **Rich Service:** Сервис управляет процессом.
- **Redis-First:** Все состояние в Redis.
