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

### Описание папок

| Папка | Назначение |
|-------|-----------|
| `core/` | Инфраструктура: config, DI, factory |
| `services/` | Общие сервисы: director, sender, animation, error, fsm, reporting |
| `base/` | Базовые классы для наследования (BaseOrchestrator, UnifiedViewDTO) |
| `resources/` | Константы, FSM states |
| `features/` | Фичи (доменный подход) |
| `middlewares/` | Aiogram middlewares |

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
│   └── components/         # Stateless UI рендереры
│       ├── content_ui.py   # Основной контент
│       ├── menu_ui.py      # Меню/логи
│       └── flow_ui.py      # Спец. режимы
│
├── tests/                  # 🔴 ОБЯЗАТЕЛЬНО — Тесты фичи
│   ├── unit/
│   └── conftest.py
│
└── __init__.py
```

---

## 📊 Пример: Combat Feature (эталон)

```plaintext
features/combat/
├── client.py                   # API клиент к backend/combat
├── handlers/
│   └── combat_handlers.py      # Callback handlers (как роутеры)
├── resources/
│   ├── formatters/
│   │   └── combat_formatters.py    # Форматирование текста
│   └── keyboards/
│       └── combat_callback.py      # CallbackData классы
├── system/
│   ├── combat_bot_orchestrator.py  # Главный координатор
│   ├── combat_state_manager.py     # FSM (драфт хода)
│   └── components/                 # Stateless UI рендереры
│       ├── content_ui.py           # Нижнее сообщение (дашборд)
│       ├── menu_ui.py              # Верхнее сообщение (логи)
│       └── flow_ui.py              # Спец. режимы (spectator)
└── tests/
    └── unit/
```

### Как это работает:

1. **Handler** получает callback от Telegram
2. **Handler** вызывает метод **Orchestrator** (`handle_menu_event`, `handle_control_event`...)
3. **Orchestrator**:
   - Вызывает `client.py` → получает данные от backend
   - Вызывает UI компоненты (`content_ui`, `menu_ui`) → получает ViewDTO
   - Работает с FSM через `state_manager`
4. **Orchestrator** возвращает `UnifiedViewDTO` (menu + content)
5. **Handler** отправляет результат в Telegram

---

## 🔄 Слои клиента

```
Handler (callback/message)
    ↓
Orchestrator
    ├── client.py → Backend API
    ├── UI Components (content_ui, menu_ui, flow_ui)
    └── StateManager (FSM)
    ↓
UnifiedViewDTO (menu + content) → Handler → Telegram
```

| Слой | Роль | Файлы |
|------|------|-------|
| **Handler** | Принимает callback/message, как роутер в FastAPI | `handlers/*.py` |
| **Orchestrator** | Координация: вызов API, UI компонентов, FSM | `system/*_orchestrator.py` |
| **API Client** | HTTP запросы к backend | `client.py` |
| **UI Components** | Stateless рендереры (текст + клавиатуры) | `system/components/` |
| **StateManager** | Работа с FSM (драфт, состояние) | `system/*_state_manager.py` |
| **Resources** | Keyboards, formatters, callbacks | `resources/` |

### UnifiedViewDTO

Orchestrator возвращает `UnifiedViewDTO` — унифицированный ответ:

```python
class UnifiedViewDTO:
    menu: ViewDTO | None      # Верхнее сообщение (лог, инфо)
    content: ViewDTO | None   # Нижнее сообщение (основной UI)
```

Handler получает готовый DTO и отправляет в Telegram.

### API контракты (Shared DTO)

DTO которые используются **и backend, и client** — живут в `src/shared/schemas/`:

```python
# src/shared/schemas/combat.py
from shared.schemas.combat import CombatDashboardDTO, CombatLogDTO
```

Это API контракт — backend формирует, client потребляет.

---

## ⚠️ Legacy код

| Папка | Статус | Действие |
|-------|--------|----------|
| `bot/handlers/` | 🔴 Legacy | Мигрировать в `telegram_bot/features/` |
| `bot/ui_service/` | 🔴 Legacy | Мигрировать в `telegram_bot/features/{f}/system/` |
| `bot/resources/` | 🔴 Legacy | Мигрировать в `telegram_bot/common/` или `features/{f}/resources/` |
| `bot/core_client/` | 🔴 Legacy | Мигрировать в `telegram_bot/features/{f}/client.py` |

---

## 📋 Чеклист новой фичи

- [ ] Создать папку `features/{name}/`
- [ ] Создать `client.py` — API клиент
- [ ] Создать `handlers/` — обработчики
- [ ] Создать `resources/` — keyboards, formatters (если нужно)
- [ ] Создать `system/` — orchestrator, components (если сложная)
- [ ] Создать `tests/`
- [ ] Подключить роутер в `core/routers.py`

---

## 📋 Чеклист миграции из bot/

- [ ] Перенести handler из `bot/handlers/callback/{name}/` → `telegram_bot/features/{name}/handlers/`
- [ ] Перенести ui_service из `bot/ui_service/{name}/` → `telegram_bot/features/{name}/system/`
- [ ] Перенести client из `bot/core_client/{name}_client.py` → `telegram_bot/features/{name}/client.py`
- [ ] Перенести resources → `features/{name}/resources/` или `common/`
- [ ] Обновить импорты
- [ ] Удалить старые файлы из `bot/`
