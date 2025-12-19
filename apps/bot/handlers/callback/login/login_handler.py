# apps/bot/handlers/callback/login/login_handler.py
import asyncio
from typing import Any

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.handlers.callback.login.char_creation import start_creation_handler
from apps.bot.resources.fsm_states.states import InGame, StartTutorial
from apps.bot.resources.keyboards.callback_data import LobbySelectionCallback
from apps.bot.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from apps.bot.ui_service.combat.combat_bot_orchestrator import CombatBotOrchestrator
from apps.bot.ui_service.exploration.exploration_ui import ExplorationUIService
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY, fsm_clean_core_state
from apps.bot.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from apps.bot.ui_service.menu_service import MenuService
from apps.bot.ui_service.tutorial.tutorial_service import TutorialServiceStats
from apps.bot.ui_service.tutorial.tutorial_service_skill import TutorialServiceSkills
from apps.common.database.repositories import get_character_repo, get_symbiote_repo
from apps.common.schemas_dto import SessionDataDTO
from apps.common.schemas_dto.auth_dto import GameStage
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.game_core.game_service.game_sync_service import GameSyncService
from apps.game_core.game_service.login_service import LoginService

router = Router(name="login_handler_router")


async def _fetch_character_display_data(session: AsyncSession, char_id: int) -> tuple[str, str]:
    char_repo = get_character_repo(session)
    sym_repo = get_symbiote_repo(session)
    character = await char_repo.get_character(char_id)
    char_name = character.name if character else "Прошедший"
    symbiote = await sym_repo.get_symbiote(char_id)
    sym_name = symbiote.symbiote_name if symbiote else DEFAULT_ACTOR_NAME
    return char_name, sym_name


async def _handle_tutorial_stats(char_id: int, state: FSMContext, bot: Bot, message_content: dict) -> None:
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
    account_manager: AccountManager,
    orchestrator: CombatBotOrchestrator,
) -> None:
    log.debug(f"SessionRestore | type=combat user_id={user_id} char_id={char_id}")
    ac_data = await account_manager.get_account_data(char_id)
    if not ac_data:
        await Err.generic_error(call)
        return
    combat_session_id = ac_data.get("combat_session_id")
    if not combat_session_id:
        await Err.generic_error(call)
        return
    session_context["combat_session_id"] = combat_session_id
    await state.update_data({FSM_CONTEXT_KEY: session_context})

    # Получаем оба view одним вызовом
    (dash_text, dash_kb), (log_text, log_kb) = await orchestrator.get_dashboard_view(combat_session_id, char_id, {})

    msg_menu = session_context.get("message_menu")
    msg_content = session_context.get("message_content")
    if isinstance(msg_menu, dict):
        try:
            await bot.edit_message_text(
                chat_id=msg_menu["chat_id"],
                message_id=msg_menu["message_id"],
                text=log_text,
                reply_markup=log_kb,
                parse_mode="HTML",
            )
        except TelegramAPIError as e:
            log.warning(f"SessionRestore | action=update_menu status=failed char_id={char_id} error='{e}'")
    if isinstance(msg_content, dict):
        try:
            await bot.edit_message_text(
                chat_id=msg_content["chat_id"],
                message_id=msg_content["message_id"],
                text=dash_text,
                reply_markup=dash_kb,
                parse_mode="HTML",
            )
        except TelegramAPIError as e:
            log.warning(f"SessionRestore | action=update_content status=failed char_id={char_id} error='{e}'")
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
    call: CallbackQuery,
    session: AsyncSession,
    account_manager: AccountManager,
    exploration_ui_service: ExplorationUIService,
) -> None:
    log.debug(f"Login | event=in_game user_id={user_id} char_id={char_id}")
    sync_service = GameSyncService(session, account_manager)
    await sync_service.synchronize_player_state(char_id)
    actor_name = session_context.get("symbiote_name", "Симбиот")
    nav_text, nav_kb = await exploration_ui_service.render_map(char_id=char_id, actor_name=actor_name)
    menu_service = MenuService(
        game_stage="in_game", state_data=state_data, session=session, account_manager=account_manager
    )
    menu_text, menu_kb = await menu_service.get_data_menu()
    msg_menu = session_context.get("message_menu")
    msg_content = session_context.get("message_content")
    if not isinstance(msg_menu, dict) or not isinstance(msg_content, dict):
        await Err.generic_error(call)
        return
    try:
        await bot.edit_message_text(
            chat_id=msg_menu["chat_id"],
            message_id=msg_menu["message_id"],
            text=menu_text,
            reply_markup=menu_kb,
            parse_mode="HTML",
        )
    except TelegramAPIError as e:
        log.warning(f"Login | action=update_menu status=failed char_id={char_id} error='{e}'")
    try:
        await bot.edit_message_text(
            chat_id=msg_content["chat_id"],
            message_id=msg_content["message_id"],
            text=nav_text,
            reply_markup=nav_kb,
            parse_mode="HTML",
        )
    except TelegramAPIError as e:
        log.warning(f"Login | action=update_content status=failed char_id={char_id} error='{e}'")
    await fsm_clean_core_state(state=state, event_source=call)
    await state.set_state(InGame.navigation)
    log.info(f"FSM | state=InGame.navigation char_id={char_id}")


@router.callback_query(LobbySelectionCallback.filter(F.action == "login"))
async def start_logging_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    account_manager: AccountManager,
    orchestrator: CombatBotOrchestrator,
    exploration_ui_service: ExplorationUIService,
) -> None:
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
        await Err.generic_error(call)
        return
    await call.answer()
    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)
    login_service = LoginService(char_id=char_id, state_data=state_data, account_manager=account_manager)

    async def run_logic() -> Any:
        return await login_service.handle_login(session=session)

    results = await asyncio.gather(
        anim_service.animate_loading(duration=2.0, text="📡 <b>Установка нейро-связи...</b>"),
        run_logic(),
    )
    login_result = results[1]
    if not isinstance(login_result, (str, tuple)):
        await Err.generic_error(call)
        return
    char_name, symbiote_name = await _fetch_character_display_data(session, char_id)
    session_context["char_name"] = char_name
    session_context["symbiote_name"] = symbiote_name
    await state.update_data({FSM_CONTEXT_KEY: session_context})
    if isinstance(login_result, str):
        game_stage = login_result
        await fsm_clean_core_state(state=state, event_source=call)
        if isinstance(message_menu, dict):
            try:
                ms = MenuService(
                    game_stage=game_stage,
                    state_data=await state.get_data(),
                    session=session,
                    account_manager=account_manager,
                )
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
                await start_creation_handler(call, state, bot, user_id, char_id, message_menu, session, account_manager)
        elif game_stage == "combat":
            await _handle_combat_restore(
                user_id, char_id, state, bot, state_data, session_context, call, account_manager, orchestrator
            )
        else:
            await Err.generic_error(call)
    elif isinstance(login_result, tuple):
        if login_result[0] == "combat":
            await _handle_combat_restore(
                user_id, char_id, state, bot, state_data, session_context, call, account_manager, orchestrator
            )
        else:
            await _handle_in_game_login(
                user_id,
                char_id,
                state,
                bot,
                state_data,
                session_context,
                call,
                session,
                account_manager,
                exploration_ui_service,
            )
