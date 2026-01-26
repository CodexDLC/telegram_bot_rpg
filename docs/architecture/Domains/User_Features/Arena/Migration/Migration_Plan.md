# 🚀 Arena Migration Plan

[⬅️ Назад: Polling](../Client/Polling.md)

## 🤖 AI CONTEXT
План миграции legacy кода Arena в новую архитектуру. Старый код в `apps/game_core/modules/arena/` и `game_client/bot/`. Новый код в `backend/domains/user_features/arena/` и `game_client/telegram_bot/features/arena/`.

## 📍 Legacy Code (удалить после миграции)

### Backend
| Файл | Статус | Описание |
| :--- | :--- | :--- |
| `apps/game_core/modules/arena/arena_orchestrator.py` | 🔴 Закомментирован | Старый orchestrator |
| `apps/game_core/modules/arena/arena_service.py` | 🟡 Активен но сломан | Фасад (импорт мёртвый) |
| `apps/game_core/modules/arena/service_1v1.py` | 🔴 Закомментирован | Логика 1v1 |
| `apps/game_core/modules/arena/matchmaking_service.py` | 🔴 Закомментирован | Расчёт GearScore |

### Client
| Файл | Статус | Описание |
| :--- | :--- | :--- |
| `game_client/bot/core_client/arena_client.py` | 🔴 Закомментирован | Старый client |
| `game_client/bot/ui_service/arena_ui_service/` | 🟡 Частично работает | UI сервисы |
| `game_client/bot/handlers/callback/game/arena/` | 🟡 Активен | Старые handlers |

## 📋 Порядок миграции

### Фаза 1: Backend
| Шаг | Действие | Результат |
| :--- | :--- | :--- |
| 1.1 | Создать структуру папок в `backend/domains/user_features/arena/` | Пустые `init.py` |
| 1.2 | Создать `dto/arena_dto.py` | `ArenaUIPayloadDTO`, `ArenaScreenEnum` |
| 1.3 | Создать `data/arena_resources.py` | Тексты и кнопки |
| 1.4 | Создать `services/arena_service.py` | Бизнес-логика (из legacy `service_1v1`) |
| 1.5 | Создать `gateway/arena_gateway.py` | Роутинг + `CoreResponseDTO` |
| 1.6 | Создать `api/arena.py` | FastAPI router |
| 1.7 | Подключить router в `backend/router.py` | Include router |
| 1.8 | Создать dependency в `backend/dependencies/` | `get_arena_gateway` |

### Фаза 2: Client
| Шаг | Действие | Результат |
| :--- | :--- | :--- |
| 2.1 | Создать структуру папок в `features/arena/` | Пустые `init.py` |
| 2.2 | Создать `resources/keyboards/arena_callback.py` | `ArenaCallback` |
| 2.3 | Создать `resources/formatters/arena_formatter.py` | Форматирование |
| 2.4 | Создать `client.py` | HTTP client |
| 2.5 | Создать `system/arena_ui_service.py` | Рендеринг UI |
| 2.6 | Создать `system/arena_bot_orchestrator.py` | Координация |
| 2.7 | Создать `handlers/arena_handler.py` | Единый handler |
| 2.8 | Подключить router в `core/routers.py` | Include router |
| 2.9 | Добавить arena client в `BotContainer` | `container.arena` |

### Фаза 3: Интеграция
| Шаг | Действие |
| :--- | :--- |
| 3.1 | Добавить `CoreDomain.ARENA` в enums |
| 3.2 | Зарегистрировать Arena в Director registry |
| 3.3 | Проверить переход Lobby → Arena |
| 3.4 | Проверить переход Arena → Combat |
| 3.5 | Проверить переход Arena → Lobby (выход) |

### Фаза 4: Cleanup
| Шаг | Действие |
| :--- | :--- |
| 4.1 | Удалить `apps/game_core/modules/arena/` |
| 4.2 | Удалить `game_client/bot/handlers/callback/game/arena/` |
| 4.3 | Удалить `game_client/bot/ui_service/arena_ui_service/` |
| 4.4 | Удалить `game_client/bot/core_client/arena_client.py` |
| 4.5 | Убрать старые импорты из container |

## 🔄 Что переиспользуем из Legacy
| Компонент | Legacy | Действие |
| :--- | :--- | :--- |
| `ArenaManager` | `backend/database/redis/manager/arena_manager.py` | ✅ Оставляем как есть |
| Логика очередей | `service_1v1.join_queue`, `check_and_match` | 📝 Адаптируем в новый Service |
| UI тексты | `arena_ui_service.py` | 📝 Переносим в Resources |
| Callback structure | `ArenaQueueCallback` | 📝 Упрощаем в `ArenaCallback` |

## ⚠️ Что НЕ переносим
| Компонент | Причина |
| :--- | :--- |
| `ArenaCoreOrchestrator` (backend) | Заменяем на Gateway + Service |
| Прямые вызовы DB session | Service работает только с Redis |
| Множественные handlers | Один handler + роутинг в orchestrator |
| `ArenaState` (отдельный) | Используем `BotState.arena` |

## ✅ Критерии готовности
| Критерий | Проверка |
| :--- | :--- |
| Вход в арену из Lobby | Кнопка → `BotState.arena` → main menu |
| Выбор режима 1v1 | Показ mode menu |
| Поиск противника | Очередь в Redis, polling с анимацией |
| Матч найден | Переход в `BotState.combat` |
| Shadow при таймауте | Backend создаёт shadow, переход в combat |
| Отмена поиска | Выход из очереди, возврат в mode menu |
| Выход из арены | Переход в `BotState.lobby` |