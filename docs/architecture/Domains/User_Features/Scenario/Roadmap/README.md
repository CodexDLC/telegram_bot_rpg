# 📂 Scenario Roadmap

[⬅️ Назад: Scenario Domain](../README.md)

---

## Текущий статус

**Phase:** 🚧 Implementation / Cleanup

**Refactoring:** Архитектура внедрена, но требуется доработка контента и хендлеров.

---

## 📅 Активные задачи

### 🛠️ [Task: Cleanup & Fixes](./Task_Analysis_and_Docs.md)
Детальный план по исправлению `TutorialHandler` и JSON-файлов.

- [ ] **TutorialHandler:** Реализовать методы сохранения (убрать TODO).
- [ ] **Content:** Адаптировать `tutorial_arrival.json` под новые ID предметов/скиллов.

---

## Что СДЕЛАНО (MVP 0.1.0)

### ✅ Phase 1: Backend Architecture
- [x] `ScenarioService` (Core Logic)
- [x] `ScenarioGateway` (API Entry)
- [x] `ScenarioRepositoryORM` (Postgres + JSONB)
- [x] `ScenarioDirector` (Engine переходов)
- [x] `ScenarioFormatter` (DTO Builder)

### ✅ Phase 2: Client Implementation
- [x] `ScenarioClient` (HTTP)
- [x] `ScenarioBotOrchestrator` (UI Logic)
- [x] `ScenarioUIService` (Adaptive Keyboards)
- [x] `ScenarioHandler` (Aiogram)

---

## TODO (Post-MVP)

### Phase 4: Advanced Features
- [ ] **Context Assembler Integration:** Использование данных мира/персонажа в условиях переходов.
- [ ] **Dynamic Dialogs:** Генерация диалогов через LLM (опционально).
- [ ] **Quest Log:** Отображение активных квестов в меню персонажа.

### Phase 5: Content Expansion
- [ ] Создать квест "Town Hub" (мирная зона).
- [ ] Создать квест "Dungeon Entrance".
