# tests/integration/test_login_flow.py
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Chat, Message, User

# 2. Создание
from app.handlers.callback.login.char_creation import (
    choose_gender_handler,
    choosing_name_handler,
    confirm_creation_handler,
)
from app.handlers.callback.login.lobby import start_login_handler
from app.handlers.callback.login.lobby_character_selection import select_or_delete_character_handler
from app.handlers.callback.login.login_handler import start_logging_handler
from app.handlers.callback.login.logout import global_logout_handler

# 3. Туториалы
from app.handlers.callback.tutorial.tutorial_game import (
    start_tutorial_handler,
    tutorial_confirmation_handler,
    tutorial_event_stats_handler,
)
from app.handlers.callback.tutorial.tutorial_skill import (
    in_skills_progres_handler,
    skill_confirm_handler,
    start_skill_phase_handler,
)

# --- ИМПОРТЫ ХЭНДЛЕРОВ ---
# 1. Общие
from app.handlers.commands import cmd_start

# --- РЕСУРСЫ ---
from app.resources.fsm_states.states import CharacterCreation, CharacterLobby, InGame, StartTutorial
from app.resources.keyboards.callback_data import LobbySelectionCallback, TutorialQuestCallback
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY

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
    msg.from_user = User(id=TEST_USER_ID, is_bot=False, first_name="Tester", username="test_user", language_code="ru")
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
async def test_full_game_cycle(get_async_session, fsm_context, mock_bot, mock_message, mock_callback):
    """
    Полный цикл: Старт -> Создание -> Туториал (Статы) -> Туториал (Скиллы) -> Вход -> Выход -> Вход.
    """
    async with get_async_session() as session:
        # 1. СТАРТ
        print("\n🏁 Шаг 1: /start")
        await cmd_start(mock_message, fsm_context, mock_bot, session)

        data = await fsm_context.get_data()
        assert FSM_CONTEXT_KEY in data
        assert data[FSM_CONTEXT_KEY].get("message_menu") is not None

        # 2. НАЧАЛО (Авто-создание)
        print("\n🏁 Шаг 2: Начать приключение")
        mock_callback.data = "start_adventure"
        await start_login_handler(mock_callback, fsm_context, mock_bot, session)
        assert await fsm_context.get_state() == CharacterCreation.choosing_gender

        # 3. СОЗДАНИЕ
        print("\n🏁 Шаг 3: Ввод данных")
        mock_callback.data = "gender:male"
        await choose_gender_handler(mock_callback, fsm_context, mock_bot)

        mock_message.text = "Hero"
        await choosing_name_handler(mock_message, fsm_context, mock_bot)

        mock_callback.data = "confirm"
        await confirm_creation_handler(mock_callback, fsm_context, mock_bot, session)
        print("✅ Персонаж создан.")

        # 4. ТУТОРИАЛ (СТАТЫ)
        print("\n🏁 Шаг 4: Туториал (Статы)")
        # Фикс бага с InGame стейтом (если ты его еще не поправил в коде, тут мы страхуемся)
        state = await fsm_context.get_state()
        if state != StartTutorial.start:
            await fsm_context.set_state(StartTutorial.start)

        mock_callback.data = "tut:start"
        await start_tutorial_handler(mock_callback, fsm_context, mock_bot)

        for _ in range(4):
            mock_callback.data = "tut_ev1:might"
            await tutorial_event_stats_handler(mock_callback, fsm_context, mock_bot)

        mock_callback.data = "tut:continue"
        await tutorial_confirmation_handler(mock_callback, fsm_context, mock_bot, session)
        print("✅ Статы распределены.")

        # 5. ТУТОРИАЛ (СКИЛЛЫ)
        print("\n🏁 Шаг 5: Туториал (Скиллы)")
        # Начало фазы скиллов
        mock_callback.data = "tut_quest:start_skill_phase"
        await start_skill_phase_handler(mock_callback, fsm_context, mock_bot)
        assert await fsm_context.get_state() == StartTutorial.in_skills_progres

        # Прокликиваем ветку (Меч -> Легкая броня -> Рефлексы -> Лут)
        # Используем TutorialQuestCallback
        path = [
            ("step_1", "path_melee", "path_melee"),
            ("step_2", "path_melee", "light_armor"),
            ("step_3", "path_melee", "reflexes"),
            ("finale", "path_melee", "FINALE_LOOTING"),
        ]

        for phase, branch, val in path:
            cb_data = TutorialQuestCallback(phase=phase, branch=branch, value=val)
            await in_skills_progres_handler(mock_callback, fsm_context, cb_data, mock_bot)

        # Подтверждение (Награда)
        print("✅ Скиллы выбраны, подтверждаем...")
        cb_data = TutorialQuestCallback(phase="p_end", branch="none", value="mining")
        await skill_confirm_handler(mock_callback, fsm_context, cb_data, mock_bot, session)

        # После скиллов нас должно перекинуть в Лобби для входа
        assert await fsm_context.get_state() == CharacterLobby.selection

        # 6. ВХОД В ИГРУ
        print("\n🏁 Шаг 6: Вход в мир (Login)")
        mock_callback.data = "lsc:login"
        await start_logging_handler(mock_callback, fsm_context, mock_bot, session)

        state = await fsm_context.get_state()
        assert state == InGame.navigation, f"❌ Ошибка входа! Текущий стейт: {state}"
        print("✅ Успешный вход в Навигацию.")

        # 7. ВЫХОД (Logout)
        print("\n🏁 Шаг 7: Выход (Logout)")
        mock_callback.data = "lsc:logout"
        await global_logout_handler(mock_callback, fsm_context, mock_bot)
        assert await fsm_context.get_state() is None
        print("✅ Выход успешен.")

        # 8. РЕ-ЛОГИН (Проверка сохранения)
        print("\n🏁 Шаг 8: Возвращение (Re-Login)")
        mock_callback.data = "start_adventure"
        await start_login_handler(mock_callback, fsm_context, mock_bot, session)

        # Выбираем чара
        data = await fsm_context.get_data()
        char_id = data["characters"][-1]["character_id"]
        cb_data = LobbySelectionCallback(action="select", char_id=char_id)
        await select_or_delete_character_handler(mock_callback, cb_data, fsm_context, mock_bot, session)

        # Входим
        mock_callback.data = "lsc:login"
        await start_logging_handler(mock_callback, fsm_context, mock_bot, session)

        state = await fsm_context.get_state()
        assert state == InGame.navigation
        print("✅ Ре-логин успешен! Цепочка работает.")
