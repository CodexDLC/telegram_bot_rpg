# Context Assembler v2.0

⬅️ [Назад к Документации](../../../../README.md) | ⬅️ [Назад к Game Core Services](../README.md)

**Универсальный агрегатор данных для любого слоя приложения.**

Context Assembler v2 — это эволюция системы подготовки контекста. Изначально созданный для Combat System, теперь он превращается в универсальный Data Reader, способный обслуживать любые модули игры: Status Screen, Inventory UI, Exploration Checks, Trade, Tutorial и другие.

---

## 📚 Оглавление

### 1. [🧠 Concepts (Концепция)](./concepts/README.md)
Философия, цели и ключевые механики новой версии сборщика контекста.
*   [Philosophy](./concepts/philosophy.md) - Зачем нужен v2 и чем он лучше.
*   [Scope System](./concepts/scope_system.md) - Гибкая система областей видимости данных.
*   [Data Flow](./concepts/data_flow.md) - Визуализация потока данных.

### 2. [⚙️ Specs (Техническая спецификация)](./specs/README.md)
Детальное описание реализации для разработчиков.
*   **[Data Structures](./specs/data_structures/README.md)** - DTO, Redis схемы.
*   **[Components](./specs/components/README.md)** - Архитектура классов (Orchestrator, Assemblers, Formatters).
*   **[Flows](./specs/flows/README.md)** - Диаграммы последовательности и примеры.

### 3. [🗺️ Roadmap (План развития)](./roadmap/README.md)
Планы по внедрению и миграции.
*   [Migration Plan](./roadmap/migration_v1_to_v2.md)
*   [Known Issues](./roadmap/known_issues.md)

---

## 💡 Философия v2

*   **Было (v1):** Специализированный сервис для боя. Всегда загружает ВСЁ (attributes, inventory, skills, vitals) bulk-запросами.
*   **Стало (v2):**
    *   Гибкий агрегатор с системой флагов **Scope**.
    *   Загружает **только то, что нужно** конкретному сценарию.
    *   Один флаг = одна цель (`combats`, `status`, `inventory`).
    *   Оптимизация запросов к БД через **conditional loading**.

---

## 🔑 Ключевые концепции

### 1. Scope System
Единый флаг, который определяет:
1.  Какие таблицы читать из БД.
2.  Какие данные собирать.
3.  Какой Temp DTO формировать.

**Примеры:**
*   `scope="combats"` → загружает боевые статы + equipped items + skills + vitals.
*   `scope="status"` → загружает только attributes + vitals для экрана персонажа.
*   `scope="inventory"` → загружает весь инвентарь + wallet для UI инвентаря.

### 2. Temp DTO Hierarchy
Специализированные контексты для разных задач:
*   **CombatTempContext** — полный боевой контекст (`math_model`, `loadout`, `vitals`).
*   **StatusTempContext** — данные для UI статуса.
*   **InventoryTempContext** — данные для UI инвентаря.

Все наследуются от `BaseTempContext` и имеют общие `core` поля, но разные `computed` fields.

### 3. UUID Keys
Всегда возвращаем `temp:setup:{uuid}` для изоляции контекстов. Каждый запрос = новый UUID = свежий снимок данных без конфликтов.

### 4. Strategy Pattern
Разные типы сущностей (Player, Monster, Pet) обрабатываются разными Assemblers:
*   **PlayerAssembler** — работает с SQL (characters, attributes, inventory, skills).
*   **MonsterAssembler** — работает с generated monsters.
*   **PetAssembler** — будущее расширение.

---

## 🚀 Quick Start

### Запрос контекста для боя
```python
request = ContextRequestDTO(
    player_ids=[101, 102],
    monster_ids=["uuid-mob-1"],
    scope="combats"
)

response = await context_assembler.get_entry_point(
    action="assemble",
    context=request.model_dump()
)

# response.player = {101: "temp:setup:uuid-1", 102: "temp:setup:uuid-2"}
# response.monster = {"uuid-mob-1": "temp:setup:uuid-3"}
```

