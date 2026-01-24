# AccountSessionService

[← Back to Services](./README.md)

## Class: AccountSessionService

**File:** `backend/domains/user_features/account/services/account_session_service.py`

### Overview
⭐ **Центральный сервис** для управления `ac:{char_id}` (AccountContextDTO) и кэшем лобби.

Отвечает за:
1. Сборку `AccountContextDTO` из `CharacterReadDTO`
2. CRUD операции с `ac:{char_id}` через `AccountManager`
3. Валидацию данных (DTO <-> Dict)
4. Управление кэшем лобби (`lobby:user:{user_id}`)

### Dependencies
- `AccountManager` - Redis manager для работы с `ac:{char_id}` и lobby cache

---

## Methods

### Session Management (ac:{char_id})

#### `create_session(character: CharacterReadDTO, initial_state: CoreDomain) -> AccountContextDTO`
Создает новую сессию `ac:{char_id}` на основе данных персонажа из БД.

**Flow:**
1. Вызывает `_build_context(character, initial_state)` для сборки `AccountContextDTO`
2. Сохраняет в Redis: `account_manager.create_account(char_id, context.model_dump())`

**Returns:** `AccountContextDTO`

**Used by:** OnboardingService.initialize(), LoginService.login()

---

#### `get_session(char_id: int) -> AccountContextDTO | None`
Получает сессию персонажа из Redis.

**Flow:**
1. Читает из Redis: `account_manager.get_full_account(char_id)`
2. Валидирует через Pydantic: `AccountContextDTO.model_validate(data)`
3. При ошибке валидации → возвращает `None`

**Returns:** `AccountContextDTO | None`

**Used by:** OnboardingService (все методы), LoginService.login()

---

#### `update_bio(char_id: int, bio: BioDict) -> None`
Обновляет секцию `bio` в `ac:{char_id}`.

**Parameters:**
- `bio` - словарь с полями: `name`, `gender`, `created_at`

**Flow:**
1. Вызывает `account_manager.update_bio(char_id, bio)`
2. AccountManager делает точечное обновление через RedisJSON

**Used by:** OnboardingService.set_name(), OnboardingService.set_gender()

---

#### `update_state(char_id: int, state: CoreDomain) -> None`
Обновляет поле `state` в `ac:{char_id}`.

**Parameters:**
- `state` - CoreDomain enum (ONBOARDING, COMBAT, SCENARIO, EXPLORATION)

**Flow:**
1. Вызывает `account_manager.set_state(char_id, state)`

**Used by:** OnboardingService.finalize() (TODO), Combat/Scenario при переходах

---

### Lobby Cache Management

#### `get_lobby_cache(user_id: int) -> list[CharacterReadDTO] | None`
Получает список персонажей из кэша лобби.

**Flow:**
1. Читает из Redis: `account_manager.get_lobby_cache(user_id)`
2. Если `None` → возвращает `None` (Cache Miss)
3. Валидирует каждый элемент через Pydantic: `[CharacterReadDTO.model_validate(char) for char in chars_data]`
4. При ошибке валидации → возвращает `None`

**Returns:** `list[CharacterReadDTO] | None`

**Used by:** LobbyService.get_characters_list()

---

#### `set_lobby_cache(user_id: int, characters: list[CharacterReadDTO]) -> None`
Сохраняет список персонажей в кэш лобби.

**Flow:**
1. Сериализует в JSON: `[char.model_dump(mode="json") for char in characters]`
2. Сохраняет в Redis: `account_manager.set_lobby_cache(user_id, chars_data)` (TTL 3600s)

**Used by:** LobbyService.get_characters_list() (после Cache Miss)

---

#### `delete_lobby_cache(user_id: int) -> None`
Удаляет кэш лобби (инвалидация).

**Flow:**
1. Вызывает `account_manager.delete_lobby_cache(user_id)`

**Used by:** LobbyService.create_character_shell(), LobbyService.delete_character()

---

## Private Methods

### `_build_context(character: CharacterReadDTO, state: CoreDomain) -> AccountContextDTO`
Собирает `AccountContextDTO` из `CharacterReadDTO`.

**Logic:**
1. Извлекает `vitals` из `character.vitals_snapshot`:
   - `hp_cur`, `hp_max`, `mp_cur`, `mp_max`, `stamina_cur`, `stamina_max`
   - Если `None` → дефолтные значения (HP 100/100, MP 50/50, Stamina 100/100)

2. Создает `AttributesDict` с дефолтами (все = 8)

3. Создает `SessionsDict` из `character.active_sessions`:
   - `combat_id`, `inventory_id`

4. Собирает `AccountContextDTO`:
   ```python
   AccountContextDTO(
       state=state,
       bio=BioDict(
           name=character.name,
           gender=character.gender,
           created_at=character.created_at.isoformat()
       ),
       location=LocationDict(
           current=character.location_id,
           prev=character.prev_location_id
       ),
       stats=StatsDict(...),
       attributes=attributes,
       sessions=sessions,
       skills={}
   )
   ```

**Returns:** `AccountContextDTO`

---

## Data Structures

### AccountContextDTO
```python
class AccountContextDTO(BaseModel):
    state: CoreDomain  # ONBOARDING, COMBAT, SCENARIO, EXPLORATION
    bio: BioDict
    location: LocationDict
    stats: StatsDict
    attributes: AttributesDict
    sessions: SessionsDict
    skills: dict[str, Any] = {}
```

### TypedDicts
```python
class BioDict(TypedDict):
    name: str | None
    gender: str | None
    created_at: str | None

class LocationDict(TypedDict):
    current: str
    prev: str | None

class StatsDict(TypedDict):
    hp: VitalsDict
    mp: VitalsDict
    stamina: VitalsDict

class VitalsDict(TypedDict):
    cur: int
    max: int

class AttributesDict(TypedDict):
    strength: int
    agility: int
    endurance: int
    intelligence: int
    wisdom: int
    men: int
    perception: int
    charisma: int
    luck: int

class SessionsDict(TypedDict):
    combat_id: str | None
    inventory_id: str | None
```

---

## Redis Keys

### ac:{char_id}
**Структура:** RedisJSON
**TTL:** Не установлен (permanent until logout/cleanup)
**Content:** `AccountContextDTO` в JSON

### lobby:user:{user_id}
**Структура:** Redis String (JSON array)
**TTL:** 3600 секунд (1 час)
**Content:** `list[CharacterReadDTO]` в JSON

---

## Notes

- **Центральная точка** для всех операций с `ac:{char_id}` → упрощает изменения структуры
- Валидация через Pydantic → гарантирует type safety
- Разделение ответственности: AccountManager (Redis low-level), AccountSessionService (business logic)
- При ошибке валидации возвращает `None` → вызывающий код должен обработать (fallback на БД)
