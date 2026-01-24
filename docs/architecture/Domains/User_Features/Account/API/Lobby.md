# Lobby API

## Overview

Lobby API управляет персонажами пользователя: список, создание, удаление.

**Примечание:** Выбор персонажа для входа (Login/Resume Session) - ОТДЕЛЬНАЯ ЗАДАЧА, не документируется здесь.

---

## Endpoints

### 0. Initialize Lobby (Auto-Create First Character)

**`POST /account/lobby/{user_id}/initialize`**

Вход в лобби. Если персонажей нет - **автоматически создает первого** и возвращает Onboarding.

#### Response (No Characters - Auto-Create)

**DTO:** `CoreResponseDTO[OnboardingUIPayloadDTO]`

```json
{
  "header": {
    "current_state": "onboarding",
    "error": null
  },
  "payload": {
    "step": "NAME",
    "title": "Создание персонажа",
    "description": "Как будут звать вашего героя?\n\n<i>Введите имя сообщением:</i>",
    "buttons": [],
    "draft": {
      "name": null,
      "gender": null
    }
  }
}
```

#### Response (Has Characters - Show Lobby)

**DTO:** `CoreResponseDTO[LobbyListDTO]`

```json
{
  "header": {
    "current_state": "lobby",
    "error": null
  },
  "payload": {
    "characters": [
      {
        "character_id": 1,
        "name": "Aragorn",
        "gender": "male",
        "hp": 85,
        "created_at": "2025-01-20T10:30:00Z"
      }
    ]
  }
}
```

#### Logic

1. Вызывает `LobbyService.get_characters_list(user_id)`.
2. Если список **пустой** → вызывает `LobbyService.create_character_shell(user_id)`.
3. `create_character_shell()` создает Character Shell и возвращает `OnboardingUIPayloadDTO`.
4. Если список **НЕ пустой** → возвращает `LobbyListDTO`.

#### Side Effects

- Если персонажей 0 → создается Character Shell, инициализируется Onboarding
- Если персонажи есть → просто возвращается список

---

### 1. List Characters

**`GET /account/lobby/{user_id}/characters`**

Получить список всех персонажей пользователя.

#### Response

**DTO:** `CoreResponseDTO[LobbyListDTO]`

```json
{
  "header": {
    "current_state": "lobby",
    "error": null
  },
  "payload": {
    "characters": [
      {
        "character_id": 1,
        "name": "Aragorn",
        "gender": "male",
        "hp": 85,
        "created_at": "2025-01-20T10:30:00Z"
      },
      {
        "character_id": 2,
        "name": "Legolas",
        "gender": "male",
        "hp": 100,
        "created_at": "2025-01-21T14:15:00Z"
      }
    ]
  }
}
```

**Примечание:** Игра НЕ имеет уровней (level/exp), возвращаем только hp из `vitals_snapshot.hp.cur`.

#### Cache Strategy (Cache-Aside)

1. **Ключ:** `lobby:user:{user_id}`
2. **TTL:** 3600 секунд (1 час)
3. **Инвалидация:** при создании/удалении персонажа

---

### 2. Create Character Shell

**`POST /account/lobby/{user_id}/characters`**

Создаёт Character Shell (пустую запись) для Onboarding.

#### Request

**DTO:** `CharacterShellCreateDTO`

```json
{
  "user_id": 12345
}
```

#### Response

**DTO:** `CoreResponseDTO[CharacterShellDTO]`

```json
{
  "header": {
    "current_state": "lobby",
    "error": null
  },
  "payload": {
    "character_id": 42
  }
}
```

#### Side Effects

- Новая запись в таблице `characters`:
  - `user_id`, `created_at`
  - `name` = "Новый персонаж" (default)
  - `gender` = "other" (default)
  - `game_stage` = "creation"
  - `vitals_snapshot` = default (HP 100, MP 50, Stamina 100)

