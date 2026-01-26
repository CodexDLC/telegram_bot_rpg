# 📂 Scenario Telegram Bot Client

[⬅️ Назад: Client Interfaces](../README.md)

---

## 🎯 Описание
Реализация клиента для прохождения сценариев в Telegram.
Обеспечивает отображение текста, адаптивных клавиатур и обработку нажатий.

---

## 📁 Структура файлов

`game_client/telegram_bot/features/scenario/`

```plaintext
features/scenario/
├── client.py               # HTTP Client
├── handlers/               # Aiogram Handlers
│   └── scenario_handler.py
├── system/                 # Logic & UI
│   ├── scenario_bot_orchestrator.py
│   └── scenario_ui_service.py
└── resources/              # Resources
    ├── formatters/
    │   └── scenario_formatter.py
    └── keyboards/
        └── scenario_callback.py
```

---

## 🔌 ScenarioClient

**File:** `client.py`

Обертка над HTTP API.
- `initialize(char_id, quest_key)`
- `step(char_id, action_id)`

---

## 🎭 ScenarioBotOrchestrator

**File:** `system/scenario_bot_orchestrator.py`

Координирует процесс.
- **State:** Ожидает `BotState.scenario`.
- **Action Dispatching:**
  - `initialize`: Вызывает API init, рендерит первую сцену.
  - `step`: Вызывает API step, рендерит следующую сцену ИЛИ переключает стейт (если API вернул другой домен).

---

## 🖼️ ScenarioUIService

**File:** `system/scenario_ui_service.py`

Отвечает за красоту.
- **Adaptive Keyboard:** Автоматически размещает кнопки:
  - Короткие (<20 символов) — по 2 в ряд.
  - Длинные — по 1 в ряд.
- **Text Formatting:** Использует `ScenarioFormatter` для обработки спец-тегов (цвета, иконки).

---

## 🎮 Handlers

**File:** `handlers/scenario_handler.py`

Единый хендлер для всех действий сценария.
- Ловит `ScenarioCallback` (`sc:...`).
- Передает управление в `Orchestrator.handle_request`.

---

## 🔄 Flow

1. **Start:**
   - Игрок попадает в сценарий (из Лобби или другого режима).
   - Вызывается `Orchestrator.handle_request(action="initialize")`.
   - API возвращает первую сцену.
   - Бот отправляет сообщение.

2. **Step:**
   - Игрок жмет кнопку.
   - Callback `sc:step:action_id`.
   - `Orchestrator` вызывает `client.step()`.
   - API возвращает новую сцену.
   - Бот редактирует сообщение.

3. **Transition:**
   - Игрок жмет кнопку (например, "В бой").
   - API возвращает `header.current_state = "combat"`.
   - `Orchestrator` видит смену стейта.
   - Вызывает `Director.set_scene("combat")`.
   - Управление передается в `CombatBotOrchestrator`.
