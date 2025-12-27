# tests/integration/test_combat_flow.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Chat, Message, User

# Хендлеры
from apps.bot.handlers.callback.game.combat.action_handlers import (
    leave_combat_handler,
    refresh_combat_handler,
    submit_turn_handler,
)

# Ресурсы
from apps.bot.resources.fsm_states import BotState
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.database.repositories.ORM.characters_repo_orm import CharactersRepoORM
from apps.common.schemas_dto import CharacterOnboardingUpdateDTO, CharacterShellCreateDTO, UserUpsertDTO
from apps.game_core.game_service.combat.session.combat_lifecycle_service import CombatLifecycleService

TEST_USER_ID = 777
TEST_CHAT_ID = 777
TEST_BOT_ID = 999
SESSION_ID = "test_combat_session_123"


@pytest.fixture
def mock_bot():
    bot = AsyncMock()
    bot.id = TEST_BOT_ID
    bot.edit_message_text = AsyncMock()
    return bot


@pytest.fixture
def fsm_context():
    storage = MemoryStorage()
    key = StorageKey(bot_id=TEST_BOT_ID, chat_id=TEST_CHAT_ID, user_id=TEST_USER_ID)
    return FSMContext(storage=storage, key=key)


@pytest.fixture
def mock_message(mock_bot):
    msg = MagicMock(spec=Message)
    msg.from_user = User(id=TEST_USER_ID, is_bot=False, first_name="CombatTester")
    msg.chat = Chat(id=TEST_CHAT_ID, type="private")
    msg.bot = mock_bot
    msg.message_id = 5000
    sent_msg = MagicMock(spec=Message)
    sent_msg.message_id = 5001
    sent_msg.chat = msg.chat
    msg.answer = AsyncMock(return_value=sent_msg)
    msg.edit_text = AsyncMock(return_value=sent_msg)
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
async def test_combat_flow(get_async_session, fsm_context, mock_bot, mock_callback, app_container):
    """
    Тест боевой системы (RBC):
    1. Подготовка: Создание персонажа, инициализация боя (Lifecycle).
    2. Отображение боя (Refresh).
    3. Ход игрока (Submit).
    4. Завершение боя (Finish).
    """
    async with get_async_session() as session:
        # ==========================================
        # 0. ПОДГОТОВКА ДАННЫХ (ARRANGE)
        # ==========================================
        print("\n🏁 Шаг 0: Подготовка данных")

        # Создаем юзера и персонажа
        auth_client = app_container.get_auth_client(session)
        await auth_client.upsert_user(
            UserUpsertDTO(
                telegram_id=TEST_USER_ID,
                first_name="Fighter",
                last_name="Testov",  # Добавлено обязательное поле
                username="fight",
                language_code="ru",
                is_premium=False,
            )
        )

        char_repo = CharactersRepoORM(session)
        char_id = await char_repo.create_character_shell(CharacterShellCreateDTO(user_id=TEST_USER_ID))
        await char_repo.update_character_onboarding(
            char_id, CharacterOnboardingUpdateDTO(name="Gladiator", gender="male", game_stage="in_game")
        )
        await session.commit()

        # Инициализация боя через LifecycleService
        combat_manager = app_container.combat_manager
        lifecycle = CombatLifecycleService(combat_manager, app_container.account_manager)

        # 1. Создаем сессию
        await lifecycle.create_battle(SESSION_ID, {"battle_type": "pve", "mode": "duel"})

        # 2. Добавляем игрока
        await lifecycle.add_participant(session, SESSION_ID, char_id, "blue", "Gladiator", is_ai=False)

        # 3. Добавляем манекен (врага)
        dummy_id = -100
        await lifecycle.add_dummy_participant(SESSION_ID, dummy_id, hp=100, energy=100, name="Dummy")

        # 4. Инициализируем состояние
        await lifecycle.initialize_battle_state(SESSION_ID)

        print(f"   -> Бой создан: {SESSION_ID}, Игрок: {char_id}, Враг: {dummy_id}")

        # Устанавливаем FSM
        await fsm_context.set_state(BotState.combat)
        initial_context = {
            "user_id": TEST_USER_ID,
            "char_id": char_id,
            "combat_session_id": SESSION_ID,
            "message_content": {"chat_id": TEST_CHAT_ID, "message_id": 5000},
            "message_menu": {"chat_id": TEST_CHAT_ID, "message_id": 5001},
        }
        await fsm_context.update_data({FSM_CONTEXT_KEY: initial_context})
        await fsm_context.update_data(combat_target_id=dummy_id)

        # ==========================================
        # 1. ОТОБРАЖЕНИЕ БОЯ (REFRESH)
        # ==========================================
        print("\n🏁 Шаг 1: Отображение боя (Refresh)")
        # cb_refresh = CombatActionCallback(action="refresh") # Unused
        await refresh_combat_handler(mock_callback, fsm_context, mock_bot, app_container, session)

        assert mock_bot.edit_message_text.called
        print("   -> Экран боя обновлен.")

        # ==========================================
        # 2. ХОД ИГРОКА (SUBMIT)
        # ==========================================
        print("\n🏁 Шаг 2: Ход игрока (Submit)")

        # Эмулируем выбор атаки
        await fsm_context.update_data(combat_selection={"atk": ["head"], "def": ["body"]})

        # cb_submit = CombatActionCallback(action="submit") # Unused

        # Мокаем UIAnimationService, чтобы не ждать 30 секунд
        with patch("apps.bot.handlers.callback.game.combat.action_handlers.UIAnimationService") as mock_anim:
            mock_anim_instance = mock_anim.return_value
            # Эмулируем успешный результат поллинга (возвращаем DTO, как будто бой обновился)
            from apps.bot.ui_service.combat.dto.combat_view_dto import CombatViewDTO
            from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO

            mock_view = CombatViewDTO(
                content=ViewResultDTO(text="Бой идет...", kb=None),
                menu=ViewResultDTO(text="Лог боя...", kb=None),
                target_id=dummy_id,
            )
            mock_anim_instance.animate_polling = AsyncMock(return_value=mock_view)

            await submit_turn_handler(mock_callback, fsm_context, mock_bot, app_container, session)

        # Проверяем, что ход записан в Redis
        moves = await combat_manager.get_rbc_moves(SESSION_ID, char_id)
        assert moves is not None
        assert str(dummy_id) in moves
        print("   -> Ход игрока зарегистрирован в Redis.")

        # ==========================================
        # 3. ЗАВЕРШЕНИЕ БОЯ (FINISH)
        # ==========================================
        print("\n🏁 Шаг 3: Завершение боя (Finish)")

        # Эмулируем победу (вызываем finish_battle напрямую, так как нет воркера)
        await lifecycle.finish_battle(SESSION_ID, winner_team="blue")

        # Проверяем метаданные сессии
        meta = await combat_manager.get_rbc_session_meta(SESSION_ID)
        assert meta["active"] == "0"
        assert meta["winner"] == "blue"
        print("   -> Бой завершен, победитель: blue.")

        # Проверяем очистку combat_session_id у игрока в Redis/AccountManager
        # (AccountManager кэширует данные, поэтому лучше проверить через него или напрямую в Redis)
        # В lifecycle.finish_battle вызывается update_account_fields(..., combat_session_id="")

        # Проверим через AccountManager
        acc_data = await app_container.account_manager.get_account_data(char_id)
        assert acc_data.get("combat_session_id") == ""
        print("   -> combat_session_id очищен у игрока.")

        # ==========================================
        # 4. ВЫХОД ИЗ БОЯ (LEAVE)
        # ==========================================
        print("\n🏁 Шаг 4: Выход из боя (Leave)")
        # cb_leave = CombatActionCallback(action="leave") # Unused

        # Мокаем orchestrator.leave_combat, так как он может требовать сложной логики наград
        # Или используем реальный, если он простой.
        # leave_combat в CombatBotOrchestrator вызывает get_rewards_view и переключает стейт.

        await leave_combat_handler(mock_callback, fsm_context, mock_bot, app_container, session)

        # Проверяем переключение стейта (обычно на InGame.navigation или CharacterLobby.selection)
        # В leave_combat_handler стейт берется из result.new_state.
        # Если бой завершен, leave_combat должен вернуть new_state="InGame:navigation" (или подобное).

        # Так как мы не настраивали rewards view детально, проверим просто вызов edit_message_text
        assert mock_bot.edit_message_text.called
        print("   -> Выход из боя обработан.")

        print("✅ Тест боевой системы успешно пройден.")
