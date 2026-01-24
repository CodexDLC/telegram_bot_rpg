# Onboarding API

## Overview

Onboarding API управляет процессом создания персонажа (Wizard Flow).

---

## Endpoint

**`POST /account/onboarding/{char_id}/action`**

Обрабатывает шаги визарда создания персонажа.

---

## Request

### Path Parameters
- `char_id` (int): ID персонажа

### Body

```json
{
  "action": "set_name | set_gender | finalize",
  "value": "..." (опционально)
}
```

**Примеры:**

```json
// Шаг 1: Установка имени
{
  "action": "set_name",
  "value": "Aragorn"
}

// Шаг 2: Выбор пола
{
  "action": "set_gender",
  "value": "male"
}

// Шаг 3: Финализация
{
  "action": "finalize"
}
```

---

## Response

### Success - set_name (200 OK)

**DTO:** `CoreResponseDTO[OnboardingUIPayloadDTO]`

```json
{
  "header": {
    "current_state": "onboarding",
    "error": null
  },
  "payload": {
    "step": "GENDER",
    "title": "Выбор пола",
    "description": "Приятно познакомиться, <b>Aragorn</b>!\n\nВыберите пол вашего персонажа:",
    "buttons": [
      {
        "text": "Мужской",
        "action": "set_gender",
        "value": "male"
      },
      {
        "text": "Женский",
        "action": "set_gender",
        "value": "female"
      }
    ],
    "draft": {
      "name": "Aragorn",
      "gender": null
    }
  }
}
```

### Success - set_gender (200 OK)

**DTO:** `CoreResponseDTO[OnboardingUIPayloadDTO]`

```json
{
  "header": {
    "current_state": "onboarding",
    "error": null
  },
  "payload": {
    "step": "CONFIRM",
    "title": "Подтверждение",
    "description": "Проверьте данные:\n\n👤 Имя: <b>Aragorn</b>\n⚧ Пол: <b>Мужской</b>\n\nВсё верно?",
    "buttons": [
      {
        "text": "✅ Открыть глаза",
        "action": "finalize",
        "value": null
      }
    ],
    "draft": {
      "name": "Aragorn",
      "gender": "male"
    }
  }
}
```

### Success - finalize (200 OK - Redirect to Scenario)

**DTO:** `CoreResponseDTO`

```json
{
  "header": {
    "current_state": "scenario",
    "error": null
  },
  "payload": null
}
```

**⚠️ TODO:** Payload для Scenario пока пустой (зависит от миграции Scenario Domain).

---

## Behavior

### Wizard Flow

1. **NAME** → Ввод имени (текстовое сообщение от пользователя)
2. **GENDER** → Выбор пола (кнопки: Мужской / Женский)
3. **CONFIRM** → Подтверждение данных (кнопка "Открыть глаза")
4. **FINALIZE** → Переход в Scenario Domain

### State Management

Все промежуточные данные хранятся в `ac:{char_id}.bio`:
```json
{
  "name": "Aragorn",
  "gender": "male",
  "created_at": "2025-01-24T12:00:00Z"
}
```

### UI Localization

Тексты и кнопки берутся из `OnboardingResources` (`backend/domains/user_features/account/data/locales/onboarding_resources.py`).

---

## Architecture

### Layer Structure

```
API → Gateway → Service → AccountSessionService → Redis
```

### Components

**OnboardingGateway** (`backend/domains/user_features/account/gateway/onboarding_gateway.py`)
```python
class OnboardingGateway:
    async def handle_action(char_id: int, action: str, value: Any = None) -> CoreResponseDTO
        # PUBLIC - обрабатывает действия пользователя
```

**OnboardingService** (`backend/domains/user_features/account/services/onboarding_service.py`)
```python
class OnboardingService:
    async def set_name(char_id: int, name: str) -> OnboardingUIPayloadDTO
    async def set_gender(char_id: int, gender: str) -> OnboardingUIPayloadDTO
    async def finalize(char_id: int) -> None  # ⚠️ TODO
```

**API Router** (`backend/domains/user_features/account/api/onboarding.py`)
```python
@router.post("/{char_id}/action", response_model=CoreResponseDTO)
async def handle_action(
    char_id: int,
    action: str = Body(..., embed=True),
    value: Any = Body(None, embed=True),
    gateway: OnboardingGateway = Depends()
):
    return await gateway.handle_action(char_id, action, value)
```

---

## Data Models

### OnboardingUIPayloadDTO

**File:** `common/schemas/onboarding.py`

```python
class ButtonDTO(BaseModel):
    text: str
    action: str
    value: str | None = None

class OnboardingDraftDTO(BaseModel):
    name: str | None = None
    gender: str | None = None

class OnboardingUIPayloadDTO(BaseModel):
    step: str  # "NAME" | "GENDER" | "CONFIRM"
    title: str
    description: str
    buttons: list[ButtonDTO]
    draft: OnboardingDraftDTO | None = None
    error: str | None = None
```

### OnboardingActionEnum

```python
class OnboardingActionEnum(str, Enum):
    SET_NAME = "set_name"
    SET_GENDER = "set_gender"
    FINALIZE = "finalize"
```

---

## Client Usage (Telegram Bot)

**AccountClient** (`game_client/telegram_bot/features/account/client.py`)
```python
class AccountClient:
    async def onboarding_action(
        char_id: int,
        action: str,
        value: Any = None
    ) -> CoreResponseDTO:
        # POST /account/onboarding/{char_id}/action
```

**OnboardingBotOrchestrator** (использует AccountClient)
```python
async def handle_name_input(self, message: Message) -> UnifiedViewDTO:
    # 1. Получить char_id из FSM context
    # 2. Отправить set_name action
    response = await self.account_client.onboarding_action(
        char_id=char_id,
        action="set_name",
        value=message.text
    )

    # 3. Рендерить следующий шаг (GENDER)
    return await self.render(response.payload)
```

---

## Testing Strategy

### Unit Tests
- OnboardingService: set_name/set_gender валидация
- OnboardingGateway: action routing

### Integration Tests
- API endpoint: полный flow NAME → GENDER → CONFIRM → FINALIZE

### E2E Tests
- Bot → HTTP API → Redis → Scenario redirect

---

## Notes

- **Idempotent:** Можно вызывать set_name/set_gender многократно - обновляется draft в Redis
- **No DB Updates:** Данные хранятся только в `ac:{char_id}` до finalize
- **Fast operation:** ~5-20ms (Redis операции)
- **Finalize - TODO:** Зависит от миграции Scenario Domain и ARQ Worker
