# Data Transfer Objects (DTOs)

[← Back to Data](./README.md)

## Request DTOs

### UserUpsertDTO
**Location:** `common/schemas/user.py`
```python
class UserUpsertDTO(BaseModel):
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    language_code: str | None
    is_premium: bool
```

### LobbyInitRequest
```python
class LobbyInitRequest(BaseModel):
    user_id: int
```

### LoginRequest
```python
class LoginRequest(BaseModel):
    char_id: int
```

### CharacterShellCreateDTO
**Location:** `common/schemas/character.py`
```python
class CharacterShellCreateDTO(BaseModel):
    user_id: int
```

---

## Response DTOs

### UserDTO
**Location:** `common/schemas/user.py`
```python
class UserDTO(BaseModel):
    telegram_id: int
    # ... (full fields)
    created_at: datetime
    updated_at: datetime
```

### CharacterReadDTO
**Location:** `common/schemas/character.py`
```python
class CharacterReadDTO(BaseModel):
    char_id: int
    user_id: int
    name: str | None
    gender: str | None
    level: int
    exp: int
    game_stage: str
    created_at: datetime
```

### LobbyInitDTO
**Location:** `common/schemas/lobby.py`
```python
class LobbyInitDTO(BaseModel):
    characters: list[CharacterReadDTO]
```

### OnboardingViewDTO
**Location:** `common/schemas/onboarding.py`
```python
class OnboardingViewDTO(BaseModel):
    step: str
    draft: OnboardingDraftDTO
    error: str | None
```

### CoreResponseDTO[T]
**Location:** `common/schemas/core_response.py`
```python
class CoreResponseDTO(BaseModel, Generic[T]):
    header: GameStateHeader
    payload: T | None
```
