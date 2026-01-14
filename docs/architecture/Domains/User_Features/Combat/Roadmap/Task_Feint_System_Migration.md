# 🚀 Task: Feint System Migration & Implementation

[⬅️ Назад: Roadmap](../Roadmap.md)

---

## 🎯 Цель
Миграция логики финтов из старой документации (v1) в новую архитектуру (v2) и полная реализация сервиса управления рукой (`FeintService`).

## 📋 Подзадачи (Subtasks)

### 1. Architecture & Design (Архитектура)
- [x] Создать спецификацию `Feint_Service.md`.
- [ ] Обновить `State_Models.md` (добавить `hand`, `pool` в `ActorMetaDTO`).
- [ ] Обновить `Mechanics_Service.md` (интеграция фазы `Refill Hand`).
- [ ] Обновить `View_Service.md` (отображение `hand` в UI).

### 2. Core Implementation (Код: Engine)
- [ ] Реализовать `FeintService` (Logic):
    - [ ] `calculate_pool(actor)`
    - [ ] `fill_hand(actor)` (The Buyer algorithm)
    - [ ] `validate_card(actor, card_hash)`
- [ ] Интегрировать вызов `FeintService` в `MechanicsService` (конец хода).
- [ ] Обновить `ContextBuilder` для работы с `FeintCard`.

### 3. Data & Config (Данные)
- [ ] Создать DTO: `FeintCardDTO`, `DeckDTO`.
- [ ] Обновить Redis Schema для хранения руки.
- [ ] Перенести конфиги финтов из старых JSON/Code в `GameData`.

### 4. UI Integration (Клиент)
- [ ] Обновить `CombatDashboardDTO` (добавить список доступных действий).
- [ ] Обновить `ViewService` для генерации клавиатуры на основе `Actor.hand`.

## 🔗 Связанные документы
*   `docs/architecture/Domains/User_Features/Combat/Engine/Logic/Feint_Service.md`
