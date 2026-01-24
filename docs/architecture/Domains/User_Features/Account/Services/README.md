# Account Domain - Services Layer

[← Back to Account](../README.md)

## Overview
Services Layer - бизнес-логика и управление процессами Account Domain.

### Responsibilities
- Валидация бизнес-правил
- Координация между Repository, Redis, и другими сервисами
- Управление транзакциями и side effects
- Cache management (для Lobby)

### Structure

```
services/
├── registration_service.py      # User Upsert логика
├── lobby_service.py             # Character CRUD + Cache-Aside
├── onboarding_service.py        # Wizard Flow (Onboarding)
├── login_service.py             # Восстановление ac:{char_id}
└── account_session_service.py   # ⭐ Центральный сервис для ac:{char_id}
```

---

## Services Overview

### RegistrationService
**Responsibilities:** User Upsert операция (INSERT или UPDATE).

**Methods:**
- `upsert_user(user_dto: UserUpsertDTO) -> UserDTO`

**См. подробно:** [Registration.md](./Registration.md)

---

### LobbyService
**Responsibilities:** Character CRUD, Cache-Aside паттерн, инициализация Onboarding.

**Methods:**
- `get_characters_list(user_id: int) -> list[CharacterReadDTO]`
- `create_character_shell(user_id: int) -> OnboardingUIPayloadDTO`
- `delete_character(char_id: int, user_id: int) -> bool`

**Cache Strategy:** Cache-Aside (Redis `lobby:user:{user_id}`, TTL 3600s)

**См. подробно:** [Lobby.md](./Lobby.md)

---

### OnboardingService
**Responsibilities:** Wizard Flow управление, работа с `ac:{char_id}` через AccountSessionService.

**Methods:**
- `initialize(character: CharacterReadDTO) -> OnboardingUIPayloadDTO`
- `resume_session(char_id: int) -> OnboardingUIPayloadDTO`
- `set_name(char_id: int, name: str) -> OnboardingUIPayloadDTO`
- `set_gender(char_id: int, gender: str) -> OnboardingUIPayloadDTO`
- `finalize(char_id: int) -> None` (⚠️ TODO)

**См. подробно:** [Onboarding.md](./Onboarding.md)

---

### LoginService
**Responsibilities:** Восстановление игровой сессии, определение state, ownership validation.

**Methods:**
- `login(char_id: int, user_id: int) -> AccountContextDTO`

**См. подробно:** [Login.md](./Login.md)

---

### AccountSessionService
**Responsibilities:** Центральный сервис для управления `ac:{char_id}`, Lobby cache management.

**Methods:**
- `create_session(character: CharacterReadDTO, initial_state: CoreDomain) -> AccountContextDTO`
- `get_session(char_id: int) -> AccountContextDTO | None`
- `update_bio(char_id: int, bio: BioDict) -> None`
- `update_state(char_id: int, state: CoreDomain) -> None`
- `get_lobby_cache(user_id: int) -> list[CharacterReadDTO] | None`
- `set_lobby_cache(user_id: int, characters: list[CharacterReadDTO]) -> None`
- `delete_lobby_cache(user_id: int) -> None`

**См. подробно:** [AccountSessionService.md](./AccountSessionService.md)

---

## Contents

- **[Registration.md](./Registration.md)** - RegistrationService
- **[Lobby.md](./Lobby.md)** - LobbyService
- **[Onboarding.md](./Onboarding.md)** - OnboardingService
- **[Login.md](./Login.md)** - LoginService
- **[AccountSessionService.md](./AccountSessionService.md)** - AccountSessionService
