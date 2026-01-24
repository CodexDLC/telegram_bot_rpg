# Account Domain - Client Interface

## Overview

Описание интеграции Account Domain с Telegram Bot клиентом.

---

## AccountClient (HTTP Client)

**File:** `game_client/telegram_bot/features/account/client.py`

### Class Schema

```python
class AccountClient:
    """HTTP клиент для взаимодействия с Account Domain API."""

    def __init__(self, base_url: str):
        # httpx.AsyncClient для HTTP запросов

    # Registration
    async def register_user(
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str | None = "ru",
        is_premium: bool = False
    ) -> None:
        # POST /account/register

    # Lobby - List
    async def list_characters(user_id: int) -> CoreResponseDTO[LobbyListDTO]:
        # GET /account/lobby/{user_id}/characters

    # Lobby - Create
    async def create_character(
        user_id: int,
        name: str,
        gender: str
    ) -> CoreResponseDTO[CharacterShellDTO]:
        # POST /account/lobby/{user_id}/characters

    # Lobby - Delete
    async def delete_character(
        char_id: int,
        user_id: int
    ) -> CoreResponseDTO[dict[str, bool]]:
        # DELETE /account/lobby/characters/{char_id}?user_id={user_id}

    # Login (FUTURE)
    # async def login(char_id: int) -> CoreResponseDTO:
    #     # POST /account/login
```

### Responsibilities
- HTTP запросы к Account API
- Сериализация/десериализация JSON
- Обработка HTTP ошибок (4xx, 5xx)
- Валидация ответов (CoreResponseDTO parsing)

---

## Bot Orchestrators

### StartBotOrchestrator

**File:** `game_client/telegram_bot/features/commands/orchestrators/start_bot_orchestrator.py`

```python
class StartBotOrchestrator:
    def __init__(
        self,
        account_client: AccountClient,
        user: TelegramUser
    ):
        pass

    async def handle_start(self) -> UnifiedViewDTO:
        # 1. Register/Update user
        await self.account_client.register_user(
            telegram_id=self.user.id,
            username=self.user.username,
            first_name=self.user.first_name,
            last_name=self.user.last_name,
            language_code=self.user.language_code,
            is_premium=self.user.is_premium
        )

        # 2. Render Start Menu (UI)
        return await self.render_start_menu(self.user.first_name)
```

**Responsibilities:**
- Вызов `register_user()` при `/start`
- Рендеринг приветственного меню
- НЕ работает напрямую с БД (только через HTTP API)

---

### LobbyBotOrchestrator

**File:** `game_client/telegram_bot/features/lobby/orchestrators/lobby_bot_orchestrator.py`

```python
class LobbyBotOrchestrator:
    def __init__(
        self,
        account_client: AccountClient,
        user: TelegramUser
    ):
        pass

    async def show_lobby(self) -> UnifiedViewDTO:
        # 1. Получить список персонажей
        response = await self.account_client.list_characters(self.user.id)

        # 2. Рендерить UI (сетка 2x2 с персонажами)
        return await self.render_lobby(response.payload.characters)

    async def handle_create_character(
        self,
        name: str,
        gender: str
    ) -> UnifiedViewDTO:
        # 1. Создать Character Shell
        response = await self.account_client.create_character(
            user_id=self.user.id,
            name=name,
            gender=gender
        )

        # 2. Redirect to Onboarding
        return await self.redirect_to_onboarding(response.payload.character_id)

    async def handle_delete_character(self, char_id: int) -> UnifiedViewDTO:
        # 1. Удалить персонажа
        await self.account_client.delete_character(
            char_id=char_id,
            user_id=self.user.id
        )

        # 2. Refresh lobby
        return await self.show_lobby()

    # FUTURE - Login
    # async def handle_character_selection(self, char_id: int) -> UnifiedViewDTO:
    #     # 1. Login (Resume Session)
    #     response = await self.account_client.login(char_id)
    #
    #     # 2. Redirect to domain (Combat, Exploration, etc.)
    #     return await self.redirect_to_domain(response)
```

**Responsibilities:**
- Отображение списка персонажей (Lobby UI)
- Создание Character Shell (имя + пол)
- Удаление персонажей (с подтверждением)
- Redirect в Onboarding после создания
- НЕ работает напрямую с БД (только через HTTP API)

---

## Bot Handlers

### Command Handlers

**File:** `game_client/telegram_bot/features/commands/handlers/router.py`

```python
@router.message(Command("start"))
async def handle_start_command(message: Message, state: FSMContext):
    # 1. Создать StartBotOrchestrator
    orchestrator = StartBotOrchestrator(
        account_client=get_account_client(),
        user=message.from_user
    )

    # 2. Handle /start
    view = await orchestrator.handle_start()

    # 3. Render UI
    await message.answer(
        text=view.text,
        reply_markup=view.keyboard
    )
```

---

### Lobby Callback Handlers

**File:** `game_client/telegram_bot/features/lobby/handlers/router.py`

