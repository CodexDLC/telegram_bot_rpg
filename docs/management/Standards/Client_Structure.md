# 📱 Client Structure Standard

[⬅️ Назад: Standards](./README.md)

---

## 🤖 AI CONTEXT

> ⚠️ **Game Client** — это Telegram клиент. Обрабатывает UI, отправляет запросы на backend.
>
> **Две папки:**
> - `telegram_bot/` — **целевая структура** (доменный подход)
> - `bot/` — **legacy**, будет удалён после миграции

---

## 📍 Расположение

```
src/game_client/
```

---

## 📁 Целевая структура

```plaintext
src/game_client/
│
├── telegram_bot/           # 📱 Основной клиент
│   ├── app_telegram.py     # Entry point (Dispatcher, Bot)
│   │
│   ├── core/               # Инфраструктура
│   │   ├── config.py       # Settings
│   │   ├── container.py    # DI container
│   │   ├── api_client.py   # HTTP клиент к backend
│   │   ├── factory.py      # Bot factory
│   │   └── routers.py      # Сборка роутеров
│   │
│   ├── services/           # Общие сервисы клиента
│   │   ├── director/       # GameDirector + Registry (маршрутизация сцен)
│   │   ├── sender/         # ViewSender (отправка в Telegram)
│   │   ├── animation/      # Анимации
│   │   ├── error/          # Обработка ошибок
│   │   ├── fsm/            # Общие FSM handlers (garbage collector)
│   │   └── reporting/      # (будущее) баг репорты, логи для админов
│   │
│   ├── base/               # Базовые классы
│   │   ├── base_orchestrator.py
│   │   ├── base_service.py
│   │   └── view_dto.py     # UnifiedViewDTO
│   │
│   ├── resources/          # Общие ресурсы
│   │   ├── constants.py
│   │   └── states.py       # FSM states
│   │
│   ├── features/           # 🏰 Фичи (доменный подход)
│   │   ├── combat/
│   │   ├── commands/
│   │   ├── account/        # (будущее)
│   │   ├── inventory/      # (будущее)
│   │   └── ...
│   │
│   └── middlewares/        # Aiogram middlewares
│       ├── throttling.py
│       ├── security.py
│       └── user_validation.py
│
└── bot/                    # ⚠️ LEGACY — удалить после миграции
```

---

## 🏰 Структура фичи (Feature)

Каждая фича — самодостаточный модуль:

```plaintext
features/{feature}/
│
├── client.py               # 🔴 ОБЯЗАТЕЛЬНО — API клиент к backend
│
├── handlers/               # 🔴 ОБЯЗАТЕЛЬНО — Aiogram handlers
│   └── {feature}_handlers.py
│
├── resources/              # 🟡 ОПЦИОНАЛЬНО — Ресурсы фичи
│   ├── formatters/         # Форматирование текста
│   └── keyboards/          # Клавиатуры, callback data
│
├── system/                 # 🟡 ОПЦИОНАЛЬНО — Логика UI (для сложных фич)
│   ├── {feature}_bot_orchestrator.py  # Координация: API + UI + FSM
│   ├── {feature}_state_manager.py     # Работа с FSM (драфт, состояние)
│   └── {feature}_ui_service.py        # Рендеринг UI
│
├── tests/                  # 🔴 ОБЯЗАТЕЛЬНО — Тесты фичи
│   ├── unit/
│   └── conftest.py
│
└── __init__.py
```

---

## 🧩 Паттерны реализации (Client Patterns)

### 1. Handler (Обработчик)
**Ответственность:**
*   Принимает callback/message от Aiogram.
*   Действует как роутер: минимум логики.
*   Создает `GameDirector`.
*   Получает `Orchestrator` из `container`.
*   Вызывает метод `Orchestrator`.
*   Отправляет результат через `ViewSender`.

**Пример:**
```python
@router.callback_query(...)
async def handle_arena_action(call, callback_data, state, user, container):
    orchestrator = container.arena
    director = GameDirector(container, state)
    orchestrator.set_director(director)
    
    view_result = await orchestrator.handle_request(user.id, callback_data)
    
    if view_result:
        sender = ViewSender(...)
        await sender.send(view_result)
```

### 2. Orchestrator (Оркестратор)
**Ответственность:**
*   Координирует всю логику фичи.
*   Вызывает API через `client.py`.
*   Вызывает `UIService` для рендеринга.
*   Работает с FSM через `StateManager` (если нужно).
*   Возвращает `UnifiedViewDTO`.

**Пример:**
```python
class ArenaBotOrchestrator(BaseBotOrchestrator):
    async def handle_request(self, user_id, callback_data) -> UnifiedViewDTO:
        char_id = await self.director.get_char_id()
        response = await self.client.action(...)
        
        redirect = await self.check_and_switch_state(response)
        if redirect:
            return redirect
            
        return await self.render(response.payload)
```

### 3. UIService (Сервис UI)
**Ответственность:**
*   Преобразует DTO от бэкенда в `ViewResultDTO`.
*   Использует `Formatter` для текста.
*   Использует `Callback` классы для клавиатур.

**Пример:**
```python
class ArenaUIService:
    def render_screen(self, payload: ArenaUIPayloadDTO) -> ViewResultDTO:
        text = self.formatter.format_text(payload)
        keyboard = self._build_keyboard(payload.buttons)
        return ViewResultDTO(text=text, kb=keyboard)
```

### 4. Formatter (Форматтер)
**Ответственность:**
*   Форматирует текст (HTML, смайлики, подстановка данных).
*   Stateless.

**Пример:**
```python
class ArenaFormatter:
    @staticmethod
    def format_text(payload: ArenaUIPayloadDTO) -> str:
        return f"<b>{payload.title}</b>\n{payload.description}"
```

### 5. Client (API Клиент)
**Ответственность:**
*   Отправляет HTTP запросы к backend.
*   Наследуется от `BaseApiClient`.
*   Парсит ответ в `CoreResponseDTO`.

---

## 🔄 Слои клиента

```
Handler (callback/message)
    ↓
Orchestrator
    ├── client.py → Backend API
    ├── UIService
    │   └── Formatter
    └── StateManager (FSM)
    ↓
UnifiedViewDTO (menu + content) → Handler → ViewSender → Telegram
```

| Слой | Роль | Файлы |
|------|------|-------|
| **Handler** | Принимает callback/message, как роутер в FastAPI | `handlers/*.py` |
| **Orchestrator** | Координация: вызов API, UI компонентов, FSM | `system/*_orchestrator.py` |
| **API Client** | HTTP запросы к backend | `client.py` |
| **UIService** | Stateless рендерер UI | `system/*_ui_service.py` |
| **StateManager** | Работа с FSM (драфт, состояние) | `system/*_state_manager.py` |
| **Resources** | Keyboards, formatters, callbacks | `resources/` |

---

## 📋 Чеклист новой фичи

- [ ] Создать папку `features/{name}/`
- [ ] Создать `client.py` — API клиент
- [ ] Создать `handlers/` — обработчики
- [ ] Создать `resources/` — keyboards, formatters (если нужно)
- [ ] Создать `system/` — orchestrator, ui_service (если сложная)
- [ ] Создать `tests/`
- [ ] Подключить роутер в `core/routers.py`
