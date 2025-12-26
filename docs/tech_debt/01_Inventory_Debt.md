# Технический долг: Система Инвентаря

## Текущий статус vs Целевая архитектура
**Текущее состояние**: `InventoryService` работает как традиционный CRUD-сервис, обращаясь к базе данных при каждой операции (получение предметов, экипировка, перемещение).
**Цель**: Сессионный инвентарь (Session-Based), где состояние загружается в Redis один раз, изменяется там, и асинхронно синхронизируется с БД.

## Проблемы (Gaps)
1.  **Нет сессии в Redis**: `InventoryService` читает из PostgreSQL (`inventory_repo`) при каждом запросе.
2.  **Тяжелые вычисления**: Методы `get_capacity` и `has_free_slots` повторно запрашивают БД и пересчитывают статы каждый раз.
3.  **Отсутствие Core Orchestrator**: Логика находится внутри `InventoryService`, но должен быть `InventoryCoreOrchestrator`, управляющий *Жизненным циклом сессии* (Загрузка -> Кэш -> Сброс в БД).

## План действий
1.  **Создать `InventorySessionManager`**:
    *   Методы: `load_session(char_id)`, `get_session(char_id)`, `save_session(char_id)`.
    *   Структура данных: `InventorySessionDTO` (список предметов, слоты экипировки, кэш статов).
2.  **Рефакторинг `InventoryService`**:
    *   Изменить методы для работы с `InventorySessionDTO` вместо репозиториев БД.
    *   Пример: `equip_item` должен модифицировать DTO в памяти.
3.  **Реализовать `InventoryCoreOrchestrator`**:
    *   Обернуть `InventoryService`.
    *   Обработать `init_session` (Загрузка из БД -> Redis).
    *   Обработать `flush_session` (Redis -> БД) через фоновую задачу или явное сохранение.
4.  **Оптимизация API**:
    *   Создать единый эндпоинт `POST /inventory/action` (или внутренний аналог) для обработки `equip`, `unequip`, `move`, `drop` через Диспетчер.

## Задействованные файлы
*   `apps/game_core/game_service/inventory/inventory_service.py` (Основная логика, требует рефакторинга)
*   `apps/game_core/game_service/inventory/inventory_logic_helper.py` (Вспомогательная логика)
*   `apps/bot/ui_service/inventory/inventory_bot_orchestrator.py` (Оркестратор бота)
*   `apps/bot/handlers/callback/ui/inventory/inventory_main.py` (Хендлер бота)
*   `apps/bot/core_client/inventory_client.py` (Клиент для общения с Core)