- **Создаются связанные записи с дефолтами:**
  - `CharacterAttributes` (все атрибуты = 8: strength, agility, endurance, intelligence, wisdom, men, perception, charisma, luck)
  - `CharacterSymbiote` (пустой)
  - `ResourceWallet` (пустой)

- Инвалидация кэша `lobby:user:{user_id}`

**Примечание:** Начальные ЗНАЧЕНИЯ атрибутов устанавливаются по умолчанию (все = 8). Scenario Domain может их модифицировать при интро сценарии.

---

### 3. Delete Character

**`DELETE /account/lobby/characters/{char_id}`**

Удаляет персонажа (требуется проверка владельца).

#### Request

**Path Params:**
- `char_id` - ID персонажа

**Query Params:**
- `user_id` - ID владельца (для проверки)

#### Response: Success

```json
{
  "header": {
    "current_state": "lobby",
    "error": null
  },
  "payload": {
    "success": true
  }
}
```

#### Response: Not Owner (403)

```json
{
  "detail": "You are not the owner of this character"
}
```

#### Response: Not Found (404)

```json
{
  "detail": "Character not found"
}
```

#### Side Effects

- Запись удалена из таблицы `characters` (CASCADE удалит связанные данные)
- Инвалидация кэша `lobby:user:{user_id}`
- Очистка Redis сессий персонажа (`ac:{char_id}`, `cs:*`, и т.д.) - FUTURE

---

## Data Models

### LobbyListDTO

**File:** `common/schemas/lobby.py`

```python
class CharacterReadDTO(BaseModel):
    character_id: int
    name: str
    gender: str  # "male" | "female" | "other"
    hp: int  # from vitals_snapshot.hp.cur
    created_at: datetime

class LobbyListDTO(BaseModel):
    characters: list[CharacterReadDTO]
```

### CharacterShellCreateDTO

**File:** `common/schemas/character.py`

```python
class CharacterShellCreateDTO(BaseModel):
    user_id: int
```

### CharacterShellDTO

```python
class CharacterShellDTO(BaseModel):
    character_id: int
```

---

## Architecture

### Layer Structure

```
API → Gateway → Service → Repository
```

### Components

**LobbyGateway** (`backend/domains/user_features/account/gateway/lobby_gateway.py`)
```python
class LobbyGateway:
    # PUBLIC (для API) - возвращает CoreResponseDTO
    async def list_characters(user_id: int) -> CoreResponseDTO[LobbyListDTO]
    async def create_character(user_id: int) -> CoreResponseDTO[CharacterShellDTO]
    async def delete_character(char_id: int, user_id: int) -> CoreResponseDTO[dict]

    # PRIVATE (внутренняя логика) - возвращает чистый DTO
    async def _get_characters_list(user_id: int) -> LobbyListDTO
    async def _create_character_shell(user_id: int) -> CharacterShellDTO
    async def _delete_character(char_id: int, user_id: int) -> bool
```

**LobbyService** (`backend/domains/user_features/account/services/lobby_service.py`)
```python
class LobbyService:
    async def get_characters_list(user_id: int) -> list[CharacterReadDTO]
        # Cache-Aside реализация (ПЕРЕНОС AS-IS из legacy Lobby)

    async def create_character_shell(user_id: int, dto: CharacterShellCreateDTO) -> int
        # INSERT в PostgreSQL, invalidate cache

    async def delete_character(char_id: int, user_id: int) -> bool
        # DELETE из PostgreSQL, invalidate cache

    async def _invalidate_cache(user_id: int) -> None
        # DEL lobby:user:{user_id}
```

**CharactersRepoORM** (`backend/database/postgres/repositories/characters_repo_orm.py`)
```python
class CharactersRepoORM:
    async def get_characters(user_id: int) -> list[Character]
        # SELECT * FROM characters WHERE user_id = ?

    async def create_character_shell(dto: CharacterShellCreateDTO, user_id: int) -> int
        # INSERT INTO characters (...) RETURNING character_id

    async def delete_character(char_id: int) -> None
        # DELETE FROM characters WHERE character_id = ?
```

