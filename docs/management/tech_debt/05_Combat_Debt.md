# Технический долг: Боевая Система

## Текущий статус vs Целевая архитектура
**Текущее состояние**: Высокое соответствие. Архитектура RBC (Round Based Combat) реализована хорошо.
**Цель**: Полностью функциональный Session-Based бой.

## Проблемы (Gaps)
1.  **Заглушки**: `check_battle_status` возвращает хардкод "active".
2.  **Делегирование**: `use_item` и `switch_target` полагаются на `CombatService`, который требует полной проверки.
3.  **Надежность Супервизора**: Нужно убедиться, что `restore_active_battles` действительно вызывается при старте приложения.

## План действий
1.  **Реализовать `check_battle_status`**:
    *   Читать поле `winner` из Redis Meta.
    *   Возвращать "finished", если победитель установлен.
2.  **Проверить `CombatService`**:
    *   Убедиться, что `use_consumable` корректно уменьшает количество предметов в Инвентаре (или помечает их использованными в сессии).
3.  **Хук запуска**:
    *   Проверить `main.py` или событие `startup`, вызывается ли `CombatOrchestratorRBC.restore_active_battles()`.

## Задействованные файлы
*   `apps/game_core/game_service/combat/combat_orchestrator_rbc.py` (Основной оркестратор)
*   `apps/game_core/game_service/combat/mechanics/combat_service.py` (Сервис механик)
*   `apps/game_core/game_service/combat/supervisor/combat_supervisor.py` (Супервизор)
*   `apps/bot/handlers/callback/game/combat/action_handlers.py` (Хендлеры действий)
*   `apps/bot/core_client/combat_rbc_client.py` (Клиент)
