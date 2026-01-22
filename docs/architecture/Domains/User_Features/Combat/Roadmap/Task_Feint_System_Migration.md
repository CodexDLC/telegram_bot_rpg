# 🚀 Task: Feint System Migration & Implementation

[⬅️ Назад: Roadmap](../Roadmap.md)

---

## 🎯 Цель
Миграция логики финтов из старой документации (v1) в новую архитектуру (v2) и полная реализация сервиса управления рукой (`FeintService`).

## 📋 Подзадачи (Subtasks)

### 1. Architecture & Design (Архитектура)
- [x] Создать спецификацию `Feint_Service.md`.
- [x] Обновить `State_Models.md` (добавить `hand`, `pool` в `ActorMetaDTO`).
- [x] Обновить `Mechanics_Service.md` (интеграция фазы `Refill Hand`).
- [x] Обновить `View_Service.md` (отображение `hand` в UI) - *Реализовано в коде ViewService*.

### 2. Core Implementation (Код: Engine)
- [x] Обновить `ActorMetaDTO`: добавить поля `hand`, `pool`, `deck` (как `feints: FeintHandDTO`)
- [x] Обновить `CombatDataService._build_snapshot`: загрузка `hand`, `pool`, `deck` из Redis (автоматически через `meta`)
- [x] Обновить `CombatDataService.commit_session`: сохранение `hand`, `pool`, `deck` в Redis (автоматически через `meta`)
- [x] Реализовать `FeintService` (Logic):
    - [x] `calculate_pool(actor)` (реализовано как `refill_hand`)
    - [x] `fill_hand(actor)` (реализовано как `refill_hand`)
    - [x] `validate_card(actor, card_hash)` (реализовано в `TurnManager` через `consume_feint_atomic`)
- [x] Интегрировать вызов `FeintService` в `MechanicsService` (конец хода)
- [x] Обновить `ContextBuilder` для работы с `FeintCard` (триггеры оружия)

### 3. Data & Config (Данные)
- [x] Создать DTO: `FeintCardDTO`, `DeckDTO` (как `FeintConfigDTO`, `FeintHandDTO`)
- [x] ✅ Redis Schema уже поддерживает сохранение через `JSON.MERGE` в `$.meta`
- [x] Перенести конфиги финтов из старых JSON/Code в `GameData` (структура создана, наполнение - отдельная задача)

### 4. UI Integration (Клиент)
- [x] Обновить `CombatDashboardDTO` (добавить список доступных действий).
- [x] Обновить `ViewService` для генерации клавиатуры на основе `Actor.hand`.

## 🔗 Связанные документы
*   `docs/architecture/Domains/User_Features/Combat/Engine/Logic/Feint_Service.md`
