# Unit Testing Specifications

## 🧪 Обзор

Юнит-тесты фокусируются на внутренней логике ассемблеров и схем данных. Главная задача — убедиться, что сырые данные из БД корректно трансформируются в структуры для Redis.

## 📦 Компоненты

### 1. PlayerAssembler
**Файл:** `tests/unit/context_assembler/test_player_assembler.py`

**Сценарии:**
*   `test_process_batch_success`: Успешная сборка для списка ID.
*   `test_process_batch_partial_db_failure`: Один из запросов к БД упал (обработка исключений).
*   `test_process_batch_missing_ids`: Запрошен ID, которого нет в БД.
*   `test_dto_selection`: Проверка выбора правильного DTO (Combat/Status/Inventory) в зависимости от scope.

### 2. MonsterAssembler
**Файл:** `tests/unit/context_assembler/test_monster_assembler.py`

**Сценарии:**
*   `test_process_batch_success`: Успешная сборка монстров.
*   `test_equipment_calculation`: Проверка, что `MonsterDataHelper` корректно считает статы шмота.
*   `test_skills_snapshot_handling`: Обработка скиллов (список vs словарь).

### 3. Temp Context Schemas
**Файлы:** `tests/unit/context_assembler/schemas/test_*.py`

**Сценарии:**
*   **CombatTempContext:**
    *   Проверка генерации `math_model` (атрибуты, модификаторы).
    *   Проверка `exclude` в `model_dump` (core поля не должны попадать в output).
*   **MonsterTempContext:**
    *   Проверка совместимости структуры `math_model` с игроком.

## 🛠️ Mocks & Fixtures

Для юнит-тестов используются моки репозиториев:
*   `mock_character_repo`
*   `mock_attributes_repo`
*   `mock_inventory_repo`
*   `mock_skill_repo`

См. раздел [Fixtures](../fixtures/README.md) для деталей.