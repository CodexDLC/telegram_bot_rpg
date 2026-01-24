# Login Gateway

[← Back to Gateway](./README.md)

## Class: LoginGateway

**File:** `backend/domains/user_features/account/gateway/login_gateway.py`

### Overview
Gateway для входа в игру (Resume Session).
Определяет, в каком состоянии находится персонаж, и направляет его в нужный домен.

### Public Methods

#### `login(char_id: int) -> CoreResponseDTO`
Вход в игру.

**Logic:**
1. Вызывает `LoginService.login(char_id)`.
2. Получает результат (ViewDTO другого домена или Onboarding).
3. Оборачивает в `CoreResponseDTO`.

**Returns:**
- `CoreResponseDTO`:
  - `header.current_state`: Целевой домен (COMBAT, LOBBY, ONBOARDING, etc.).
  - `payload`: ViewDTO целевого домена.

**Example Response (Resume Combat):**
```json
{
  "header": {
    "current_state": "combat"
  },
  "payload": {
    "combat_id": "...",
    "logs": [...]
  }
}
```
