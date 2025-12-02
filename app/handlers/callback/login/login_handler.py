import asyncio
from typing import Any

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.callback.login.char_creation import start_creation_handler
from app.resources.fsm_states.states import InGame, StartTutorial
from app.resources.keyboards.callback_data import LobbySelectionCallback
from app.resources.schemas_dto.fsm_state_dto import SessionDataDTO
from app.resources.texts.buttons_callback import GameStage
from app.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from app.services.core_service.manager.account_manager import account_manager
from app.services.game_service.game_sync_service import GameSyncService
from app.services.game_service.login_service import LoginService
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY, fsm_clean_core_state
from app.services.ui_service.combat.combat_ui_service import CombatUIService
from app.services.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from app.services.ui_service.menu_service import MenuService
from app.services.ui_service.navigation_service import NavigationService
from app.services.ui_service.tutorial.tutorial_service import TutorialServiceStats
from app.services.ui_service.tutorial.tutorial_service_skill import TutorialServiceSkills
from database.repositories import get_character_repo, get_symbiote_repo

router = Router(name="login_handler_router")


async def _fetch_character_display_data(session: AsyncSession, char_id: int) -> tuple[str, str]:
    """Извлекает имя персонажа и имя Симбиота из БД."""
    char_repo = get_character_repo(session)
    sym_repo = get_symbiote_repo(session)
    character = await char_repo.get_character(char_id)
    char_name = character.name if character else "Прошедший"
    symbiote = await sym_repo.get_symbiote(char_id)
    sym_name = symbiote.symbiote_name if symbiote else DEFAULT_ACTOR_NAME
    return char_name, sym_name


async def _handle_tutorial_stats(char_id: int, state: FSMContext, bot: Bot, message_content: dict) -> None:
    """Переводит пользователя в туториал по распределению статов."""
    log.debug(f"Redirect | stage=tutorial_stats char_id={char_id}")
    tut_stats_service = TutorialServiceStats(char_id=char_id)
    text, kb = tut_stats_service.get_restart_stats()

    await bot.edit_message_text(
        chat_id=message_content["chat_id"],
        message_id=message_content["message_id"],
        text=text,
        reply_markup=kb,
        parse_mode="HTML",
    )

    await state.set_state(StartTutorial.start)
    await state.update_data(bonus_dict={}, event_pool=None, sim_text_count=0)
    log.info(f"FSM | state=StartTutorial.start char_id={char_id}")


async def _handle_tutorial_skills(char_id: int, state: FSMContext, bot: Bot, message_content: dict) -> None:
    """Переводит пользователя в туториал по выбору умений."""
    log.debug(f"Redirect | stage=tutorial_skills char_id={char_id}")
    skill_choices_list: list[str] = []
    tut_skill_service = TutorialServiceSkills(skills_db=skill_choices_list)
    text_skill, kb_skill = tut_skill_service.get_start_data()

    if text_skill and kb_skill:
        await bot.edit_message_text(
            chat_id=message_content["chat_id"],
            message_id=message_content["message_id"],
            text=text_skill,
            reply_markup=kb_skill,
            parse_mode="HTML",
        )
        await state.set_state(StartTutorial.in_skills_progres)
        await state.update_data(skill_choices_list=skill_choices_list)
        log.info(f"FSM | state=StartTutorial.in_skills_progres char_id={char_id}")
    else:
        log.error(f"Redirect | status=failed reason='Failed to get skill data' char_id={char_id}")


async def _handle_combat_restore(
    user_id: int,
    char_id: int,
    state: FSMContext,
    bot: Bot,
    state_data: dict,
    session_context: dict,
    call: CallbackQuery,
) -> None:
    """Восстанавливает и отображает интерфейс боя."""
    log.debug(f"SessionRestore | type=combat user_id={user_id} char_id={char_id}")
    ac_data = await account_manager.get_account_data(char_id)
    if not ac_data:
        log.warning(f"SessionRestore | status=failed reason='Account data not found' char_id={char_id}")
        await Err.generic_error(call)
        return

    combat_session_id = ac_data.get("combat_session_id")
    if not combat_session_id:
        log.warning(f"SessionRestore | status=failed reason='combat_session_id not found' char_id={char_id}")
        await Err.generic_error(call)
        return

    session_context["combat_session_id"] = combat_session_id
    await state.update_data({FSM_CONTEXT_KEY: session_context})
    log.debug(f"FSM | data_updated key=combat_session_id value={combat_session_id} char_id={char_id}")

    combat_ui = CombatUIService(user_id, char_id, str(combat_session_id), state_data)
    log_text, log_kb = await combat_ui.render_combat_log(page=0)
    dash_text, dash_kb = await combat_ui.render_dashboard(current_selection={})

    msg_menu = session_context.get("message_menu")
    msg_content = session_context.get("message_content")

    if isinstance(msg_menu, dict):
        await bot.edit_message_text(
            chat_id=msg_menu["chat_id"],
            message_id=msg_menu["message_id"],
            text=log_text,
            reply_markup=log_kb,
            parse_mode="HTML",
        )
    if isinstance(msg_content, dict):
        await bot.edit_message_text(
            chat_id=msg_content["chat_id"],
            message_id=msg_content["message_id"],
            text=dash_text,
            reply_markup=dash_kb,
            parse_mode="HTML",
        )

    await fsm_clean_core_state(state=state, event_source=call)
    await state.set_state(InGame.combat)
    log.info(f"FSM | state=InGame.combat char_id={char_id}")


