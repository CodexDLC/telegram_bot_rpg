# tests/integration/test_navigation_flow.py
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Chat, Message, User

from apps.bot.handlers.callback.login.login_handler import start_logging_handler
from apps.bot.handlers.callback.login.logout import global_logout_handler
from apps.bot.resources.fsm_states import CharacterLobby, InGame
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.database.repositories.ORM.characters_repo_orm import CharactersRepoORM
from apps.common.schemas_dto import CharacterOnboardingUpdateDTO, CharacterShellCreateDTO, UserUpsertDTO

TEST_USER_ID = 555
TEST_CHAT_ID = 555
TEST_BOT_ID = 999


@pytest.fixture
def mock_bot():
    bot = AsyncMock()
    bot.id = TEST_BOT_ID
    bot.edit_message_text = AsyncMock()
    bot.delete_message = AsyncMock()
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def fsm_context():
    storage = MemoryStorage()
    key = StorageKey(bot_id=TEST_BOT_ID, chat_id=TEST_CHAT_ID, user_id=TEST_USER_ID)
    return FSMContext(storage=storage, key=key)


@pytest.fixture
def mock_message(mock_bot):
    msg = MagicMock(spec=Message)
    msg.from_user = User(
        id=TEST_USER_ID,
        is_bot=False,
        first_name="NavTester",
        username="nav_test",
        language_code="ru",
    )
    msg.chat = Chat(id=TEST_CHAT_ID, type="private")
    msg.text = "menu"
    msg.bot = mock_bot
    msg.message_id = 3000

    sent_msg = MagicMock(spec=Message)
    sent_msg.message_id = 3001
    sent_msg.chat = msg.chat

    msg.answer = AsyncMock(return_value=sent_msg)
    msg.edit_text = AsyncMock(return_value=sent_msg)
    msg.delete = AsyncMock()

    return msg


@pytest.fixture
def mock_callback(mock_bot, mock_message):
    call = MagicMock(spec=CallbackQuery)
    call.from_user = mock_message.from_user
    call.message = mock_message
    call.bot = mock_bot
    call.data = ""
    call.answer = AsyncMock()
    return call


@pytest.mark.asyncio
async def test_navigation_entry_exit(
    get_async_session, fsm_context, mock_bot, mock_message, mock_callback, app_container
):
    """
    Тест входа в режим навигации и выхода из него:
    1. Подготовка: Создание персонажа.
    2. Установка контекста FSM (как будто мы выбрали персонажа в лобби).
    3. Вход (Login).
    4. Проверка стейта InGame.exploration.
    5. Выход (Logout).
    6. Проверка сброса стейта.
    """

    # Имитация данных Middleware
    data = {
        "account_manager": app_container.account_manager,
    }
    await fsm_context.set_data(data)

    async with get_async_session() as session:
        # ==========================================
        # 0. ПОДГОТОВКА ДАННЫХ (ARRANGE)
        # ==========================================
        print("\n🏁 Шаг 0: Подготовка данных")

        # 1. Создаем юзера
        auth_client = app_container.get_auth_client(session)
        user_dto = UserUpsertDTO(
            telegram_id=TEST_USER_ID,
            first_name="NavTester",
            username="nav_test",
            last_name="Testov",
            language_code="ru",
            is_premium=False,
        )
        await auth_client.upsert_user(user_dto)

        # 2. Создаем персонажа
        char_repo = CharactersRepoORM(session)
        char_create_dto = CharacterShellCreateDTO(user_id=TEST_USER_ID)
        char_id = await char_repo.create_character_shell(char_create_dto)

        # ВАЖНО: Устанавливаем game_stage="in_game", чтобы LoginService пустил нас в игру
        char_update_dto = CharacterOnboardingUpdateDTO(name="Navigator", gender="male", game_stage="in_game")
        await char_repo.update_character_onboarding(char_id, char_update_dto)

        await session.commit()
        print(f"   -> Создан персонаж: {char_id} (Navigator)")

        # 3. Подготавливаем FSM (эмулируем, что персонаж уже выбран в лобби)
        # Нам нужно положить char_id в FSM_CONTEXT_KEY
        initial_context = {
            "user_id": TEST_USER_ID,
            "char_id": char_id,
            "message_menu": {"chat_id": TEST_CHAT_ID, "message_id": 3000},  # Эмуляция меню
            "message_content": {"chat_id": TEST_CHAT_ID, "message_id": 3001},  # Эмуляция контента
        }
        await fsm_context.update_data({FSM_CONTEXT_KEY: initial_context})

        # Устанавливаем начальный стейт (мы в лобби)
        await fsm_context.set_state(CharacterLobby.selection)

        # ==========================================
        # 1. ВХОД В ИГРУ (LOGIN)
        # ==========================================
        print("\n🏁 Шаг 1: Вход в игру (Login)")

        mock_callback.data = "lsc:login"
        # Создаем callback data объект, так как фильтр может его использовать,
        # но в самом хендлере он не передается аргументом, если не указан в сигнатуре.
        # В start_logging_handler аргументы: call, state, bot, session, container.

        await start_logging_handler(
            call=mock_callback, state=fsm_context, bot=mock_bot, session=session, container=app_container
        )

        # Проверяем стейт
        current_state = await fsm_context.get_state()
        assert current_state == InGame.exploration, f"Ожидался InGame.exploration, получен {current_state}"
        print("   -> Стейт успешно переключен на InGame.exploration.")

        # Проверяем, что бот попытался обновить интерфейс (меню или контент)
        # start_logging_handler вызывает orchestrator.handle_login, который возвращает DTO с меню/контентом.
        # Затем хендлер вызывает bot.edit_message_text.
        assert mock_bot.edit_message_text.called
        print("   -> Интерфейс обновлен (edit_message_text вызван).")

        # ==========================================
        # 2. ВЫХОД ИЗ ИГРЫ (LOGOUT)
        # ==========================================
        print("\n🏁 Шаг 2: Выход из игры (Logout)")

        mock_callback.data = "lsc:logout"

        await global_logout_handler(call=mock_callback, state=fsm_context, bot=mock_bot)

        # Проверяем сброс стейта
        current_state = await fsm_context.get_state()
        assert current_state is None, f"Ожидался сброс стейта (None), получен {current_state}"
        print("   -> Стейт успешно сброшен.")

        # Проверяем очистку char_id в FSM
        fsm_data = await fsm_context.get_data()
        session_ctx = fsm_data.get(FSM_CONTEXT_KEY, {})
        assert session_ctx.get("char_id") is None
        print("   -> char_id удален из контекста сессии.")

        print("✅ Тест навигации (вход/выход) успешно пройден.")
