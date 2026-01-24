# Lobby Gateway

[← Back to Gateway](./README.md)

## Class: LobbyGateway

**File:** `backend/domains/user_features/account/gateway/lobby_gateway.py`

### Overview
Gateway для управления персонажами (список, создание, удаление).

### Public Methods

#### `list_characters(user_id: int) -> CoreResponseDTO[LobbyListDTO]`
Возвращает список персонажей пользователя.
- Использует Cache-Aside (через Service).

#### `create_character(user_id: int) -> CoreResponseDTO[CharacterShellDTO]`
Создает пустую болванку персонажа.
- **Input:** `user_id`.
- **Logic:**
  1. Проверяет лимит персонажей.
  2. Создает запись в БД.
  3. Инициализирует Onboarding контекст.
- **Output:** `character_id` созданного персонажа.

#### `delete_character(char_id: int, user_id: int) -> CoreResponseDTO[dict]`
Удаляет персонажа.
- **Validation:** Проверяет, что `user_id` является владельцем `char_id`.
