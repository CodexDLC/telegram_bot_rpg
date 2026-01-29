# 🎮 Backend Structure Standard

[⬅️ Назад: Standards](./README.md)

---

## 🤖 AI CONTEXT

> ⚠️ **Backend** — это игровой сервер. Обрабатывает запросы от клиентов, хранит состояние, выполняет игровую логику.
>
> **Два типа доменов:**
> - **User Features** — внешние, имеют API для клиентов
> - **Internal Systems** — внутренние, используются только другими доменами

---

## 📍 Расположение

```
src/backend/
```

---

## 📁 Целевая структура

```plaintext
src/backend/
│
├── main.py                 # Entry point (FastAPI app)
├── router.py               # Главный роутер (собирает все API)
│
├── core/                   # Инфраструктура
│   ├── config.py           # Settings
│   ├── database.py         # DB connection
│   ├── exceptions.py       # Base exceptions
│   └── security.py         # Auth, tokens
│
├── database/               # Persistence layer
│   ├── postgres/           # PostgreSQL
│   │   ├── models/         # ORM модели
│   │   └── repositories/   # Репозитории
│   └── redis/              # Redis
│       ├── managers/       # Redis managers
│       └── redis_service.py
│
├── dependencies/           # FastAPI dependencies (DI)
│
├── domains/                # 🏰 Бизнес-логика
│   ├── user_features/      # Внешние домены (с API)
│   │   ├── account/
│   │   ├── combat/
│   │   ├── inventory/
│   │   └── ...
│   └── internal_systems/   # Внутренние домены (без API)
│       ├── context_assembler/
│       ├── dispatcher/
│       └── ...
│
├── resources/              # Статические данные (game data)
│   ├── game_data/          # Items, monsters, abilities...
│   └── balance/            # Формулы, веса
│
└── services/               # Общие сервисы
    ├── calculators/
    └── workers/            # ARQ workers (глобальные)
```

---

## 🏰 Структура доменов

### User Features (внешние домены)

Имеют API — клиенты обращаются к ним напрямую.

```plaintext
domains/user_features/{domain}/
│
├── api/                    # 🔴 ОБЯЗАТЕЛЬНО — HTTP endpoints
│   ├── {feature}.py        # FastAPI роутеры
│   └── __init__.py         # Собирает в один router
│
├── gateway/                # 🔴 ОБЯЗАТЕЛЬНО — Точки входа
│   └── {feature}_gateway.py
│
├── services/               # 🔴 ОБЯЗАТЕЛЬНО — Бизнес-логика
│   ├── {feature}_service.py        # Основная логика
│   └── {feature}_session_service.py # Работа с Redis (опционально)
│
├── dto/                    # 🔴 ОБЯЗАТЕЛЬНО — DTO домена
│   └── {feature}_dto.py
│
├── tests/                  # 🔴 ОБЯЗАТЕЛЬНО — Тесты домена
│   ├── unit/
│   ├── integration/
│   └── conftest.py
│
└── ...                     # ⚪ ОПЦИОНАЛЬНО — остальное
```

**Опциональные папки** (зависят от сложности домена):

| Папка | Когда нужна | Пример |
|-------|-------------|--------|
| `orchestrators/` | Координация flow | `combat_entry_orchestrator.py` |
| `engine/` | Чистая логика/математика | `combat_engine/logic/` |
| `workers/` | Фоновые задачи (ARQ) | `workers/tasks/` |
| `data/` | Локальные ресурсы | `locales/` |

---

### Internal Systems (внутренние домены)

Нет API — используются только другими доменами внутри backend.

```plaintext
domains/internal_systems/{system}/
│
├── dto/                    # 🟡 Если есть контракт
│   └── dtos.py
│
├── tests/                  # 🔴 ОБЯЗАТЕЛЬНО — Тесты
│   ├── unit/
│   └── conftest.py
│
└── ...                     # Свободная структура
```

---

## 🧩 Паттерны реализации (Backend Patterns)

### 1. Gateway (Шлюз)
**Ответственность:**
*   Принимает запрос от API.
*   Маршрутизирует запрос на нужный метод Service.
*   Упаковывает результат в `CoreResponseDTO`.
*   Обрабатывает ошибки и логирует их.

**Пример:**
```python
class ArenaGateway:
    async def handle_action(self, char_id: int, action: str, ...) -> CoreResponseDTO:
        try:
            if action == "join_queue":
                return self._success(await self.service.join_queue(...))
            # ...
        except Exception as e:
            logger.exception(...)
            return self._error("Internal Error")
```

### 2. Service (Сервис Домена)
**Ответственность:**
*   Реализует бизнес-логику (правила игры).
*   Работает с DTO.
*   Не знает про HTTP/API.
*   Делегирует работу с данными в SessionService или Repository.
*   Вызывает другие домены через Dispatcher.

**Пример:**
```python
class ArenaService:
    async def join_queue(self, char_id: int, mode: str) -> ArenaUIPayloadDTO:
        gs = await self.session.get_gear_score(char_id)
        await self.session.add_to_queue(char_id, mode, gs)
        return ArenaUIPayloadDTO(...)
```

### 3. SessionService (Сервис Сессии)
**Ответственность:**
*   Инкапсулирует работу с Redis (Managers).
*   Объединяет несколько менеджеров (например, ArenaManager + AccountManager).
*   Предоставляет удобный интерфейс для Service.

**Пример:**
```python
class ArenaSessionService:
    def __init__(self, arena_manager: ArenaManager, account_manager: AccountManager): ...

    async def join_queue(self, char_id: int, mode: str) -> int:
        gs = await self.account_manager.get_gear_score(char_id)
        await self.arena_manager.add_to_queue(mode, char_id, gs)
        return gs
```

### 4. Manager (Redis Manager)
**Ответственность:**
*   Прямой доступ к Redis (get, set, zadd).
*   Знает структуру ключей (`arena:queue:{mode}`).
*   Находится в `backend/database/redis/manager/`.

---

## 🔄 Слои и направление зависимостей

```
API → Gateway → Service → SessionService → Manager (Redis)
                                     ↘ Repository (DB)
                                     ↘ Dispatcher (Other Domains)
```

| Слой | Знает о | Не знает о |
|------|---------|------------|
| API | Gateway, DTO | Services, Engine |
| Gateway | Services, Orchestrators | Engine internals |
| Service | SessionService, Repository, Engine | API, Gateway |
| SessionService | Managers | Service, API |
| Manager | Redis | Service, Logic |

---

## 🧪 Тестирование

Тесты живут **внутри домена**:

```plaintext
domain/tests/
├── unit/               # Изолированные тесты
│   ├── test_service.py
│   └── test_engine.py
├── integration/        # С БД/Redis
│   └── test_gateway.py
└── conftest.py         # Fixtures домена
```

**Правила:**
- `conftest.py` может наследовать fixtures из родительского
- Каждый домен может иметь свои специфичные fixtures
- Unit тесты не трогают БД/Redis
- Integration тесты используют test database

---

## 📋 Чеклист нового домена (User Feature)

- [ ] Создать папку в `domains/user_features/{name}/`
- [ ] Создать `api/` с роутерами
- [ ] Создать `gateway/` с точками входа
- [ ] Создать `services/` с бизнес-логикой
- [ ] Создать `dto/` (или использовать shared)
- [ ] Создать `tests/` с базовой структурой
- [ ] Подключить роутер в главный `router.py`
- [ ] Создать документацию в `docs/architecture/Domains/User_Features/{Name}/`
