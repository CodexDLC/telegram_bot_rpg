# 🧠 Context System (Context Assembler v2)

[⬅️ Назад: Core](../../../Core/README.md) | [🏠 Архитектура (Root)](../../../../README.md)

---

## 🎯 Описание
**Context Assembler v2** — это универсальный агрегатор данных для любого слоя приложения.
Изначально созданный для боевой системы, теперь он обслуживает все модули: Status Screen, Inventory UI, Exploration Checks, Trade.

**Главная идея:** Один запрос — один контекст. Загружаем только то, что нужно (Scope System).

---

## 📚 Структура документации

### 1. [🧠 Concepts (Концепция)](Concepts/README.md)
Философия, цели и ключевые механики.
*   **[Philosophy](Concepts/Philosophy.md)** — Зачем нужен v2 и чем он лучше v1.
*   **[Scope System](Concepts/Scope_System.md)** — Гибкая система областей видимости (`combats`, `status`, `inventory`).
*   **[Data Flow](Concepts/Data_Flow.md)** — Визуализация потока данных.

### 2. [⚙️ Specs (Спецификация)](Specs/README.md)
Детальное описание реализации.
*   **[Service API](Specs/Orchestrator/Service.md)** — Описание сервиса `ContextAssemblerService`.
*   **[Aggregators](Specs/Aggregators/README.md)** — Сборщики данных (Player, Monster).
*   **[Query Planner](Specs/Query_Planner/Builder.md)** — Оптимизатор SQL запросов.
*   **[Data Structures](Data/DTOs.md)** — DTO и схемы Redis.

### 3. [📜 Legacy & Roadmap](Legacy/README.md)
История изменений и планы.
*   [Migration v1 -> v2](Legacy/Migration_Log.md)
*   [Known Issues](Legacy/Known_Issues.md)

---

## 🚀 Quick Start

### Прямой вызов (Dependency Injection)

```python
# 1. Инжектим сервис
class MyOrchestrator:
    def __init__(self, assembler: ContextAssemblerService):
        self.assembler = assembler

    async def start_logic(self, char_id: int):
        # 2. Формируем запрос
        request = ContextRequestDTO(
            player_ids=[char_id],
            scope="combats"
        )
        
        # 3. Вызываем (Сервис сам откроет сессию БД)
        response = await self.assembler.assemble(request)
        
        # 4. Используем данные
        redis_key = response.player[char_id]
```
