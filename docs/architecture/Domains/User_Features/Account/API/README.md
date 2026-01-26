# 📂 Account API Layer

[⬅️ Назад: Account Domain](../README.md)

---

## 🎯 Описание
Слой HTTP API для управления пользователями и персонажами.
Предоставляет endpoints для регистрации, лобби, онбординга и входа в игру.

## 🗺️ Содержание

### 📄 Спецификация
Ниже описаны доступные методы API.

---

## Endpoints

### 1. Registration

#### `POST /account/register`

Создаёт или обновляет запись пользователя в БД (User Upsert).

**Request:**
```json
{
  "telegram_id": 123456789,
  "username": "player123",
  "first_name": "John",
  "last_name": "Doe",
  "language_code": "ru",
  "is_premium": false
}
```

**Response:**
```json
{
  "success": true
}
```

**Errors:**
- `400` - Invalid telegram_id
- `500` - Database error

**См. подробно:** [Registration.md](./Registration.md)

---

### 2. Lobby

#### `GET /account/lobby/{user_id}/characters`

Получить список персонажей пользователя.

**Response:**
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

**Cache:** Redis `lobby:user:{user_id}`, TTL 3600s

---

#### `POST /account/lobby/{user_id}/characters`

Создать Character Shell (пустую запись) для Onboarding.

**Request:**
```json
{
  "name": "Aragorn",
  "gender": "male"
}
```

**Response:**
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

**Side Effects:**
- INSERT в `characters` table
- Инвалидация кэша `lobby:user:{user_id}`

---

#### `DELETE /account/lobby/characters/{char_id}`

Удалить персонажа.

**Request Params:**
- `char_id` (path)
- `user_id` (query, для проверки владельца)

**Response:**
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

**Errors:**
- `403` - Not owner
- `404` - Character not found

**См. подробно:** [Lobby.md](./Lobby.md)

---

### 3. Onboarding

#### `POST /account/onboarding/{char_id}/action`

Обрабатывает шаги визарда создания персонажа.

**Actions:**
- `set_name` - установка имени
- `set_gender` - выбор пола
- `finalize` - завершение (redirect в Scenario)

**См. подробно:** [Onboarding.md](./Onboarding.md)

---

### 4. Login

#### `POST /account/lobby/{user_id}/characters/{char_id}/login`

Вход в игру персонажем (Resume Session).

**Logic:**
1. Восстанавливает `ac:{char_id}` из БД (если нет в Redis)
2. Читает `state` из контекста
3. Маршрутизирует в активный домен (ONBOARDING/COMBAT/SCENARIO/EXPLORATION)

**См. подробно:** [Login.md](./Login.md)

---

## Общая структура ответов

Все endpoints (кроме Registration) возвращают `CoreResponseDTO`:

```python
class CoreResponseDTO(BaseModel):
    header: GameStateHeader  # current_state, error
    payload: T | None        # Domain-specific data
```

**Registration** возвращает простой `dict[str, bool]`:
```json
{
  "success": true
}
```

---

## Gateway Pattern

Account Domain использует Gateway Layer:

```
API Endpoint → Gateway (public method) → Service → Repository
                   ↓
            CoreResponseDTO (с header)

Gateway (private method) → Service → Repository
                   ↓
            Clean DTO (без header)
```

**Пример:**
```python
# PUBLIC (для API)
async def list_characters(user_id: int) -> CoreResponseDTO[LobbyListDTO]

# PRIVATE (внутренняя логика)
async def _get_characters_list(user_id: int) -> LobbyListDTO
```

---

## Детальная документация

- **[Registration.md](./Registration.md)** - Registration API (User Upsert)
- **[Lobby.md](./Lobby.md)** - Lobby API (Character CRUD + Initialize)
- **[Onboarding.md](./Onboarding.md)** - Onboarding API (Wizard Flow)
- **[Login.md](./Login.md)** - Login API (Resume Session)
