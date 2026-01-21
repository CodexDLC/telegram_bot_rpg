> ⚠️ **DRAFT / NEEDS UPDATE**
> Этот документ описывает проблемы старой архитектуры.
> **Задача:** Расширить документацию на основе текущего кода и создать полноценную задачу по переходу на Core-Side Draft Session.

# Технический долг: Система Онбординга

## Текущий статус vs Целевая архитектура
**Текущее состояние**: "FSM как База Данных". Черновик (имя, пол) хранится в `FSMContext` Бота.
**Цель**: "Сессия Черновика в Core". Черновик хранится в Redis на уровне Core. Бот не хранит состояние данных черновика.

## Проблемы (Gaps)
1.  **Зависимость от платформы**: Если мы добавим Web-клиент, он не увидит черновик, начатый в Telegram.
2.  **Риск потери данных**: Хранилище FSM может быть очищено при перезапуске бота (в зависимости от конфига), тогда как Core Redis персистентен.
3.  **Логика в Хендлере**: `OnboardingHandler` вручную обновляет данные FSM.

## План действий
1.  **Создать `DraftSessionManager` в Core**:
    *   Методы: `update_draft(char_id, field, value)`, `get_draft(char_id)`, `clear_draft(char_id)`.
    *   Хранилище: Redis Hash `onboarding:draft:{char_id}`.
2.  **Рефакторинг `OnboardingCoreOrchestrator`**:
    *   `handle_input(char_id, field, value)`: Валидирует ввод и вызывает `DraftSessionManager`.
    *   `finalize(char_id)`: Читает полный черновик из `DraftSessionManager`, вызывает `CharacterFactory`, очищает черновик.
3.  **Обновить Хендлер Бота**:
    *   Убрать `await state.update_data(...)` для бизнес-данных.
    *   Просто пересылать ввод в `orchestrator.handle_input()`.

## Задействованные файлы
*   `apps/game_core/game_service/onboarding/onboarding_core_orchestrator.py` (Создать/Обновить)
*   `apps/game_core/game_service/onboarding/onboarding_service.py` (Логика сохранения)
*   `apps/bot/handlers/callback/onboarding/onboarding_handler.py` (Хендлер бота, требует очистки от FSM логики)
*   `apps/bot/ui_service/onboarding/onboarding_bot_orchestrator.py` (Оркестратор бота)
*   `apps/bot/core_client/onboarding_client.py` (Клиент)
