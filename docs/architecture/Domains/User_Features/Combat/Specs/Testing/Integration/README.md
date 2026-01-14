# Integration Testing Specifications

## 🔗 Pipeline Flow
**Component:** `CombatPipeline`

*   `test_full_exchange_flow`: Полный цикл (Builder -> Resolver -> Mechanics).
*   `test_interrupted_flow`: Прерывание пайплайна (например, не хватило маны).

## 🔗 Executor Flow
**Component:** `CombatExecutor`

*   `test_dual_wield_execution`: Запуск двух пайплайнов для двух рук.
*   `test_counter_attack_generation`: Создание задачи на контратаку.
