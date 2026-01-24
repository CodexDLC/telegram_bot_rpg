# Fixtures & Mock Data

## 🎭 Концепция

Мы используем централизованные фикстуры в `tests/fixtures/context_assembler_fixtures.py` и `conftest.py`, чтобы избежать дублирования кода создания сложных DTO.

## 🧱 Core Data Fixtures

### Characters
*   `sample_character_meta`: Базовая инфа (ID, Name, Class).
*   `sample_character_attributes`: Полный набор атрибутов (Strength, Agility...).
*   `sample_vitals`: HP/Energy (current/max).

### Inventory
*   `sample_inventory_full`: Набор предметов (Weapon, Armor, Potion).
    *   Включает сложные кейсы: заточка, бонусы, камни.
*   `sample_inventory_equipped`: Только надетые предметы.

### Monsters
*   `sample_monster_orm`: Объект монстра, имитирующий ответ SQLAlchemy.
    *   Включает `scaled_base_stats`, `loadout_ids`, `skills_snapshot`.

## 🛠️ Service Mocks

### Redis Manager Mock
```python
@pytest.fixture
def mock_redis_pipeline():
    pipeline = AsyncMock()
    # По умолчанию возвращает успех для всех операций
    pipeline.execute.return_value = [True, True, True, True] 
    return pipeline
```

### Repository Mocks
Используем `AsyncMock` для всех методов репозиториев.
*   Важно: методы `get_batch` должны возвращать списки или словари, соответствующие входным ID.

## 📄 JSON Samples

В папке `tests/fixtures/samples/` хранятся эталонные JSON-файлы:
*   `expected_combat_context_player.json`
*   `expected_combat_context_monster.json`

Тесты сравнивают результат работы ассемблера с этими файлами для гарантии стабильности контракта.