# 🎓 Domain: Onboarding (Character Creation)

> **Status:** ⚠️ Needs Refactoring (Legacy Code)

## 🎯 Описание
Инструмент создания нового персонажа.
Отвечает только за сбор данных (Пол, Имя, Раса, Класс) и генерацию записи в БД.

## 🔄 Flow
1.  **Input Loop:** Сбор параметров через UI (Wizard).
2.  **Creation:** Создание записи персонажа в БД.
3.  **Handoff:** Передача управления в **Scenario Engine** (запуск скрипта `tutorial_start`).
    *   *Note:* Сам туториал НЕ является частью Onboarding, это сценарий.

## 📂 Структура (V2 Target)
*   **API:** Handlers (Wizard Steps).
*   **Engine:** Character Factory.
*   **Data:** Creation Draft DTO.

## 🔗 Current Code (Legacy)
*   `apps/game_core/modules/onboarding/`
*   `apps/bot/handlers/callback/onboarding/`