async def _handle_in_game_login(
    user_id: int,
    char_id: int,
    state: FSMContext,
    bot: Bot,
    state_data: dict,
    session_context: dict,
    state_name: str,
    loc_id: str,
    call: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Обрабатывает вход в игру, отображая навигационный интерфейс и меню."""
    log.debug(f"Login | event=in_game user_id={user_id} char_id={char_id} location_id={loc_id}")

    sync_service = GameSyncService(session)
    await sync_service.synchronize_player_state(char_id)
    log.debug(f"StateSync | status=success char_id={char_id}")

    nav_service = NavigationService(char_id=char_id, state_data=state_data)
    nav_text, nav_kb = await nav_service.get_navigation_ui(state_name, loc_id)

    menu_service = MenuService(game_stage="in_game", state_data=state_data, session=session)
    menu_text, menu_kb = await menu_service.get_data_menu()

    msg_menu = session_context.get("message_menu")
    msg_content = session_context.get("message_content")

    if not isinstance(msg_menu, dict) or not isinstance(msg_content, dict):
        log.warning(f"Login | status=failed reason='message_menu or message_content not found' user_id={user_id}")
        await Err.generic_error(call)
        return

    await bot.edit_message_text(
        chat_id=msg_menu["chat_id"],
        message_id=msg_menu["message_id"],
        text=menu_text,
        reply_markup=menu_kb,
        parse_mode="HTML",
    )
    await bot.edit_message_text(
        chat_id=msg_content["chat_id"],
        message_id=msg_content["message_id"],
        text=nav_text,
        reply_markup=nav_kb,
        parse_mode="HTML",
    )

    await fsm_clean_core_state(state=state, event_source=call)
    await state.set_state(InGame.navigation)
    log.info(f"FSM | state=InGame.navigation char_id={char_id}")


@router.callback_query(LobbySelectionCallback.filter(F.action == "login"))
async def start_logging_handler(call: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession) -> None:
    """Обрабатывает вход в игру, определяет игровой этап и направляет пользователя."""
    if not call.from_user:
        return

    user_id = call.from_user.id
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")

    log.info(f"Login | event=start user_id={user_id} char_id={char_id}")

    message_content = session_context.get("message_content")
    message_menu = session_context.get("message_menu")

    if not isinstance(char_id, int) or not isinstance(message_content, dict):
        log.warning(
            f"Login | status=failed reason='Invalid FSM data' user_id={user_id} char_id={char_id} content_type={type(message_content)}"
        )
        await Err.generic_error(call)
        return

    await call.answer()

    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)
    login_service = LoginService(char_id=char_id, state_data=state_data)

    async def run_logic() -> Any:
        return await login_service.handle_login(session=session)

    log.debug(f"Login | action=gather_animation_and_logic user_id={user_id}")
    results = await asyncio.gather(
        anim_service.animate_loading(duration=2.0, text="📡 <b>Установка нейро-связи...</b>"),
        run_logic(),
    )
    login_result = results[1]
    log.debug(f"Login | result='{login_result}' user_id={user_id}")

    if not isinstance(login_result, (str, tuple)):
        log.error(
            f"Login | status=failed reason='Invalid result from LoginService' result='{login_result}' user_id={user_id}"
        )
        await Err.generic_error(call)
        return

    char_name, symbiote_name = await _fetch_character_display_data(session, char_id)
    session_context["char_name"] = char_name
    session_context["symbiote_name"] = symbiote_name
    await state.update_data({FSM_CONTEXT_KEY: session_context})
    log.debug(f"FSM | data_updated keys='char_name, symbiote_name' char_id={char_id}")

    if isinstance(login_result, str):
        game_stage = login_result
        log.info(f"Redirect | game_stage='{game_stage}' char_id={char_id}")
        await fsm_clean_core_state(state=state, event_source=call)

        if isinstance(message_menu, dict):
            try:
                ms = MenuService(game_stage=game_stage, state_data=await state.get_data(), session=session)
                menu_text, menu_kb = await ms.get_data_menu()
                await bot.edit_message_text(
                    chat_id=message_menu["chat_id"],
                    message_id=message_menu["message_id"],
                    text=menu_text,
                    reply_markup=menu_kb,
                    parse_mode="HTML",
                )
            except TelegramAPIError as e:
                log.warning(f"Redirect | action=update_menu status=failed char_id={char_id} error='{e}'")

        if game_stage == GameStage.TUTORIAL_STATS:
            await _handle_tutorial_stats(char_id, state, bot, message_content)
        elif game_stage == GameStage.TUTORIAL_SKILL:
            await _handle_tutorial_skills(char_id, state, bot, message_content)
        elif game_stage == GameStage.CREATION:
            if isinstance(message_menu, dict):
                await start_creation_handler(call, state, bot, user_id, char_id, message_menu, session)
        elif game_stage == "combat":
            await _handle_combat_restore(user_id, char_id, state, bot, state_data, session_context, call)
        else:
            log.error(f"Redirect | status=failed reason='Unknown game_stage' stage='{game_stage}' char_id={char_id}")
            await Err.generic_error(call)

    elif isinstance(login_result, tuple):
        state_name, loc_id = login_result
        log.info(f"Login | status=success state='{state_name}' loc_id='{loc_id}' char_id={char_id}")

        if state_name == "combat":
            await _handle_combat_restore(user_id, char_id, state, bot, state_data, session_context, call)
        else:
            await _handle_in_game_login(
                user_id, char_id, state, bot, state_data, session_context, state_name, loc_id, call, session
            )
