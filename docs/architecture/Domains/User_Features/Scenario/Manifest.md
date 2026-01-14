# 📜 Domain: Scenario (Quests & Dialogs)

> **Status:** ⚠️ Needs Refactoring / Active Development

## 🎯 Описание
Полноценный сервис для управления нарративом.
Отвечает за **Диалоги с NPC**, **Квестовые цепочки** и **Туториал**.

## ⚙️ Функционал
1.  **Dialog Engine:** Интерактивные диалоги (NPC реплики -> Варианты ответов игрока).
2.  **Quest Engine:** Отслеживание прогресса квестов (Start, Objectives, Complete).
3.  **Script Runner:** Исполнение JSON-сценариев (выдача наград, изменение стейта мира).

## 📂 Структура (V2 Target)
*   **API:** Handlers (Dialog interaction).
*   **Engine:**
    *   `DialogManager`: Управление потоком текста.
    *   `QuestManager`: Управление состоянием квестов.
*   **Data:**
    *   `ScriptRepository`: Загрузка JSON-сценариев.
    *   `QuestState`: Прогресс игрока.
*   **Utils:**
    *   `ScenarioLoader`: Парсинг и валидация JSON-файлов.

## 🔗 Current Code
*   `apps/game_core/modules/scenario_orchestrator/`
*   `apps/bot/handlers/callback/game/scenario_handler.py`
*   `apps/game_core/utils/scenario_loader.py` (JSON Loader)
