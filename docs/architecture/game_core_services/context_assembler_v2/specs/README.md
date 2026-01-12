# Technical Specifications

⬅️ [Назад к Context Assembler v2](../README.md) | 🏠 [Назад к Документации](../../../../README.md)

Технические спецификации Context Assembler v2 для разработчиков.

---

## 1. [Data Structures (Структуры данных)](./data_structures/README.md)
Описание всех DTO, схем Redis и иерархии Temp Context.
*   **[DTOs](./data_structures/dtos.md)** — Request/Response форматы, контракты API.
*   **[Temp Context Hierarchy](./data_structures/temp_context_hierarchy.md)** — Иерархия контекстов (Base → Combat/Status/Inventory).
*   **[Redis Storage](./data_structures/redis_storage.md)** — Формат хранения в Redis, TTL, ключи.

## 2. [Components (Компоненты системы)](./components/README.md)
Детальное описание каждого компонента с API и логикой работы.
*   **[Orchestrator](./components/orchestrator.md)** — ContextAssemblerOrchestrator (главный фасад).
*   **[Player Assembler](./components/player_assembler.md)** — PlayerAssembler (стратегия для игроков).
*   **[Monster Assembler](./components/monster_assembler.md)** — MonsterAssembler (стратегия для монстров).
*   **[Query Plan Builder](./components/query_plan_builder.md)** — Построение плана запросов на основе scope.
*   **[Formatters Layer](./components/formatters_layer.md)** — Слой форматирования данных (будущее).

## 3. [Flows (Потоки данных)](./flows/README.md)
Диаграммы и описания процессов обработки.
*   **[Request Flow](./flows/request_flow.md)** — Детальная цепочка обработки запроса.
*   **[Integration Examples](./flows/integration_examples.md)** — Примеры использования из разных модулей (Combat, Status, Inventory).

---

## Navigation Guide

*   **Если ты хочешь понять контракты API:**
    *   Читай [data_structures/dtos.md](./data_structures/dtos.md)
*   **Если ты хочешь понять внутреннюю архитектуру:**
    *   Читай [components/](./components/README.md) (начни с `orchestrator.md`)
*   **Если ты хочешь интегрировать Context Assembler в свой модуль:**
    *   Читай [flows/integration_examples.md](./flows/integration_examples.md)
*   **Если ты хочешь расширить систему:**
    *   Читай [components/query_plan_builder.md](./components/query_plan_builder.md) и [data_structures/temp_context_hierarchy.md](./data_structures/temp_context_hierarchy.md)
