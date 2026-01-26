# 📱 Arena Client Architecture

[⬅️ Назад: Resources](../Backend/Resources.md)

## 🤖 AI CONTEXT
Client — Telegram-клиент для Arena. Один handler маршрутизирует все callback на orchestrator. Orchestrator координирует HTTP-запросы к backend и рендеринг UI. Polling с анимацией для поиска матча.

## 📍 Расположение
`game_client/telegram_bot/features/arena/`
*   `client.py`
*   `handlers/arena_handler.py`
*   `resources/keyboards/arena_callback.py`
*   `resources/formatters/arena_formatter.py`
*   `system/arena_bot_orchestrator.py`
*   `system/arena_ui_service.py`

## 🔄 Flow
`User Callback` → `arena_handler` (единый роутер) → `ArenaBotOrchestrator.handle_request` → `ArenaClient` (HTTP) → `Backend API` → `ArenaUIService.render` → `ViewSender` → `Telegram`

## 📦 Компоненты

### ArenaClient
**Файл:** `client.py`
**Наследует:** `BaseApiClient`

| Метод | HTTP | Endpoint | Описание |
| :--- | :--- | :--- | :--- |
| `action(char_id, action, mode, value)` | POST | `/arena/{char_id}/action` | Универсальный метод для всех действий |

### ArenaCallback
**Файл:** `resources/keyboards/arena_callback.py`
**Prefix:** `arena`

| Поле | Тип | Описание |
| :--- | :--- | :--- |
| `action` | `str` | `menu_main`, `menu_mode`, `join_queue`, `check_match`, `cancel_queue`, `leave`, `start_battle` |
| `mode` | `str` \| `None` | `1v1`, `group`, `tournament` |
| `value` | `str` \| `None` | Доп. данные если нужны |

### ArenaBotOrchestrator
**Файл:** `system/arena_bot_orchestrator.py`
**Наследует:** `BaseBotOrchestrator`

#### Публичные методы
| Метод | Описание |
| :--- | :--- |
| `handle_request(user_id, callback_data)` | Главная точка входа, роутинг по action |
| `render(payload)` | Рендер payload в `UnifiedViewDTO` (для Director) |
| `get_search_poller(user_id, mode)` | Возвращает функцию для polling |

#### Роутинг в handle_request
| Action | Приватный метод |
| :--- | :--- |
| `menu_main` | `_handle_menu_main()` |
| `menu_mode` | `_handle_menu_mode(mode)` |
| `join_queue` | `_handle_join_queue(mode)` → запускает polling |
| `cancel_queue` | `_handle_cancel_queue(mode)` |
| `leave` | `director.set_scene(LOBBY)` |
| `start_battle` | `director.set_scene(COMBAT)` |

#### Polling логика (join_queue)
1.  Вызывает `client.action("join_queue")`
2.  Получает searching screen
3.  Запускает `UIAnimationService.start_arena_polling()`
4.  Каждые N секунд вызывает `client.action("check_match")`
5.  Если `header.current_state == COMBAT` → выход из polling
6.  Если cancel → выход из polling
7.  Иначе → обновляет анимацию и продолжает

### ArenaUIService
**Файл:** `system/arena_ui_service.py`

| Метод | Входные данные | Возвращает |
| :--- | :--- | :--- |
| `render_screen(payload)` | `ArenaUIPayloadDTO` | `ViewResultDTO` |

#### Логика render_screen
1.  Форматирует текст через `ArenaFormatter`
2.  Строит клавиатуру из `payload.buttons`
3.  Возвращает `ViewResultDTO(text, kb)`

### ArenaFormatter
**Файл:** `resources/formatters/arena_formatter.py`

| Метод | Описание |
| :--- | :--- |
| `format_text(payload)` | Собирает финальный текст (title + description + gs) |
| `add_animation(text, step)` | Заменяет `{ANIMATION}` или добавляет анимацию в конец |

## 🎬 Polling & Animation
**Механизм:** Используем `UIAnimationService` (как в Combat)

### Параметры polling
| Параметр | Значение | Описание |
| :--- | :--- | :--- |
| `timeout` | 60 сек | Максимальное время polling на клиенте |
| `step_delay` | 3 сек | Интервал между `check_match` |
| `animation` | progress bar | Визуальная анимация ожидания |

### Функция check для polling
Возвращает tuple `(UnifiedViewDTO, is_waiting: bool)`

*   `is_waiting=True` → продолжаем polling
*   `is_waiting=False` → выходим (матч найден или отмена)

#### Определение is_waiting
*   `header.current_state == ARENA` → `is_waiting=True`
*   `header.current_state == COMBAT` → `is_waiting=False`

## 🔗 Интеграция с Director
При переходе в бой:
1.  Backend возвращает `header.current_state=COMBAT`
2.  Orchestrator вызывает `check_and_switch_state()`
3.  `Director.set_scene(COMBAT)` переключает на Combat feature
4.  Combat сам запрашивает dashboard по `char_id`