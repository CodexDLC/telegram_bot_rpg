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
| `services/` | Бизнес-логика | `login_service.py` |
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

## 📊 Примеры реальных доменов

### Account (простой User Feature)

```plaintext
domains/user_features/account/
├── api/
│   ├── lobby.py
│   ├── onboarding.py
│   └── registration.py
├── gateway/
│   ├── lobby_gateway.py
│   ├── login_gateway.py
│   ├── onboarding_gateway.py
│   └── registration_gateway.py
├── services/
│   ├── lobby_service.py
│   ├── login_service.py
│   └── ...
├── dto/                    # (или в shared)
└── tests/
    ├── unit/
    └── integration/
```

### Combat (сложный User Feature)

```plaintext
domains/user_features/combat/
├── api/
│   └── router.py
├── gateway/                # Gateway layer
│   └── combat_gateway.py
├── orchestrators/          # Initialization layer
│   ├── combat_entry_orchestrator.py
│   └── handler/
│       ├── combat_session_service.py
│       ├── initialization/
│       └── runtime/
├── combat_engine/          # Engine layer
│   ├── logic/
│   ├── processors/
│   ├── mechanics/
│   └── workers/
├── dto/
└── tests/
    ├── unit/
    └── integration/
```

### Context Assembler (Internal System)

```plaintext
domains/internal_systems/context_assembler/
├── service.py
├── dtos.py
├── logic/
│   ├── base_assembler.py
│   ├── player_assembler.py
│   └── monster_assembler.py
└── tests/
    └── unit/
```

---

## 🔄 Слои и направление зависимостей

```
API → Gateway → Orchestrator → Service → Engine
                    ↓
              Repository (DB/Redis)
```

| Слой | Знает о | Не знает о |
|------|---------|------------|
| API | Gateway, DTO | Services, Engine |
| Gateway | Services, Orchestrators | Engine internals |
| Orchestrator | Services, Engine | API, другие домены |
| Service | Repository, Engine | API, Gateway |
| Engine | Ничего (stateless) | Всё остальное |

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
- [ ] Создать `dto/` (или использовать shared)
- [ ] Создать `tests/` с базовой структурой
- [ ] Подключить роутер в главный `router.py`
- [ ] Создать документацию в `docs/architecture/Domains/User_Features/{Name}/`
