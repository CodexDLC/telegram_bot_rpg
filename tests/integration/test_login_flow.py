# tests/integration/test_login_flow.py
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Chat, Message, User

from apps.bot.handlers.callback.login.lobby import start_login_handler
from apps.bot.handlers.callback.onboarding.onboarding_handler import (
    on_onboarding_action,
    on_text_input,
)

# Хендлеры
from apps.bot.handlers.commands import cmd_start

# Ресурсы
from apps.bot.resources.fsm_states import BotState
from apps.bot.resources.keyboards.callback_data import OnboardingCallback
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.database.repositories.ORM.characters_repo_orm import CharactersRepoORM

TEST_USER_ID = 777
TEST_CHAT_ID = 777
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
    msg = AsyncMock(spec=Message)
    msg.from_user = User(
        id=TEST_USER_ID,
        is_bot=False,
        first_name="Tester",
        username="test_user",
        language_code="ru",
    )
    msg.chat = Chat(id=TEST_CHAT_ID, type="private")
    msg.text = "/start"
    msg.bot = mock_bot
    msg.message_id = 1000

    sent_msg = MagicMock(spec=Message)
    sent_msg.message_id = 1001
    sent_msg.chat = msg.chat

    msg.answer = AsyncMock(return_value=sent_msg)
    msg.delete = AsyncMock()
    msg.edit_text = AsyncMock()
    return msg


@pytest.fixture
def mock_callback(mock_bot, mock_message):
    call = AsyncMock(spec=CallbackQuery)
    call.from_user = mock_message.from_user
    call.message = mock_message
    call.bot = mock_bot
    call.data = ""
    call.answer = AsyncMock()
    return call


@pytest.mark.asyncio
async def test_onboarding_flow(get_async_session, fsm_context, mock_bot, mock_message, mock_callback, app_container):
    """
    Тест процесса создания персонажа (Onboarding):
    1. /start
    2. Вход в создание (start_adventure) -> InGame.onboarding
    3. Выбор пола (set_gender)
    4. Ввод имени (set_name)
    5. Финализация (finalize)
    """

    # Имитация данных Middleware
    data = {
        "account_manager": app_container.account_manager,
    }
    await fsm_context.set_data(data)

    async with get_async_session() as session:
        # ==========================================
        # 0. ОЧИСТКА ДАННЫХ (CLEANUP)
        # ==========================================
        # Удаляем всех персонажей пользователя, чтобы тест начинался с чистого листа
        char_repo = CharactersRepoORM(session)
        chars = await char_repo.get_characters(TEST_USER_ID)
        for char in chars:
            await char_repo.delete_characters(char.character_id)
        await session.commit()

        # ==========================================
        # 1. СТАРТ (/start)
        # ==========================================
        print("\n🏁 Шаг 1: /start")
        # ИСПРАВЛЕНО: Передаем container
        await cmd_start(mock_message, fsm_context, mock_bot, session, app_container)

        fsm_data = await fsm_context.get_data()
        assert FSM_CONTEXT_KEY in fsm_data

        # ==========================================
        # 2. НАЧАЛО (Вход в Onboarding)
        # ==========================================
        print("\n🏁 Шаг 2: Начать приключение")
        mock_callback.data = "start_adventure"
        # ИСПРАВЛЕНО: Убран лишний аргумент account_manager
        await start_login_handler(mock_callback, fsm_context, mock_bot, session, app_container)

        # Проверяем переход в стейт onboarding
        assert await fsm_context.get_state() == BotState.onboarding

        # Проверяем создание временного ID персонажа
        fsm_data = await fsm_context.get_data()
        assert "char_id" in fsm_data

        # ==========================================
        # 3. ВЫБОР ПОЛА
        # ==========================================
        print("\n🏁 Шаг 3: Выбор пола")
        cb_gender = OnboardingCallback(action="set_gender", value="male")
        await on_onboarding_action(mock_callback, cb_gender, fsm_context, session, app_container)

        # Проверяем сохранение в FSM
        fsm_data = await fsm_context.get_data()
        assert fsm_data.get("gender") == "male"

        # ==========================================
        # 4. ВВОД ИМЕНИ
        # ==========================================
        print("\n🏁 Шаг 4: Ввод имени")
        mock_message.text = "TestHero"
        # ИСПРАВЛЕНО: Используем on_text_input вместо on_name_input
        await on_text_input(mock_message, fsm_context, mock_bot, session, app_container)

        # Проверяем сохранение в FSM
        fsm_data = await fsm_context.get_data()
        assert fsm_data.get("name") == "TestHero"

        # ==========================================
        # 5. ФИНАЛИЗАЦИЯ
        # ==========================================
        print("\n🏁 Шаг 5: Финализация")
        cb_finalize = OnboardingCallback(action="finalize", value="confirm")
        await on_onboarding_action(mock_callback, cb_finalize, fsm_context, session, app_container)

        # Проверяем, что бот попытался отредактировать сообщение (показать финальный экран)
        # Это означает, что оркестратор отработал и вернул ViewDTO
        assert mock_callback.message.edit_text.called

        print("✅ Тест онбординга успешно пройден.")
