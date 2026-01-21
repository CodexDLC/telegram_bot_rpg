# 🗺️ PROJECT ROADMAP (TECHNICAL ALPHA)

> **Status:** Active Refactoring & Core Stabilization
> **Last Update:** 2025-12-07

**Цель:** Стабилизация ядра, переход на чистую архитектуру (v3.1), подготовка к масштабированию контента.

Легенда:
- [x] ✅ Готово
- [/] 🚧 В работе
- [ ] 📅 Запланировано

---

## ✅ History (Phase 1-2)
*   **[x] Архитектура и Ядро:** Модульный монолит, DI, SQLAlchemy, Redis.
*   **[x] Генерация Мира:** Threat System, Zone Orchestrator, Seed Gen.

---

## 🚧 Phase 3: Global Refactoring & Core Stabilization (Current)

Основной фокус на устранении технического долга и внедрении Session-Based архитектуры во все модули.

### 🛡️ Domain Refactoring
*   **[/] Combat System (v3.1):**
    *   [Roadmap](../architecture/Domains/User_Features/Combat/Roadmap/README.md)
    *   Внедрение новой системы пайплайнов и завершения боя (Settlement).
*   **[ ] Inventory System:**
    *   [Roadmap](../architecture/Domains/User_Features/Inventory/Roadmap/README.md)
    *   Миграция на Redis-сессии, механика Risk & Reward.
*   **[ ] Status & Profile:**
    *   [Roadmap](../architecture/Domains/User_Features/Status/Roadmap/README.md)
    *   Кэширование профиля, оптимизация расчетов.
*   **[ ] Lobby & Auth:**
    *   [Roadmap](../architecture/Domains/User_Features/Lobby/Roadmap/README.md)
    *   Переход на Context System для определения состояния игрока.
*   **[ ] Onboarding:**
    *   [Roadmap](../architecture/Domains/User_Features/Onboarding/Roadmap/README.md)
    *   Отказ от FSM в пользу Core Draft Session.
*   **[ ] Scenario & Quests:**
    *   [Roadmap](../architecture/Domains/User_Features/Scenario/Roadmap/README.md)
    *   Анализ текущей логики и подготовка к рефакторингу.
*   **[ ] Exploration:**
    *   [Roadmap](../architecture/Domains/User_Features/Exploration/Roadmap/README.md)
    *   Анализ текущей логики и подготовка к рефакторингу.

### 🏗️ Core Architecture
*   **[/] API Facade (`core_client`):**
    *   Инкапсуляция вызовов к `game_core` для подготовки к микросервисам.
*   **[ ] Game Sync & Session State:**
    *   [Architecture](../architecture/Core/Game_Sync/Architecture_Session_State.md)
    *   Реализация `GameStateOrchestrator` для управления жизненным циклом сессий.

---

## 📅 Phase 4: Content & Gameplay Loop (Next)

Наполнение игры жизнью после стабилизации кода.

*   **[ ] Content Injection:**
    *   Создание библиотеки предметов, рецептов, мобов.
    *   Написание сюжетных квестов (Tutorial Refactoring).
*   **[ ] Monster System:**
    *   [Roadmap](../architecture/Domains/Internal_Systems/Monster_System/Roadmap.md)
    *   Внедрение таксономии и навыков выживания.
*   **[ ] Rifts (Разломы):**
    *   Реализация процедурных данжей (см. Drafts).

---

## 🔮 Phase 5: Infrastructure & Expansion (Future)

Масштабирование и новые платформы.

*   **[ ] Telegram Mini App (TMA):**
    *   Разработка "Библиотеки" (`/help`) и визуальных интерфейсов.
*   **[ ] Infrastructure:**
    *   [CI/CD Strategy](./task/Task_CI_CD_Strategy.md)
    *   [Microservices Migration](./task/Task_Microservices_Migration.md)
*   **[ ] Public Web:**
    *   Вики-сайт на базе кода TMA.
