# 📂 Scenario Data Layer

[⬅️ Назад: Scenario Domain](../README.md)

---

## 🎯 Описание
Слой данных. Описывает модели БД, репозитории и структуру JSON-файлов сценариев.

## 🗺️ Содержание

### 🗄️ Database Models
**File:** `backend/database/postgres/models/scenario.py`

1.  **ScenarioMaster**: Метаданные квеста (название, автор, версия).
2.  **ScenarioNode**: Данные конкретной сцены (текст, кнопки, логика). Хранится как JSONB.
3.  **CharacterScenarioState**: Текущий прогресс игрока (активная нода, контекст переменных).

### 🏛️ Repositories
**File:** `backend/database/postgres/repositories/scenario_repository.py`

*   `ScenarioRepositoryORM`: Реализация на SQLAlchemy.
*   Поддерживает `upsert` для загрузки контента.

---

## 📄 JSON Structure (Content)

Сценарии хранятся в `backend/domains/user_features/scenario/resources/json/`.

### Пример Ноды
```json
{
  "quest_key": "tutorial",
  "node_key": "start",
  "text": "Привет, {char_name}!",
  "actions_logic": {
    "next": {
      "type": "transition",
      "target": "step_2"
    }
  }
}
```
