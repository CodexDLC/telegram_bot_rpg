# 🏗️ Monorepo Structure Standard

[⬅️ Назад: Standards](./README.md)

---

## 🤖 AI CONTEXT

> ⚠️ **Это целевая структура репозитория.** Текущий код может отличаться — идёт рефакторинг.
> - `apps/` — временная папка со старым кодом, **будет удалена**
> - `src/` — весь production код после рефакторинга

---

## 📦 Целевая структура

```plaintext
Telegram_Bot_RPG/
│
├── src/                        # 📦 Production код
│   ├── backend/                # Игровой сервер (API, domains, database)
│   ├── game_client/            # Telegram клиент (handlers, UI)
│   └── shared/                 # Shared библиотека (schemas, enums, config)
│
├── docs/                       # 📚 Документация
├── scripts/                    # 🔧 Dev-скрипты (seed, validate, analyze)
├── tests/                      # 🧪 E2E тесты (опционально)
├── tools/                      # 🛠️ Admin tools (streamlit dashboard)
│
├── deploy/                     # 🐳 Деплой конфиги
│   ├── Dockerfile.backend
│   ├── Dockerfile.client
│   └── docker-compose.yml
│
├── .github/                    # CI/CD workflows
├── pyproject.toml              # Python конфиг проекта
├── run.py                      # Entry point
└── README.md
```

---

## ⚠️ Временные папки (удалить после рефакторинга)

| Папка | Статус | Действие |
|-------|--------|----------|
| `apps/` | 🔴 Legacy | Рефакторится → `src/`, потом удалить |
| `game_client/bot/` | 🔴 Legacy | Мигрирует в `game_client/telegram_bot/features/` |
| `.streamlit/` | 🟡 Migrate | Перенести конфиг в `pyproject.toml` или `tools/` |
| `backend/` (корень) | 🟡 Move | Перенести в `src/backend/` |
| `game_client/` (корень) | 🟡 Move | Перенести в `src/game_client/` |
| `common/` (корень) | 🟡 Move | Переименовать и перенести в `src/shared/` |

---

## 📁 Описание папок

### `src/` — Production код

| Папка | Назначение | Подробнее |
|-------|-----------|-----------|
| `src/backend/` | Игровой сервер: API, domains, database, resources | [Backend_Structure.md](./Backend_Structure.md) |
| `src/game_client/` | Telegram клиент: handlers, UI services, formatters | [Client_Structure.md](./Client_Structure.md) |
| `src/shared/` | Shared библиотека: schemas, enums, config, exceptions | [Shared_Layer.md](./Shared_Layer.md) |

### `docs/` — Документация

```plaintext
docs/
├── architecture/       # Техническая документация (домены, инфраструктура)
├── designer/           # Геймдизайн (механики, баланс, лор)
├── management/         # Управление (roadmap, tasks, standards)
└── structure_manifest/ # AI инструкции, навигация
```

### `scripts/` — Dev-скрипты

Утилиты для разработки и отладки:
- `seed_world_gen.py` — генерация мира
- `validate_gamedata.py` — валидация game data
- `analyze_balance.py` — анализ баланса

### `tests/` — E2E тесты (опционально)

```plaintext
tests/
├── e2e/            # End-to-end тесты (если понадобятся)
└── conftest.py     # Общие fixtures
```

> ⚠️ **Unit и Integration тесты** живут внутри доменов — см. [Backend_Structure.md](./Backend_Structure.md)

### `tools/` — Инструменты

- Streamlit admin dashboard
- Debug утилиты
- Внутренние инструменты разработки

### `deploy/` — Деплой

```plaintext
deploy/
├── Dockerfile.backend      # Docker для backend
├── Dockerfile.client       # Docker для telegram client
├── docker-compose.yml      # Локальная разработка
└── k8s/                    # (будущее) Kubernetes манифесты
```

---

## 🔧 Импорты

**Текущее состояние:** Абсолютные импорты от корня.

**После завершения рефакторинга:** Относительные импорты внутри каждого пакета.

```python
# Внутри src/backend/
from .domains.combat import CombatService  # относительный

# Из shared
from src.shared.schemas import UserDTO      # или настроить через pyproject.toml
```

---

## 📋 Чеклист миграции в src/

- [ ] Создать `src/` директорию
- [ ] Перенести `backend/` → `src/backend/`
- [ ] Перенести `game_client/` → `src/game_client/`
- [ ] Перенести `common/` → `src/shared/`
- [ ] Обновить импорты
- [ ] Перенести Docker файлы в `deploy/`
- [ ] Удалить `apps/` после полного рефакторинга
- [ ] Обновить `pyproject.toml` (paths)
- [ ] Обновить CI/CD workflows
