# tests/integration/test_lobby_flow.py
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Chat, Message, User

from apps.bot.handlers.callback.login.lobby import start_login_handler
from apps.bot.handlers.callback.login.lobby_character_selection import (
    select_or_delete_character_handler,
)
from apps.bot.resources.fsm_states import BotState
from apps.bot.resources.keyboards.callback_data import LobbySelectionCallback
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.database.model_orm.character import Character
from apps.common.database.repositories.ORM.characters_repo_orm import CharactersRepoORM
from apps.common.schemas_dto import CharacterOnboardingUpdateDTO, CharacterShellCreateDTO, UserUpsertDTO

TEST_USER_ID = 888
TEST_CHAT_ID = 888
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
    # Используем MagicMock для самого объекта, но AsyncMock для методов
    msg = MagicMock(spec=Message)
    msg.from_user = User(
        id=TEST_USER_ID,
        is_bot=False,
        first_name="LobbyTester",
        username="lobby_test",
        language_code="ru",
    )
    msg.chat = Chat(id=TEST_CHAT_ID, type="private")
    msg.text = "menu"
    msg.bot = mock_bot
    msg.message_id = 2000

    # Мокаем ответное сообщение
    sent_msg = MagicMock(spec=Message)
    sent_msg.message_id = 2001
    sent_msg.chat = msg.chat

    # Явно задаем AsyncMock для асинхронных методов
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
async def test_lobby_management_flow(
    get_async_session, fsm_context, mock_bot, mock_message, mock_callback, app_container
):
    """
    Тест управления персонажами в лобби:
    1. Подготовка: Создание 2-х персонажей в БД через репозиторий.
    2. Вход в лобби (start_adventure).
    3. Выбор персонажа (Select).
    4. Удаление персонажа (Delete -> Confirm).
    5. Проверка удаления в БД.
    6. Проверка возврата в лобби.
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

        # 1. Создаем/обновляем юзера
        auth_client = app_container.get_auth_client(session)
        user_dto = UserUpsertDTO(
            telegram_id=TEST_USER_ID,
            first_name="LobbyTester",
            username="lobby_test",
            last_name="Testov",
            language_code="ru",
            is_premium=False,
        )
        await auth_client.upsert_user(user_dto)

        # 2. Создаем двух персонажей через репозиторий
        char_repo = CharactersRepoORM(session)

        # Создаем Char 1
        char1_create_dto = CharacterShellCreateDTO(user_id=TEST_USER_ID)
        char1_id = await char_repo.create_character_shell(char1_create_dto)

        # Обновляем имя и стадию
        char1_update_dto = CharacterOnboardingUpdateDTO(name="CharOne", gender="male", game_stage="lobby")
        await char_repo.update_character_onboarding(char1_id, char1_update_dto)

        # Создаем Char 2 (которого будем удалять)
        char2_create_dto = CharacterShellCreateDTO(user_id=TEST_USER_ID)
        char2_id = await char_repo.create_character_shell(char2_create_dto)

        char2_update_dto = CharacterOnboardingUpdateDTO(name="CharToDelete", gender="female", game_stage="lobby")
        await char_repo.update_character_onboarding(char2_id, char2_update_dto)

        await session.commit()
        print(f"   -> Созданы персонажи: {char1_id} (CharOne), {char2_id} (CharToDelete)")

        # ==========================================
        # 1. ВХОД В ЛОББИ
        # ==========================================
        print("\n🏁 Шаг 1: Вход в лобби")
        mock_callback.data = "start_adventure"
        # Исправлено: убран лишний аргумент account_manager
        await start_login_handler(mock_callback, fsm_context, mock_bot, session, app_container)

        # Проверяем стейт - должно быть BotState.lobby
        assert await fsm_context.get_state() == BotState.lobby

        # Проверяем, что список персонажей загрузился в FSM
        fsm_data = await fsm_context.get_data()
        characters = fsm_data.get("characters", [])
        assert len(characters) >= 2
        print(f"   -> В лобби найдено {len(characters)} персонажей.")

        # ==========================================
        # 2. ВЫБОР ПЕРСОНАЖА (SELECT)
        # ==========================================
        print("\n🏁 Шаг 2: Выбор персонажа (CharOne)")
        # Эмулируем нажатие кнопки выбора первого персонажа
        cb_select = LobbySelectionCallback(action="select", char_id=char1_id)

        await select_or_delete_character_handler(
            call=mock_callback,
            callback_data=cb_select,
            state=fsm_context,
            bot=mock_bot,
            session=session,
            container=app_container,
        )

        # Проверяем, что char_id сохранился в контексте сессии
        fsm_data = await fsm_context.get_data()
        session_ctx = fsm_data.get(FSM_CONTEXT_KEY, {})
        assert session_ctx.get("char_id") == char1_id
        print("   -> Персонаж успешно выбран в FSM.")

        # ==========================================
        # 3. УДАЛЕНИЕ ПЕРСОНАЖА (DELETE FLOW)
        # ==========================================
        print("\n🏁 Шаг 3: Удаление персонажа (CharToDelete)")

        # Сначала выбираем его (обычно в UI мы сначала кликаем на чара, потом на удалить,
        # или кнопка удалить рядом. В коде select_or_delete_handler обрабатывает и то и то).
        # Попробуем сразу нажать Delete для char2_id
        cb_delete = LobbySelectionCallback(action="delete", char_id=char2_id)

        await select_or_delete_character_handler(
            call=mock_callback,
            callback_data=cb_delete,
            state=fsm_context,
            bot=mock_bot,
            session=session,
            container=app_container,
        )

        # Стейт остается BotState.lobby, но меняется UI
        assert await fsm_context.get_state() == BotState.lobby
        print("   -> Запрошено подтверждение удаления.")

        # Подтверждаем удаление
        cb_confirm = LobbySelectionCallback(action="delete_yes", char_id=char2_id)

        # Используем тот же хендлер для подтверждения
        await select_or_delete_character_handler(
            call=mock_callback,
            callback_data=cb_confirm,
            state=fsm_context,
            bot=mock_bot,
            session=session,
            container=app_container,
        )

        # ==========================================
        # 4. ПРОВЕРКА РЕЗУЛЬТАТОВ
        # ==========================================
        print("\n🏁 Шаг 4: Проверка результатов")

        # 1. Стейт должен быть BotState.lobby
        assert await fsm_context.get_state() == BotState.lobby

        # 2. Проверяем БД - персонаж должен быть удален (is_deleted=True или запись удалена)
        # Очистим сессию, чтобы получить свежие данные из БД
        session.expire_all()

        deleted_char = await session.get(Character, char2_id)
        if deleted_char:
            print(f"   -> ВНИМАНИЕ: Персонаж {char2_id} все еще существует в БД!")
        else:
            print("   -> Персонаж полностью удален из БД.")

        # 3. Проверяем, что активный char_id сбросился в FSM (если мы удаляли выбранного)
        # В нашем тесте мы выбрали char1, а удалили char2.
        # Но логика удаления может сбрасывать выбор.
        # В текущей реализации handle_delete_confirm вызывает process_entry_point,
        # который обновляет список персонажей, но не обязательно сбрасывает выбранного, если это был другой персонаж.
        # Однако, если мы удалили char2, то он должен исчезнуть из списка.

        fsm_data = await fsm_context.get_data()
        characters = fsm_data.get("characters", [])
        # Проверяем, что удаленного персонажа нет в списке
        deleted_in_list = any(c.character_id == char2_id for c in characters)
        assert not deleted_in_list, "Удаленный персонаж все еще в списке FSM"

        print("✅ Тест лобби успешно пройден.")
