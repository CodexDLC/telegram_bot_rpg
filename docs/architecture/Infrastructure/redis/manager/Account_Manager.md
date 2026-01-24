# 👤 AccountManager

⬅️ [Назад к Managers](../managers.md)

---

## 📋 Overview

**File:** `backend/database/redis/manager/account_manager.py`

**Role:** Управление игровыми сессиями персонажей и кэшем лобби.

**Key Features:**
- RedisJSON для хранения `ac:{char_id}` (AccountContextDTO)
- Точечные обновления секций (Bio, Stats, Attributes, Sessions, State, Location)
- Кэш-менеджмент для Lobby (Cache-Aside паттерн)
- TTL для lobby cache (600s)

---

## 🔑 Redis Keys

### Primary Keys

#### `ac:{char_id}`
**Type:** RedisJSON
**TTL:** None (permanent until logout/cleanup)
**Structure:**
```json
{
  "state": "ONBOARDING",
  "bio": {
    "name": "Aragorn",
    "gender": "male",
    "created_at": "2025-01-20T10:30:00Z"
  },
  "location": {
    "current": "start_village",
    "prev": null
  },
  "stats": {
    "hp": {"cur": 100, "max": 100},
    "mp": {"cur": 50, "max": 50},
    "stamina": {"cur": 100, "max": 100}
  },
  "attributes": {
    "strength": 8,
    "agility": 8,
    "endurance": 8,
    "intelligence": 8,
    "wisdom": 8,
    "men": 8,
    "perception": 8,
    "charisma": 8,
    "luck": 8
  },
  "sessions": {
    "combat_id": "c_123",
    "inventory_id": "inv_456"
  },
  "skills": {}
}
```

#### `lobby:user:{user_id}`
**Type:** String (JSON array)
**TTL:** 600 seconds (10 minutes)
**Structure:**
```json
[
  {
    "character_id": 1,
    "name": "Aragorn",
    "gender": "male",
    "user_id": 123456,
    "location_id": "start_village",
    "vitals_snapshot": {...},
    "created_at": "2025-01-20T10:30:00Z"
  }
]
```

---

## 🛠️ Methods

### Core Account Operations

#### `create_account(char_id: int, initial_data: dict[str, Any]) -> None`
Создает новую игровую сессию персонажа в Redis.

**Parameters:**
- `char_id` - ID персонажа
- `initial_data` - Полная структура `AccountContextDTO` в виде dict

**Redis Command:** `JSON.SET ac:{char_id} $ {data}`

**Used by:**
- `AccountSessionService.create_session()`

---

#### `account_exists(char_id: int) -> bool`
Проверяет существование сессии персонажа.

**Returns:** `True` если ключ существует, иначе `False`

---

#### `get_full_account(char_id: int) -> dict[str, Any] | None`
Получает полную структуру `ac:{char_id}`.

**Returns:** Полный JSON или `None` если ключ не найден

**Used by:**
- `AccountSessionService.get_session()`

---

#### `delete_account(char_id: int) -> None`
Удаляет игровую сессию персонажа.

**Redis Command:** `DEL ac:{char_id}`

**Used by:** Logout flow (TODO)

---

### Bio Section

#### `get_bio(char_id: int) -> dict[str, Any] | None`
Получает секцию `bio` из `ac:{char_id}`.

**Redis Command:** `JSON.GET ac:{char_id} $.bio`

**Returns:**
```python
{
  "name": "Aragorn",
  "gender": "male",
  "created_at": "2025-01-20T10:30:00Z"
}
```

---

#### `update_bio(char_id: int, bio_data: dict[str, Any]) -> None`
Обновляет всю секцию `bio` целиком.

**Redis Command:** `JSON.SET ac:{char_id} $.bio {bio_data}`

**Used by:**
- `AccountSessionService.update_bio()`

---

#### `update_bio_field(char_id: int, field: str, value: Any) -> None`
Обновляет одно поле в секции `bio`.

**Example:**
```python
await account_manager.update_bio_field(42, "name", "Legolas")
```

**Redis Command:** `JSON.SET ac:{char_id} $.bio.{field} {value}`

---

### Stats Section (Vitals)

#### `get_stats(char_id: int) -> dict[str, Any] | None`
Получает все статы (HP, MP, Stamina).

**Returns:**
```python
{
  "hp": {"cur": 85, "max": 100},
  "mp": {"cur": 30, "max": 50},
  "stamina": {"cur": 100, "max": 100}
}
```

---

#### `update_stat(char_id: int, stat_name: str, value: dict[str, int]) -> None`
Обновляет стат целиком (cur + max).

