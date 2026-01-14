# 🧠 Context System (Context Assembler v2)

[⬅️ Назад: Core](../README.md) | [🏠 Архитектура (Root)](../../../README.md)

---

## 🎯 Описание
**Context Assembler v2** — это универсальный агрегатор данных для любого слоя приложения.
Изначально созданный для боевой системы, теперь он обслуживает все модули: Status Screen, Inventory UI, Exploration Checks, Trade.

**Главная идея:** Один запрос — один контекст. Загружаем только то, что нужно (Scope System).

---

## 📚 Структура документации

### 1. [🧠 Concepts (Концепция)](./Concepts/README.md)
Философия, цели и ключевые механики.
*   **[Philosophy](./Concepts/Philosophy.md)** — Зачем нужен v2 и чем он лучше v1.
*   **[Scope System](./Concepts/Scope_System.md)** — Гибкая система областей видимости (`combats`, `status`, `inventory`).
*   **[Data Flow](./Concepts/Data_Flow.md)** — Визуализация потока данных.

### 2. [⚙️ Specs (Спецификация)](./Specs/README.md)
Детальное описание реализации.
*   **[Orchestrator](./Specs/Orchestrator/Service.md)** — Фасад системы.
*   **[Aggregators](./Specs/Aggregators/README.md)** — Сборщики данных (Player, Monster).
*   **[Query Planner](./Specs/Query_Planner/Builder.md)** — Оптимизатор SQL запросов.
*   **[Data Structures](./Data/DTOs.md)** — DTO и схемы Redis.

### 3. [📜 Legacy & Roadmap](./Legacy/README.md)
История изменений и планы.
*   [Migration v1 -> v2](./Legacy/Migration_Log.md)
*   [Known Issues](./Legacy/Known_Issues.md)

---

## 🚀 Quick Start

### Запрос контекста (Python)
```python
request = ContextRequestDTO(
    player_ids=[101],
    scope="combats"  # <-- Определяет, что грузить
)

response = await context_assembler.get_entry_point(
    action="assemble",
    context=request.model_dump()
)
# response.player[101] -> "temp:setup:uuid..."
```
