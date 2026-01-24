# Onboarding Service

[← Back to Services](./README.md)

## Class: OnboardingService

**File:** `backend/domains/user_features/account/services/onboarding_service.py`

### Overview
Сервис управляет процессом создания персонажа.
Работает с RedisJSON (`ac:{char_id}`) для хранения промежуточного состояния (Wizard Flow).

### Methods

#### `initialize(char_id: int, data: Character) -> None`
Инициализирует контекст нового персонажа.
- **Action:** Создает ключ `ac:{char_id}`.
- **Content:**
  ```json
  {
    "state": "onboarding",
    "bio": {"name": null, "gender": null},
    "location": {"current": "creation_hall"}
  }
  ```

#### `set_name(char_id: int, name: str) -> None`
Устанавливает имя персонажа.
- **Action:** `JSON.SET ac:{char_id} .bio.name "Name"`

#### `set_gender(char_id: int, gender: str) -> None`
Устанавливает пол персонажа.
- **Action:** `JSON.SET ac:{char_id} .bio.gender "male"`

#### `finalize(char_id: int) -> None`
**⚠️ TODO - НЕ РЕАЛИЗОВАНО**

Планируемая логика:
1. Обновить `game_stage` в БД через ARQ Worker (асинхронно).
2. Обновить `state` в `ac:{char_id}` на `SCENARIO`.
3. Вызвать `SystemDispatcher` для инициализации Scenario (интро сценарий).

**Зависимости:**
- Scenario Domain миграция
- ARQ Worker для сохранения в БД
