# Lobby Service

[← Back to Services](./README.md)

## Class: LobbyService

**File:** `backend/domains/user_features/account/services/lobby_service.py`

### Overview
Сервис управления персонажами пользователя: список, создание Character Shell, удаление.
Реализует Cache-Aside паттерн для оптимизации чтения списка персонажей.

### Dependencies
- `CharactersRepoORM` - Repository для работы с БД
- `AccountSessionService` - Сервис для управления кэшем лобби
- `OnboardingService` - Для инициализации Onboarding после создания Shell

---

## Methods

### `get_characters_list(user_id: int) -> list[CharacterReadDTO]`
Возвращает список персонажей пользователя с Cache-Aside стратегией.

**Flow:**
1. Попытка чтения из Redis: `session_service.get_lobby_cache(user_id)`
2. Если найдено → парсинг и возврат
3. Если НЕ найдено (Cache Miss):
   - SELECT из PostgreSQL: `repo.get_characters(user_id)`
   - Сохранение в Redis: `session_service.set_lobby_cache(user_id, characters)` (TTL 3600s)
4. Возврат списка

**Returns:** `list[CharacterReadDTO]` (может быть пустым списком)

**Business Rules:**
- Возвращает ВСЕ персонажи пользователя (до 4 штук)
- Кэш автоматически обновляется при Cache Miss

---

### `create_character_shell(user_id: int) -> OnboardingUIPayloadDTO`
Создает Character Shell и инициализирует Onboarding.

**Flow:**
1. Проверка лимита персонажей:
   - `repo.get_characters(user_id)`
   - Если `len(characters) >= MAX_CHARACTERS` (4) → raise `BusinessLogicException`

2. Создание в БД:
   - `CharacterShellCreateDTO(user_id=user_id)`
   - `repo.create_character_shell(dto)` → возвращает `CharacterReadDTO`
   - **Создается:** Character + CharacterAttributes + CharacterSymbiote + ResourceWallet (с дефолтами)

3. Инициализация Onboarding:
   - **ПРЯМОЙ вызов** `onboarding_service.initialize(character)` (тот же домен)
   - Создается `ac:{char_id}` со `state=ONBOARDING`
   - Возвращается `OnboardingUIPayloadDTO` (шаг NAME)

4. Инвалидация кэша:
   - `session_service.delete_lobby_cache(user_id)`

**Returns:** `OnboardingUIPayloadDTO` (первый шаг онбординга)

**Business Rules:**
- Максимум 4 персонажа на пользователя
- Character Shell создается с дефолтными значениями:
  - `name` = "Новый персонаж"
  - `gender` = "other"
  - `game_stage` = "creation"
  - `CharacterAttributes` (все = 8)
  - `CharacterSymbiote` (пустой)
  - `ResourceWallet` (пустой)

**Exceptions:**
- `BusinessLogicException` - превышен лимит персонажей

---

### `delete_character(char_id: int, user_id: int) -> bool`
Удаляет персонажа с проверкой владельца.

**Flow:**
1. Проверка существования:
   - `repo.get_character(char_id)`
   - Если `None` → raise `NotFoundException`

2. Проверка владельца:
   - Если `character.user_id != user_id` → raise `PermissionDeniedException`

3. Удаление из БД:
   - `repo.delete_characters(char_id)`
   - CASCADE удалит CharacterAttributes, CharacterSymbiote, ResourceWallet

4. Инвалидация кэша:
   - `session_service.delete_lobby_cache(user_id)`

**Returns:** `True` (успешно удален)

**Business Rules:**
- Только владелец может удалить персонажа
- Удаление каскадное (все связанные данные)

**Exceptions:**
- `NotFoundException` - персонаж не найден
- `PermissionDeniedException` - не владелец

---

## Cache Management

### Cache Key
- `lobby:user:{user_id}` - список персонажей пользователя

### TTL
- 3600 секунд (1 час)

### Invalidation Events
- Создание персонажа → `delete_lobby_cache(user_id)`
- Удаление персонажа → `delete_lobby_cache(user_id)`
- Обновление персонажа (name, gender) → НЕ инвалидируем (пока нет такого endpoint)

### Cache-Aside Pattern
**Read Flow:**
```
1. GET lobby:user:{user_id} из Redis
2. If HIT → deserialize, return
3. If MISS → SELECT * FROM characters WHERE user_id = ?
4. SET lobby:user:{user_id} {json} EX 3600
5. Return data
```

**Write Flow:**
```
1. INSERT/DELETE в PostgreSQL
2. DEL lobby:user:{user_id}
3. Next read will populate cache
```

---

## Constants

```python
MAX_CHARACTERS = 4  # Максимум персонажей на пользователя
```

---

## Notes

- Cache-Aside паттерн **перенесен AS-IS** из legacy `lobby_session_manager.py` (проверенная реализация)
- Onboarding вызывается **напрямую** (не через Dispatcher), так как находится в том же домене
- Character Shell создается с минимальными данными, заполнение происходит в Onboarding/Scenario
