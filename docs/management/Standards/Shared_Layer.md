# 📦 Shared Layer Standard

[⬅️ Назад: Standards](./README.md)

---

## 🤖 AI CONTEXT

> ⚠️ **Shared** (бывший `common/`) — это **библиотека общего кода** между `backend` и `game_client`.
>
> **Главное правило:** Если сомневаешься куда класть — **НЕ клади в shared**.
> Shared должен быть минимальным и содержать только то, что реально нужно обеим сторонам.

---

## 📍 Расположение

```
src/shared/          # Целевое (после миграции)
common/              # Текущее (legacy название)
```

---

## 📁 Целевая структура

```plaintext
src/shared/
│
├── schemas/              # 📋 DTO — контракт между backend и client
│   ├── base.py           # Базовые Pydantic модели
│   ├── user.py           # UserDTO, UserCreateDTO
│   ├── character.py      # CharacterDTO
│   ├── inventory.py      # InventoryDTO, ItemDTO
│   ├── combat.py         # CombatDashboardDTO, CombatLogDTO (View DTO для боя)
│   └── response.py       # CoreResponseDTO, ErrorResponse
│
├── enums/                # 🏷️ Общие перечисления
│   ├── game_state.py     # GameState, SessionState
│   ├── item_types.py     # ItemType, Rarity, Slot
│   ├── combat.py         # CombatPhase, ActionType
│   └── errors.py         # ErrorCode
│
├── constants/            # 🔢 Константы
│   ├── limits.py         # MAX_INVENTORY_SIZE, MAX_LEVEL...
│   ├── defaults.py       # DEFAULT_HP, BASE_STATS...
│   └── magic_numbers.py  # Игровые константы
│
├── config/               # ⚙️ Базовый конфиг
│   ├── settings.py       # Settings (pydantic-settings)
│   └── environment.py    # Environment detection
│
├── exceptions/           # ❌ Общие исключения
│   ├── base.py           # BaseGameException
│   ├── validation.py     # ValidationError, InvalidDataError
│   └── business.py       # NotFoundError, PermissionError
│
└── __init__.py
```

---

## ✅ Что ДОЛЖНО быть в shared

| Папка | Содержимое | Зависимости |
|-------|-----------|-------------|
| `schemas/` | Pydantic DTO для API контракта | `pydantic` only |
| `enums/` | Enum классы | `stdlib` only |
| `constants/` | Числа, строки, лимиты | `stdlib` only |
| `config/` | Settings класс | `pydantic-settings` |
| `exceptions/` | Exception классы | `stdlib` only |

### Критерий попадания в shared:

1. ✅ Используется **и backend, и client**
2. ✅ Не содержит бизнес-логики
3. ✅ Минимальные зависимости (pydantic, stdlib)
4. ✅ Stateless (нет состояния)

---

## ❌ Что НЕ должно быть в shared

| Тип | Куда класть | Почему |
|-----|------------|--------|
| Сервисы с логикой | `backend/services/` | Бизнес-логика |
| Внешние API клиенты | `backend/services/external/` | Зависимости, credentials |
| Analytics | `backend/services/analytics/` | Только backend использует |
| Validators с логикой | Там где используется | Может иметь зависимости |
| ORM модели | `backend/database/models/` | Только backend |
| Redis/DB utilities | `backend/database/` | Инфраструктура |

### Критерий НЕ попадания:

1. ❌ Используется только одной стороной
2. ❌ Содержит бизнес-логику
3. ❌ Имеет тяжёлые зависимости (redis, sqlalchemy, httpx)
4. ❌ Требует конфигурации/credentials

---

## ⚠️ Legacy код (текущее состояние)

Сейчас в `common/` есть код, который нужно перенести:

| Текущее | Целевое | Статус |
|---------|---------|--------|
| `common/schemas/` | `src/shared/schemas/` | 🟢 Остаётся |
| `common/core/config.py` | `src/shared/config/` | 🟢 Остаётся |
| `common/core/logger.py` | `src/shared/` или `backend/` | 🟡 Решить |
| `common/services/gemini_service/` | `src/backend/services/external/` | 🔴 Перенести |
| `common/services/analytics/` | `src/backend/services/analytics/` | 🔴 Перенести |
| `common/services/validators/` | Туда где используется | 🔴 Перенести |
| `common/resources/` | `src/backend/resources/` или `src/shared/` | 🟡 Решить |

---

## 📋 Чеклист миграции

- [ ] Переименовать `common/` → `src/shared/`
- [ ] Создать структуру папок (schemas, enums, constants, config, exceptions)
- [ ] Перенести gemini_service → backend
- [ ] Перенести analytics → backend
- [ ] Перенести validators → по месту использования
- [ ] Разобрать `resources/` — что shared, что backend
- [ ] Обновить импорты
