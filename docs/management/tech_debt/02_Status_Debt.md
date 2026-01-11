# Технический долг: Статус и Меню Персонажа

## Текущий статус vs Целевая архитектура
**Текущее состояние**: `StatusCoreOrchestrator` получает данные из множества репозиториев (`char_repo`, `stats_repo`, `skill_repo`) и пересчитывает все статы через `StatsAggregationService` при каждом запросе.
**Цель**: Кэшированный профиль в Redis. Тяжелые вычисления происходят только при изменении статов (экипировка/повышение уровня), а не при просмотре профиля.

## Проблемы (Gaps)
1.  **Нет кэширования**: Просмотр профиля вызывает полный пересчет модификаторов.
2.  **Сильная связность**: `StatusCoreOrchestrator` знает слишком много о конкретных репозиториях.
3.  **Отсутствие концепции "Сессии"**: Нет "Сессии Статуса", которая хранила бы текущее состояние просмотра.

## План действий
1.  **Реализовать `ProfileCacheService`**:
    *   Хранить `FullCharacterDataDTO` в Redis с TTL (например, 10 минут или до инвалидации).
    *   Ключ: `char:profile:{char_id}`.
2.  **Инвалидация по событиям**:
    *   Когда `InventoryService` меняет экипировку -> Инвалидировать кэш профиля.
    *   Когда происходит `LevelUp` -> Инвалидировать кэш профиля.
3.  **Рефакторинг `StatusCoreOrchestrator`**:
    *   `get_full_character_data`: Сначала проверить Redis. Если промах -> вызвать `StatsAggregationService` -> Сохранить в Redis.
4.  **Единый эндпоинт действий**:
    *   Реализовать `handle_action(action: str, payload: dict)` для прокачки навыков, установки титулов и т.д.

## Задействованные файлы
*   `apps/game_core/game_service/status/status_orchestrator.py` (Оркестратор Core, требует добавления кэша)
*   `apps/game_core/game_service/status/stats_aggregation_service.py` (Сервис расчета статов)
*   `apps/bot/ui_service/status_menu/status_bot_orchestrator.py` (Оркестратор бота)
*   `apps/bot/handlers/callback/ui/status_menu/character_status.py` (Хендлер меню статуса)
*   `apps/bot/core_client/status_client.py` (Клиент)
