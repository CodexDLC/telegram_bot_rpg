# Onboarding Gateway

[← Back to Gateway](./README.md)

## Class: OnboardingGateway

**File:** `backend/domains/user_features/account/gateway/onboarding_gateway.py`

### Overview
Gateway для управления процессом создания персонажа (Wizard Flow).
Принимает действия от клиента, валидирует их и передает в `OnboardingService`.

### Public Methods

#### `handle_action(char_id: int, action: str, value: Any = None) -> CoreResponseDTO`
Обрабатывает шаги визарда.

**Supported Actions:**
- `set_name`: Установка имени. `value` = str. Возвращает шаг GENDER.
- `set_gender`: Установка пола. `value` = "male" | "female". Возвращает шаг CONFIRM.
- `finalize`: Завершение создания. **Возвращает redirect в SCENARIO** (payload=None).

**Returns:**
- `CoreResponseDTO`:
  - Для `set_name/set_gender`: `current_state=ONBOARDING`, payload=`OnboardingUIPayloadDTO`
  - Для `finalize`: `current_state=SCENARIO`, payload=None (⚠️ TODO: Scenario entry point)

---

#### `resume(char_id: int) -> CoreResponseDTO[OnboardingUIPayloadDTO]`
Восстанавливает сессию онбординга (для LoginGateway).

**Logic:**
1. Вызывает `OnboardingService.resume_session(char_id)`.
2. Service читает `ac:{char_id}.bio` и определяет текущий шаг:
   - Если `name` пустой или "Новый персонаж" → шаг NAME
   - Если `gender` пустой или "other" → шаг GENDER
   - Иначе → шаг CONFIRM
3. Возвращает `OnboardingUIPayloadDTO` для продолжения.

**Returns:**
- `CoreResponseDTO` с `current_state=ONBOARDING` и `OnboardingUIPayloadDTO`.