**API Router** (`backend/domains/user_features/account/api/router.py`)
```python
@router.get("/lobby/{user_id}/characters", response_model=CoreResponseDTO[LobbyListDTO])
async def list_characters(user_id: int, gateway: LobbyGatewayDep):
    # Вызов gateway.list_characters()

@router.post("/lobby/{user_id}/characters", response_model=CoreResponseDTO[CharacterShellDTO])
async def create_character(user_id: int, dto: CharacterShellCreateDTO, gateway: LobbyGatewayDep):
    # Вызов gateway.create_character()

@router.delete("/lobby/characters/{char_id}", response_model=CoreResponseDTO[dict])
async def delete_character(char_id: int, user_id: int, gateway: LobbyGatewayDep):
    # Вызов gateway.delete_character()
```

---

## Client Usage (Telegram Bot)

**AccountClient** (`game_client/telegram_bot/features/account/client.py`)
```python
class AccountClient:
    async def list_characters(user_id: int) -> CoreResponseDTO[LobbyListDTO]
        # HTTP GET /account/lobby/{user_id}/characters

    async def create_character(user_id: int) -> CoreResponseDTO[CharacterShellDTO]
        # HTTP POST /account/lobby/{user_id}/characters

    async def delete_character(char_id: int, user_id: int) -> CoreResponseDTO[dict]
        # HTTP DELETE /account/lobby/characters/{char_id}?user_id={user_id}
```

**LobbyBotOrchestrator** (использует AccountClient)
```python
async def show_lobby(self) -> UnifiedViewDTO:
    # 1. Получить список персонажей
    response = await self.account_client.list_characters(self.user.id)

    # 2. Рендерить UI (сетка 2x2 с персонажами + кнопка "Создать")
    return await self.render(response.payload.characters)
```

---

## Cache Management (Cache-Aside)

### Redis Key

- `lobby:user:{user_id}` - JSON список персонажей

### TTL

- 3600 секунд (1 час)

### Cache-Aside Flow

**Read:**
1. `GET lobby:user:{user_id}` из Redis
2. Если найден → парсим JSON, возвращаем
3. Если НЕ найден → SELECT из PostgreSQL
4. `SET lobby:user:{user_id} {json}` с TTL 3600

**Write:**
1. INSERT/DELETE в PostgreSQL
2. `DEL lobby:user:{user_id}` (инвалидация кэша)

### Invalidation Events

- Создание персонажа → `DEL lobby:user:{user_id}`
- Удаление персонажа → `DEL lobby:user:{user_id}`
- Обновление персонажа (name, gender) → НЕ инвалидируем (пока нет такого endpoint)

**Примечание:** Cache-Aside паттерн переносится AS-IS из legacy `lobby_session_manager.py` (хорошая реализация).

---

## Testing Strategy

### Unit Tests
- LobbyService.get_characters_list() - Cache-Aside логика
- LobbyService.create_character_shell() - invalidation
- CharactersRepoORM CRUD методы

### Integration Tests
- API endpoints (FastAPI TestClient)
- Cache hit/miss проверки
- Full flow: list → create → list (cache invalidation)

### E2E Tests
- Bot → HTTP API → PostgreSQL + Redis
- Character limit (4 персонажа)
- Ownership validation (403 на чужого персонажа)

---

## Notes

- **Max Characters:** 4 персонажа на аккаунт (проверка в create_character_shell)
- **Soft Delete:** Можно реализовать `deleted_at` вместо полного удаления (FUTURE)
- **Character Shell:** Минимальная запись, заполняется в Onboarding
- **No Level/Exp:** Игра не имеет уровней, возвращаем только HP
- **Cache-Aside:** Переносится AS-IS из legacy Lobby (проверенная реализация)