```python
@router.callback_query(F.data == "lobby:create_character")
async def handle_create_character_callback(
    callback: CallbackQuery,
    state: FSMContext
):
    # 1. Перевод в FSM state "waiting_for_name"
    await state.set_state(LobbyStates.waiting_for_name)

    # 2. Запрос имени
    await callback.message.answer("Введите имя персонажа:")

@router.message(LobbyStates.waiting_for_name)
async def handle_name_input(message: Message, state: FSMContext):
    # 1. Сохранить имя в FSM data
    await state.update_data(name=message.text)

    # 2. Запрос пола
    await state.set_state(LobbyStates.waiting_for_gender)
    await message.answer("Выберите пол:", reply_markup=gender_keyboard)

@router.callback_query(LobbyStates.waiting_for_gender)
async def handle_gender_callback(
    callback: CallbackQuery,
    state: FSMContext
):
    # 1. Получить данные из FSM
    data = await state.get_data()
    gender = callback.data.split(":")[1]  # "gender:male"

    # 2. Создать персонажа
    orchestrator = LobbyBotOrchestrator(...)
    view = await orchestrator.handle_create_character(
        name=data["name"],
        gender=gender
    )

    # 3. Clear FSM state
    await state.clear()

    # 4. Render UI (redirect to Onboarding)
    await callback.message.edit_text(
        text=view.text,
        reply_markup=view.keyboard
    )
```

---

## FSM States

**File:** `game_client/telegram_bot/common/resources/states.py`

```python
class LobbyStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_gender = State()
```

---

## UI Rendering

### UnifiedViewDTO

```python
class UnifiedViewDTO(BaseModel):
    text: str                    # Текст сообщения
    keyboard: InlineKeyboardMarkup | ReplyKeyboardMarkup | None
    media: str | None = None     # Опционально: фото, видео
```

### Lobby UI Example

```python
async def render_lobby(characters: list[CharacterReadDTO]) -> UnifiedViewDTO:
    # Сетка 2x2 с персонажами + кнопка "Создать"
    text = "📋 Ваши персонажи:\n\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"{char.name} (❤️ {char.hp})",
                callback_data=f"lobby:select:{char.character_id}"
            )
        ]
        for char in characters
    ] + [
        [InlineKeyboardButton(text="➕ Создать персонажа", callback_data="lobby:create_character")]
    ])

    return UnifiedViewDTO(text=text, keyboard=keyboard)
```

---

## Integration Flow

### Registration Flow (`/start`)

```
User → /start → StartBotOrchestrator → AccountClient.register_user()
                                               ↓
                                        POST /account/register
                                               ↓
                                        RegistrationGateway
                                               ↓
                                        UsersRepoORM.upsert_user()
                                               ↓
                                        PostgreSQL INSERT/UPDATE
```

### Lobby List Flow

```
User → Lobby Menu → LobbyBotOrchestrator → AccountClient.list_characters()
                                                   ↓
                                            GET /account/lobby/{user_id}/characters
                                                   ↓
                                            LobbyGateway.list_characters()
                                                   ↓
                                            LobbyService.get_characters_list()
                                              (Cache-Aside: Redis → PostgreSQL)
                                                   ↓
                                            Render Lobby UI (сетка 2x2)
```

### Create Character Flow

```
User → "Создать" → FSM (name, gender) → LobbyBotOrchestrator.handle_create_character()
                                                   ↓
                                        AccountClient.create_character()
                                                   ↓
                                        POST /account/lobby/{user_id}/characters
                                                   ↓
                                        LobbyGateway.create_character()
                                                   ↓
                                        LobbyService.create_character_shell()
                                          (INSERT + cache invalidation)
                                                   ↓
                                        Redirect to Onboarding (char_id)
```

---

## Error Handling

### HTTP Errors

```python
async def list_characters(user_id: int) -> CoreResponseDTO[LobbyListDTO]:
    try:
        response = await self.http_client.get(...)
        response.raise_for_status()
        return CoreResponseDTO(**response.json())
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            # Handle not found
            raise CharacterNotFoundError()
        elif e.response.status_code == 500:
            # Handle server error
            raise BackendError("Server error occurred")
        else:
            raise
```

### User-Friendly Messages

```python
try:
    await orchestrator.handle_delete_character(char_id)
except CharacterNotFoundError:
    await callback.answer("Персонаж не найден", show_alert=True)
except NotOwnerError:
    await callback.answer("Это не ваш персонаж", show_alert=True)
except BackendError:
    await callback.answer("Ошибка сервера. Попробуйте позже", show_alert=True)
```

---

## Testing

### Unit Tests
- AccountClient методы (mocked httpx)
- Orchestrators (mocked AccountClient)

### Integration Tests
- Bot handlers → Orchestrators → AccountClient → Backend API

### E2E Tests
- Full flow: User interaction → Backend → Database

---

## Migration Notes

### Legacy Code Removal

**Удалить:**
- `game_client.bot.ui_service.auth.auth_bot_orchestrator.py` (прямой доступ к БД)
- `game_client.bot.core_client.auth_client.py` (legacy Auth Client)

**Заменить на:**
- `game_client/telegram_bot/features/account/client.py` (AccountClient)
- HTTP запросы вместо прямого доступа к БД

---

## См. также

- [API/README.md](../API/README.md) - API endpoints specification
- [Gateway/README.md](../Gateway/README.md) - Gateway Layer
- [Roadmap/README.md](../Roadmap/README.md) - Phase 3: Bot Client Migration
