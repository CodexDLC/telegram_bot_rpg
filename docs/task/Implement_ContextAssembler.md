# Task: Implement ContextAssembler Module

**Цель:** Реализовать модуль `ContextAssembler` для массовой подготовки контекста сущностей (Batch Processing).

**Спецификация:** [docs/architecture/core_services/context_assembler_spec.md](../architecture/core_services/context_assembler_spec.md)

---

## 1. Scaffolding (Структура)
- [ ] Создать папку `apps/game_core/context_assembler/`.
- [ ] Создать папку `apps/game_core/context_assembler/logic/`.
- [ ] Создать файлы: `service.py`, `dtos.py`, `interface.py`.
- [ ] Создать файлы стратегий: `base_assembler.py`, `player_assembler.py`, `monster_assembler.py`.

## 2. DTOs
- [ ] Определить `ContextRequestDTO` (словарь списков ID).
- [ ] Определить `ContextResponseDTO` (словарь словарей ключей).

## 3. Strategies Implementation
- [ ] **BaseAssembler:** Абстрактный метод `process_batch(ids: list[int]) -> dict[int, str]`.
- [ ] **PlayerAssembler:**
    - Реализовать `get_many_players_with_stats(ids)` в репозиториях (оптимизация SQL).
    - Реализовать трансформацию в JSON (Action-Based Strings).
    - Реализовать сохранение в Redis.
- [ ] **MonsterAssembler:**
    - Реализовать загрузку монстров (пока заглушка или Factory).

## 4. Orchestrator Implementation
- [ ] **ContextAssemblerOrchestrator:**
    - Внедрить стратегии.
    - Реализовать `prepare_bulk_context` с использованием `asyncio.gather`.

## 5. Integration Tests
- [ ] Тест: Запрос на 2 игроков и 1 монстра -> Проверка, что вернулось 3 ключа и данные в Redis корректны.
