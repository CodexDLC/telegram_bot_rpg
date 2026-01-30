# 🎮 Arena Handler

[⬅️ Назад: Client Architecture](./Architecture.md)

## 🤖 AI CONTEXT
Один handler обрабатывает все callback арены. Минимум логики — делегирует в orchestrator. Использует `BotState.arena` для всех режимов, разделение через `callback_data.action`.

## 📍 Расположение
**Файл:** `game_client/telegram_bot/features/arena/handlers/arena_handler.py`

## 🔧 Конфигурация Router
| Параметр | Значение |
| :--- | :--- |
| `name` | `arena_handler_router` |
| `State Filter` | `BotState.arena` |
| `Callback Filter` | `ArenaCallback.filter()` |

## 📋 Структура Handler
Единственный handler:

### Декоратор
`@router.callback_query(ArenaCallback.filter(), StateFilter(BotState.arena))`
Ловит все arena callback в состоянии arena.

### Параметры функции
| Параметр | Тип | Источник |
| :--- | :--- | :--- |
| `call` | `CallbackQuery` | Aiogram |
| `callback_data` | `ArenaCallback` | Aiogram Filter |
| `state` | `FSMContext` | Aiogram |
| `user` | `User` | Middleware |
| `container` | `BotContainer` | Middleware |

## 🔄 Логика Handler
**Шаги:**
1.  `await call.answer()`
2.  Проверка `call.bot`
3.  Создание orchestrator из `container.arena`
4.  Создание director с `container` и `state`
5.  `orchestrator.set_director(director)`
6.  Вызов `orchestrator.handle_request(user.id, callback_data)`
7.  Отправка результата через `ViewSender`

## 📊 Особые случаи

### Polling (join_queue)
Когда `action == "join_queue"`:
1.  Handler вызывает `orchestrator.handle_request()`
2.  Orchestrator внутри запускает polling через `UIAnimationService`
3.  Handler ждёт завершения polling
4.  Результат отправляется через `ViewSender`

### Переход в Combat (start_battle)
Когда `action == "start_battle"`:
1.  Orchestrator вызывает `director.set_scene(COMBAT)`
2.  Director переключает state и возвращает view от Combat
3.  Handler отправляет результат

### Выход в Lobby (leave)
Когда `action == "leave"`:
1.  Orchestrator вызывает `director.set_scene(LOBBY)`
2.  Director переключает state и возвращает view от Lobby
3.  Handler отправляет результат

## 🔗 Регистрация Router
**Файл:** `game_client/telegram_bot/core/routers.py`

Добавить импорт и include:

```python

from src.frontend.telegram_bot.features.arena.handlers import arena_handler

main_router.include_router(arena_handler.router)
```

## 📦 Зависимости Handler
| Зависимость | Откуда |
| :--- | :--- |
| `ArenaCallback` | `features/arena/resources/keyboards/` |
| `ArenaBotOrchestrator` | `features/arena/system/` |
| `BotState` | `telegram_bot/resources/states` |
| `GameDirector` | `telegram_bot/services/director/` |
| `ViewSender` | `telegram_bot/services/sender/` |
| `BotContainer` | `telegram_bot/core/container` |