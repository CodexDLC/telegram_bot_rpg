# Login Service

[← Back to Services](./README.md)

## Class: LoginService

**File:** `backend/domains/user_features/account/services/login_service.py`

### Overview
Сервис отвечает за вход в игру и восстановление сессии.

### Methods

#### `login(char_id: int) -> ViewDTO`
Основной метод входа.
1. **Check:** Существует ли `ac:{char_id}`?
2. **Restore:** Если нет -> `restore_context(char_id)`.
3. **Route:** Читает `.state` и вызывает соответствующий обработчик (Onboarding или Dispatcher).

#### `restore_context(char_id: int) -> None`
Восстанавливает контекст из БД.
1. Читает `Character` из БД.
2. Формирует JSON структуру для `ac:{char_id}`.
3. Сохраняет в Redis.
