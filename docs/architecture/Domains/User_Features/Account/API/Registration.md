# Registration API

## Endpoint

**`POST /account/register`**

Создаёт или обновляет запись пользователя в таблице `users`.

---

## Назначение

Синхронизация данных Telegram профиля с базой данных.
Вызывается при команде `/start` в боте.

---

## Request

### Headers
```
Content-Type: application/json
```

### Body

**DTO:** `UserUpsertDTO` (из `common/schemas/user.py`)

```python
class UserUpsertDTO(BaseModel):
    telegram_id: int        # Required - Telegram User ID
    username: str | None    # Optional - Telegram @username
    first_name: str | None  # Optional - Имя
    last_name: str | None   # Optional - Фамилия
    language_code: str | None  # Optional - Язык (ru, en, etc.)
    is_premium: bool = False   # Optional - Telegram Premium статус
```

### Validation Rules

- `telegram_id` - обязателен, уникальный, integer > 0
- `username` - опционален, max 32 символа
- `first_name` - опционален, max 64 символа
- `last_name` - опционален, max 64 символа
- `language_code` - опционален, ISO 639-1 код (2 символа)
- `is_premium` - опционален, boolean, default: false

---

## Response

### Success (200 OK)

```json
{
  "success": true
}
```

### Errors

#### 400 Bad Request
```json
{
  "detail": "Invalid telegram_id"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Database error: ..."
}
```

---

## Behavior

### Upsert Logic (INSERT or UPDATE)

1. Если пользователь с `telegram_id` **не существует** → создаётся новая запись
2. Если пользователь **существует** → обновляются все поля

**Используется:** `SQLAlchemy session.merge()` - автоматический upsert на основе primary key.

### Side Effects

- Запись в таблице `users` создана/обновлена
- Логирование: `UsersRepoORM | action=upsert_user status=success telegram_id=...`

---

## Architecture

### Layer Structure

```
API → Gateway → Service → Repository
```

### Components

**RegistrationGateway** (`backend/domains/user_features/account/gateway/registration_gateway.py`)
```python
class RegistrationGateway:
    async def upsert_user(telegram_id: int, username: str, ...) -> CoreResponseDTO
        # PUBLIC - для API, возвращает CoreResponseDTO

    async def _execute_upsert(telegram_id: int, username: str, ...) -> UserUpsertDTO
        # PRIVATE - внутренняя логика, возвращает чистый DTO
```

**RegistrationService** (`backend/domains/user_features/account/services/registration_service.py`)
```python
class RegistrationService:
    async def upsert_user(user_dto: UserUpsertDTO) -> None
        # Бизнес-логика: валидация, вызов repo
```

**UsersRepoORM** (`backend/database/postgres/repositories/users_repo_orm.py`)
```python
class UsersRepoORM:
    async def upsert_user(user_data: UserUpsertDTO) -> None
        # Уpsert в PostgreSQL через SQLAlchemy
```

**API Router** (`backend/domains/user_features/account/api/router.py`)
```python
@router.post("/register")
async def register_user(
    user_dto: UserUpsertDTO,
    gateway: RegistrationGatewayDep
) -> dict[str, bool]:
    # Вызов gateway.upsert_user()
    return {"success": True}
```

---

## Client Usage (Telegram Bot)

**AccountClient** (`game_client/telegram_bot/features/account/client.py`)
```python
class AccountClient:
    async def register_user(
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str | None = "ru",
        is_premium: bool = False
    ) -> None:
        # HTTP POST /account/register
```

**StartBotOrchestrator** (использует AccountClient)
```python
async def handle_start(self) -> UnifiedViewDTO:
    # 1. Register/Update user
    await self.account_client.register_user(
        telegram_id=self.user.id,
        username=self.user.username,
        first_name=self.user.first_name,
        ...
    )

    # 2. Render Start Menu
    return await self.render(self.user.first_name)
```

---

## Testing Strategy

### Unit Tests
- RegistrationService.upsert_user() - валидация DTO
- UsersRepoORM.upsert_user() - upsert логика

### Integration Tests
- API endpoint `/account/register` - полный flow

### E2E Tests
- Bot `/start` → HTTP POST → DB upsert

---

## Notes

- **Idempotent:** Можно вызывать многократно - результат одинаковый
- **No state change on client:** Не влияет на FSM бота
- **Fast operation:** ~10-50ms (простой upsert в PostgreSQL)
- **No Redis:** Не использует кэш, только БД
- **Прямой доступ к БД:** Account Domain имеет прямой доступ к PostgreSQL (исключение из правила)