**Example:**
```python
await account_manager.update_stat(42, "hp", {"cur": 100, "max": 100})
```

---

#### `update_stat_current(char_id: int, stat_name: str, value: int) -> None`
Обновляет только текущее значение стата (cur).

**Example:**
```python
await account_manager.update_stat_current(42, "hp", 85)
```

**Redis Command:** `JSON.SET ac:{char_id} $.stats.{stat_name}.cur {value}`

**Used by:** Combat система для обновления HP/MP/Stamina

---

### Attributes Section

#### `get_attributes(char_id: int) -> dict[str, int] | None`
Получает все атрибуты персонажа.

**Returns:**
```python
{
  "strength": 10,
  "agility": 8,
  "endurance": 12,
  ...
}
```

---

#### `update_attributes(char_id: int, attributes: dict[str, int]) -> None`
Обновляет все атрибуты целиком.

**Redis Command:** `JSON.SET ac:{char_id} $.attributes {attributes}`

**Used by:** Scenario система при распределении очков

---

### Sessions Section

#### `get_sessions(char_id: int) -> dict[str, Any] | None`
Получает активные сессии персонажа.

**Returns:**
```python
{
  "combat_id": "c_123",
  "inventory_id": "inv_456"
}
```

---

#### `set_combat_session(char_id: int, session_id: str | None) -> None`
Устанавливает ID активной боевой сессии.

**Example:**
```python
await account_manager.set_combat_session(42, "c_789")
await account_manager.set_combat_session(42, None)  # Clear
```

**Redis Command:** `JSON.SET ac:{char_id} $.sessions.combat_id {session_id}`

---

#### `set_inventory_session(char_id: int, session_id: str | None) -> None`
Устанавливает ID активной сессии инвентаря.

---

### State & Location

#### `get_state(char_id: int) -> str | None`
Получает текущий state персонажа.

**Returns:** `"ONBOARDING"` | `"COMBAT"` | `"SCENARIO"` | `"EXPLORATION"` | etc.

---

#### `set_state(char_id: int, state: str) -> None`
Обновляет state персонажа.

**Example:**
```python
await account_manager.set_state(42, "COMBAT")
```

**Redis Command:** `JSON.SET ac:{char_id} $.state {state}`

**Used by:**
- `AccountSessionService.update_state()`
- Domain transitions (Onboarding → Scenario, Scenario → Combat, etc.)

---

#### `get_location(char_id: int) -> dict[str, Any] | None`
Получает информацию о локации персонажа.

**Returns:**
```python
{
  "current": "dark_forest",
  "prev": "start_village"
}
```

---

#### `set_location(char_id: int, location_id: str) -> None`
Обновляет текущую локацию персонажа.

**Example:**
```python
await account_manager.set_location(42, "dark_forest")
```

**Redis Command:** `JSON.SET ac:{char_id} $.location.current {location_id}`

**Used by:** Exploration система при перемещении

---

### Lobby Cache Management

#### `get_lobby_cache(user_id: int) -> list[dict[str, Any]] | None`
Получает закэшированный список персонажей пользователя.

**Returns:** Список `CharacterReadDTO` в виде dict или `None` (Cache Miss)

**Used by:**
- `AccountSessionService.get_lobby_cache()`
- `LobbyService.get_characters_list()` (Cache-Aside)

---

#### `set_lobby_cache(user_id: int, characters_data: list[dict[str, Any]]) -> None`
Сохраняет список персонажей в кэш.

**Redis Command:** `SET lobby:user:{user_id} {json_data} EX 600`

**TTL:** 600 секунд (10 минут)

**Used by:**
- `AccountSessionService.set_lobby_cache()`
- `LobbyService.get_characters_list()` (после загрузки из БД)

---

#### `delete_lobby_cache(user_id: int) -> None`
Инвалидирует кэш лобби (при создании/удалении персонажа).

**Redis Command:** `DEL lobby:user:{user_id}`

**Used by:**
- `AccountSessionService.delete_lobby_cache()`
- `LobbyService.create_character_shell()`
- `LobbyService.delete_character()`

---

## 🔄 Integration Points

### Account Domain
- **AccountSessionService** - основной клиент, использует все методы для управления `ac:{char_id}`
- **OnboardingService** - обновляет Bio через `update_bio()`
- **LobbyService** - управляет lobby cache через `get/set/delete_lobby_cache()`
- **LoginService** - восстанавливает сессию через `get_full_account()`

### Other Domains
- **Combat Domain** - обновляет HP/MP/Stamina через `update_stat_current()`, устанавливает `combat_id`
- **Scenario Domain** - обновляет `state` при переходах, изменяет атрибуты
- **Exploration Domain** - обновляет `location` через `set_location()`
- **Inventory Domain** - устанавливает `inventory_id` через `set_inventory_session()`

