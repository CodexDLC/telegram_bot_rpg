# Registration Gateway

[← Back to Gateway](./README.md)

## Class: RegistrationGateway

**File:** `backend/domains/user_features/account/gateway/registration_gateway.py`

### Overview
Gateway для регистрации и синхронизации пользователей Telegram.

### Public Methods

#### `upsert_user(...) -> CoreResponseDTO[None]`
Создает или обновляет пользователя.

**Parameters:**
- `telegram_id` (int): ID пользователя.
- `username` (str | None): @username.
- `first_name` (str | None): Имя.
- `last_name` (str | None): Фамилия.
- `language_code` (str | None): Язык.
- `is_premium` (bool): Премиум статус.

**Returns:**
- `CoreResponseDTO[None]`: Успех или ошибка.

### Private Methods

#### `_execute_upsert(...) -> None`
Внутренняя логика:
1. Создает `UserUpsertDTO`.
2. Вызывает `RegistrationService.upsert_user`.
