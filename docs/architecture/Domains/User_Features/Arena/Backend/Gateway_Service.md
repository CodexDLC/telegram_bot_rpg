# ⚙️ Arena Gateway & Service

[⬅️ Назад: Arena API](../API/Arena_API.md)

## 🤖 AI CONTEXT
Gateway принимает `action` от API, маршрутизирует на методы Service, упаковывает результат в `CoreResponseDTO`. Service содержит бизнес-логику матчмейкинга и работает только с Redis.

## 🏗️ Архитектура слоёв
`API Router` → `ArenaGateway` → `ArenaService` → `ArenaManager` (Redis)
                                       → `SystemDispatcher` (создание боя)

## 📦 ArenaGateway
**Файл:** `backend/domains/user_features/arena/gateway/arena_gateway.py`

### Методы

| Метод | Входные данные | Что делает | Возвращает |
| :--- | :--- | :--- | :--- |
| `handle_action` | `char_id`, `action`, `mode`, `value` | Роутинг по action на методы Service | `CoreResponseDTO` |

### Роутинг action

| Action | Вызывает | Результат |
| :--- | :--- | :--- |
| `menu_main` | `service.get_main_menu()` | payload: main menu |
| `menu_mode` | `service.get_mode_menu(mode)` | payload: mode menu |
| `join_queue` | `service.join_queue(char_id, mode)` | payload: searching |
| `check_match` | `service.check_match(char_id, mode)` | payload или redirect to combat |
| `cancel_queue` | `service.cancel_queue(char_id, mode)` | payload: mode menu |
| `leave` | — | redirect to lobby |

## 📦 ArenaService
**Файл:** `backend/domains/user_features/arena/services/arena_service.py`

### Зависимости
*   `ArenaManager` (Redis)
*   `SystemDispatcher` (создание боя)
*   `AccountSessionService` (сессия)

### Методы

| Метод | Что делает |
| :--- | :--- |
| `get_main_menu()` | Возвращает главное меню (тексты из Resources) |
| `get_mode_menu(mode)` | Возвращает меню режима |
| `join_queue(char_id, mode)` | Получает GS, добавляет в очередь Redis, создаёт request |
| `check_match(char_id, mode)` | Ищет противника или проверяет таймаут → создаёт бой |
| `cancel_queue(char_id, mode)` | Удаляет из очереди, возвращает меню |

### Приватные методы

| Метод | Что делает |
| :--- | :--- |
| `_get_gear_score(char_id)` | TODO: пока возвращает константу 100 |
| `_find_opponent(char_id, mode, gs)` | Ищет в Redis ZSET по диапазону GS ±15% |
| `_create_battle(char_id, opponent_id, mode, type)` | Вызывает `SystemDispatcher.combat_entry()` |

## 🔧 Константы

| Константа | Значение | Описание |
| :--- | :--- | :--- |
| `MATCHMAKING_TIMEOUT` | 45 сек | Время до создания Shadow Battle |
| `GS_SEARCH_RANGE` | 0.15 | Диапазон поиска ±15% от GS |

## 🔄 Логика check_match
1.  Получить request из Redis (если нет — вернуть main menu)
2.  Искать противника в диапазоне GS
3.  Если найден → создать PvP бой → redirect to combat
4.  Если таймаут → создать Shadow бой → redirect to combat
5.  Иначе → вернуть searching screen (продолжаем polling)