---

## 📊 Performance Considerations

### RedisJSON Benefits
- **Точечные обновления** - можно обновить `$.stats.hp.cur` без загрузки всего JSON
- **Атомарность** - каждая команда `JSON.SET` атомарна
- **Эффективность** - не нужно десериализовать/сериализовать весь объект

### Cache Strategy (Lobby)
- **Cache-Aside** - кэш наполняется при первом запросе
- **TTL 600s** - автоматическая инвалидация через 10 минут
- **Manual Invalidation** - при создании/удалении персонажа

### Memory Usage
- `ac:{char_id}` - ~1-2 KB на персонажа
- `lobby:user:{user_id}` - ~0.5-1 KB на пользователя (макс 4 персонажа)

---

## 🔒 Data Consistency

### Write Strategy
- **ac:{char_id}** - пишется только AccountManager (Single Writer)
- **lobby cache** - только LobbyService (через AccountSessionService)

### Read Strategy
- Любой домен может читать `ac:{char_id}` (Multiple Readers)
- При ошибке валидации → fallback на БД

### Invalidation Rules
1. **Lobby cache** инвалидируется при:
   - Создании персонажа (`create_character_shell`)
   - Удалении персонажа (`delete_character`)

2. **ac:{char_id}** НЕ инвалидируется автоматически:
   - Требует явного `delete_account()` при logout

---

## 🚨 Error Handling

### JSON Parsing Errors
```python
try:
    data = json.loads(redis_data)
except json.JSONDecodeError:
    return None  # Caller должен обработать (fallback на БД)
```

### Missing Keys
- Все методы возвращают `None` если ключ не найден
- Caller должен решить: создать новую сессию или вернуть ошибку

### RedisJSON Path Errors
- Если путь `$.bio.name` не существует → Redis вернет `[]`
- AccountManager обрабатывает: `return res[0] if res else None`

---

## 📝 Usage Examples

### Onboarding Flow
```python
# 1. Создание сессии (LoginService)
initial_data = {
    "state": "ONBOARDING",
    "bio": {"name": None, "gender": None, "created_at": None},
    "location": {"current": "start_village", "prev": None},
    "stats": {...},
    "attributes": {...},
    "sessions": {"combat_id": None, "inventory_id": None},
    "skills": {}
}
await account_manager.create_account(char_id, initial_data)

# 2. Установка имени (OnboardingService)
bio = {"name": "Aragorn", "gender": None, "created_at": "..."}
await account_manager.update_bio(char_id, bio)

# 3. Установка пола (OnboardingService)
bio = {"name": "Aragorn", "gender": "male", "created_at": "..."}
await account_manager.update_bio(char_id, bio)

# 4. Завершение (OnboardingService)
await account_manager.set_state(char_id, "SCENARIO")
```

### Combat Flow
```python
# 1. Вход в бой
await account_manager.set_state(char_id, "COMBAT")
await account_manager.set_combat_session(char_id, "c_123")

# 2. Получение урона
await account_manager.update_stat_current(char_id, "hp", 75)

# 3. Использование маны
await account_manager.update_stat_current(char_id, "mp", 20)

# 4. Выход из боя
await account_manager.set_combat_session(char_id, None)
await account_manager.set_state(char_id, "EXPLORATION")
```

### Lobby Cache Flow
```python
# 1. Cache Miss (LobbyService)
cached = await account_manager.get_lobby_cache(user_id)
if cached is None:
    # Загрузка из БД
    characters = await characters_repo.get_characters(user_id)
    # Сохранение в кэш
    chars_data = [char.model_dump(mode="json") for char in characters]
    await account_manager.set_lobby_cache(user_id, chars_data)

# 2. Cache Invalidation (при создании персонажа)
await account_manager.delete_lobby_cache(user_id)
```

---

## 🔮 Future Improvements

### Planned Features
- **Skills Section** - управление активными навыками
- **Logout Worker** - ARQ worker для сохранения `ac:{char_id}` в БД при выходе
- **TTL для ac:{char_id}** - автоматическое удаление неактивных сессий (24 часа?)

### Optimization Ideas
- **Pipeline Commands** - пакетные обновления через Redis Pipeline
- **Lua Scripts** - атомарные операции (например, damage application с проверкой HP > 0)
- **Compression** - сжатие больших JSON структур (если skills станет большим)

---

## 📚 Related Documentation

- [Account Domain - Services](../../../Domains/User_Features/Account/Services/AccountSessionService.md)
- [Redis Key Schema](../key_schema.md)
- [Redis Service Layer](../README.md)