### Запрос контекста для статуса
```python
request = ContextRequestDTO(
    player_ids=[101],
    scope="status"
)

response = await context_assembler.get_entry_point(
    action="assemble",
    context=request.model_dump()
)

# Загружено только: attributes, vitals, symbiote
# Инвентарь и скиллы НЕ загружались (оптимизация)
```

---

## 📋 Scope Reference

### `combats`
*   **Цель:** Подготовка к бою.
*   **Загружает:**
    *   attributes (`character_attributes`)
    *   inventory (`equipped` only)
    *   skills (`character_skill_progress`)
    *   vitals (redis accounts)
    *   symbiote (`character_symbiotes`)
*   **Temp DTO:** `CombatTempContext`
*   **Computed Fields:**
    *   `math_model` (v:raw структура для боя)
    *   `loadout` (пояс, абилки, оружие)
    *   `vitals` (HP, Energy)

### `status`
*   **Цель:** Экран персонажа.
*   **Загружает:**
    *   attributes
    *   vitals
    *   symbiote
*   **Temp DTO:** `StatusTempContext`
*   **Computed Fields:**
    *   `stats_display` (форматированные статы для UI)
    *   `vitals_display` (HP/Energy bars)

### `inventory`
*   **Цель:** UI инвентаря/торговли.
*   **Загружает:**
    *   inventory (`all` items)
    *   wallet (`resource_wallets`)
*   **Temp DTO:** `InventoryTempContext`
*   **Computed Fields:**
    *   `items_by_slot` (группировка по слотам)
    *   `wallet_display` (валюта, ресурсы, компоненты)

---

## ⚖️ Отличия от v1

| Характеристика | Было (v1) | Стало (v2) |
| :--- | :--- | :--- |
| **Загрузка данных** | Всегда bulk запросы для всех данных | Conditional loading через Scope |
| **Структура DTO** | Один универсальный `TempContextSchema` | Иерархия специализированных Temp DTO |
| **Применение** | Только для боя | Для любого слоя приложения |

**Преимущества v2:**
1.  **Меньше нагрузка на БД** (не тянем лишние данные).
2.  **Быстрее отклик** (меньше данных = быстрее обработка).
3.  **Чище код** (каждый scope = своя логика).
4.  **Легче расширять** (новый scope = новый use case).

---

## 🏗️ Architecture Highlights

### Pattern: Strategy + Facade
*   **Orchestrator** = Facade (единая точка входа).
*   **Assemblers** = Strategies (разная логика для разных типов).

### Pattern: Query Plan Builder
*   Scope → Список таблиц.
*   Динамическое построение запросов.
*   Параллельное выполнение (`asyncio.gather`).

### Pattern: DTO Hierarchy
*   `BaseTempContext` (общие поля).
*   Специализированные контексты (свои computed fields).
*   Computed fields = проекции для конкретных систем.

---

## 🚦 Status

**Current Version:** 2.0-alpha

**Implemented:**
*   ✅ Orchestrator (facade)
*   ✅ PlayerAssembler (strategy)
*   ✅ MonsterAssembler (strategy)
*   ✅ Scope System (combats, status, inventory)
*   ✅ Basic Temp DTO hierarchy

**In Progress:**
*   🚧 Formatters Layer (отложено)
*   🚧 PetAssembler (планируется)
*   🚧 Migration tools (v1 → v2)

**Roadmap:**
*   Full migration from v1
*   Performance benchmarks
*   Advanced scopes (exploration, trade, tutorial)

---

## 🔗 Related Systems
*   **Combat System v3** — основной потребитель (`combats` scope).
*   **Status Service** — использует `status` scope.
*   **Inventory Service** — использует `inventory` scope.
*   **Scenario System** — будет использовать `exploration` scope.

---

## 🤝 Contributing
Перед добавлением нового scope:
1.  Опиши use case в `concepts/scope_system.md`.
2.  Определи список таблиц в **Query Plan Builder**.
3.  Создай Temp DTO (если нужен новый).
4.  Добавь пример в `integration_examples.md`.
