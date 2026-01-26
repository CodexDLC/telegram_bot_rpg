# 📂 Account Telegram Bot Client

[⬅️ Назад: Client Interfaces](../README.md)

---

## 🎯 Описание
Реализация клиентской части Account Domain для Telegram бота.
Использует **Feature-based архитектуру** и **Aiogram 3**.

---

## 📁 Структура файлов

Все файлы находятся в `game_client/telegram_bot/features/account/`:

```plaintext
features/account/
├── client.py               # HTTP Client (AccountClient)
├── handlers/               # Aiogram Handlers
│   ├── lobby_entry_handler.py
│   ├── lobby_handlers.py
│   └── onboarding_handlers.py
├── system/                 # Logic & UI
│   ├── lobby_orchestrator.py
│   ├── lobby_ui.py
│   ├── onboarding_orchestrator.py
│   └── onboarding_ui.py
└── resources/              # Keyboards & Callbacks
    └── keyboards/
        └── account_callbacks.py
```

---

## 🔌 AccountClient (HTTP Layer)

**File:** `client.py`

Отвечает за взаимодействие с Backend API. Наследуется от `BaseApiClient`.

**Основные методы:**
- `register_user(user_dto)` -> POST /account/register
- `initialize_lobby(user_id)` -> POST /account/lobby/.../initialize
- `get_characters(user_id)` -> GET /account/lobby/.../characters
- `create_character(user_id)` -> POST /account/lobby/.../characters
- `delete_character(char_id)` -> DELETE /account/lobby/...
- `login(char_id)` -> POST /account/login
- `onboarding_action(char_id, action, value)` -> POST /account/onboarding/...

---

## 🎭 Orchestrators (Logic Layer)

Оркестраторы связывают API, UI и FSM. Они не зависят от Aiogram типов (Message, CallbackQuery), работая с чистыми данными (User, action_id).

### LobbyOrchestrator
**File:** `system/lobby_orchestrator.py`

Управляет состоянием **LOBBY**.
- **Вход:** `handle_lobby_initialize` (загружает персонажей, показывает меню).
- **Выбор:** `handle_character_select` (показывает карточку).
- **Действия:** `handle_character_create`, `handle_delete_request`, `handle_character_login`.

### OnboardingOrchestrator
**File:** `system/onboarding_orchestrator.py`

Управляет состоянием **ONBOARDING**.
- **Рендер:** `render(payload)` (отображает текущий шаг визарда).
- **Действия:** `handle_onboarding_action` (кнопки), `handle_onboarding_text` (ввод имени).

---

## 🎮 Handlers (Routing Layer)

Принимают события от Telegram и передают их в Оркестраторы.

- **LobbyEntryHandler**: Обрабатывает вход в лобби (кнопка "Начать").
- **LobbyHandler**: Обрабатывает колбэки `acc_lobby:...` (выбор, удаление, логин).
- **OnboardingHandler**: Обрабатывает колбэки `acc_onboard:...` и текстовый ввод в состоянии онбординга.

---

## 🖼️ UI Components (View Layer)

Отвечают за формирование текста и клавиатур. Возвращают `ViewResultDTO`.

### LobbyUI
**File:** `system/lobby_ui.py`
- Меню выбора персонажей (сетка).
- Карточка персонажа.
- Подтверждение удаления.

### OnboardingUI
**File:** `system/onboarding_ui.py`
- Динамический рендер шагов (Title + Description + Buttons).
- Кнопка "Выйти".

---

## 🔄 Data Flow Examples

### 1. Вход в Лобби
1. **User** нажимает "Начать приключение".
2. **LobbyEntryHandler** ловит событие.
3. Вызывает `LobbyOrchestrator.handle_lobby_initialize()`.
4. **Orchestrator** вызывает `AccountClient.initialize_lobby()`.
5. **Backend** возвращает список персонажей.
6. **Orchestrator** вызывает `LobbyUI.render_lobby_menu()`.
7. **Handler** отправляет сообщение с клавиатурой.

### 2. Создание персонажа (Onboarding)
1. **User** нажимает "Создать".
2. **LobbyHandler** -> `LobbyOrchestrator.handle_character_create()`.
3. **Backend** создает заготовку и меняет стейт на `ONBOARDING`.
4. **Orchestrator** видит смену стейта и передает управление в `OnboardingOrchestrator`.
5. **OnboardingOrchestrator** рендерит первый шаг (выбор пола).
