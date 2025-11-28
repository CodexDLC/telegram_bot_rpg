# app/handlers/callback/login/login_handler.py
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
from app.services.core_service.manager.account_manager import account_manager
from app.services.game_service.login_service import LoginService
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import (
    FSM_CONTEXT_KEY,
    fsm_clean_core_state,
)
from app.services.ui_service.combat.combat_ui_service import CombatUIService
from app.services.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from app.services.ui_service.menu_service import MenuService
from app.services.ui_service.navigation_service import NavigationService
from app.services.ui_service.tutorial.tutorial_service import TutorialServiceStats
from app.services.ui_service.tutorial.tutorial_service_skill import (
    TutorialServiceSkills,
)

router = Router(name="login_handler_router")


# ==============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (Private Logic Helpers)
# ==============================================================================


async def _handle_tutorial_stats(char_id: int, state: FSMContext, bot: Bot, message_content: dict) -> None:
    """
    Переводит пользователя в туториал по распределению статов.

    Args:
        char_id (int): ID персонажа.
        state (FSMContext): Контекст FSM.
        bot (Bot): Экземпляр бота.
        message_content (dict): Данные о сообщении для редактирования.

    Returns:
        None
    """
    log.debug(f"Переход к туториалу по статам для char_id={char_id}")
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
    log.debug("Состояние FSM обновлено на StartTutorial.start")


async def _handle_tutorial_skills(char_id: int, state: FSMContext, bot: Bot, message_content: dict) -> None:
    """
    Переводит пользователя в туториал по выбору умений.

    Args:
        char_id (int): ID персонажа.
        state (FSMContext): Контекст FSM.
        bot (Bot): Экземпляр бота.
        message_content (dict): Данные о сообщении для редактирования.

    Returns:
        None
    """
    log.debug(f"Переход к туториалу по скиллам для char_id={char_id}")
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
        log.debug("Состояние FSM обновлено на StartTutorial.in_skills_progres")
    else:
        log.error(f"Не удалось получить данные старта скиллов для char_id={char_id}")


async def _handle_combat_restore(
    user_id: int,
    char_id: int,
    state: FSMContext,
    bot: Bot,
    state_data: dict,
    session_context: dict,
    call: CallbackQuery,
) -> None:
    """
    Восстанавливает и отображает интерфейс боя для пользователя.

    Args:
        user_id (int): ID пользователя.
        char_id (int): ID персонажа.
        state (FSMContext): Контекст FSM.
        bot (Bot): Экземпляр бота.
        state_data (dict): Данные состояния FSM.
        session_context (dict): Контекст сессии из FSM.
        call (CallbackQuery): Входящий колбэк.

    Returns:
        None
    """
    log.debug(f"Восстановление сессии боя для user_id={user_id}, char_id={char_id}")
    ac_data = await account_manager.get_account_data(char_id)
    if not ac_data:
        log.warning(f"Не найдены данные аккаунта для char_id={char_id}")
        await Err.generic_error(call)
        return

    combat_session_id = ac_data.get("combat_session_id")

    if not combat_session_id:
        log.warning(f"Не найден combat_session_id для char_id={char_id} при попытке восстановления боя.")
        await Err.generic_error(call)
        return

    session_context["combat_session_id"] = combat_session_id
    await state.update_data({FSM_CONTEXT_KEY: session_context})
    log.debug(f"combat_session_id={combat_session_id} сохранен в FSM.")

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
    log.debug("Состояние FSM установлено в InGame.combat")


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
) -> None:
    """
    Обрабатывает вход в игру, отображая навигационный интерфейс и меню.

    Args:
        user_id (int): ID пользователя.
        char_id (int): ID персонажа.
        state (FSMContext): Контекст FSM.
        bot (Bot): Экземпляр бота.
        state_data (dict): Данные состояния FSM.
        session_context (dict): Контекст сессии из FSM.
        state_name (str): Название состояния для навигации.
        loc_id (str): ID локации.
        call (CallbackQuery): Входящий колбэк.

    Returns:
        None
    """
    log.debug(f"Вход в игру для user_id={user_id}, char_id={char_id}. Локация: {loc_id}")
    nav_service = NavigationService(char_id=char_id, state_data=state_data)
    nav_text, nav_kb = await nav_service.get_navigation_ui(state_name, loc_id)

    menu_service = MenuService(game_stage="in_game", state_data=state_data)
    menu_text, menu_kb = menu_service.get_data_menu()

    msg_menu = session_context.get("message_menu")
    msg_content = session_context.get("message_content")

    if not isinstance(msg_menu, dict) or not isinstance(msg_content, dict):
        log.warning(f"Не найдены 'message_menu' или 'message_content' в FSM для user_id={user_id}")
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
    log.debug("Состояние FSM установлено в InGame.navigation")


# ==============================================================================
# MAIN LOGIN HANDLER
# ==============================================================================


@router.callback_query(LobbySelectionCallback.filter(F.action == "login"))
async def start_logging_handler(call: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession) -> None:
    """
    Обрабатывает нажатие кнопки "Вход в игру", запуская процесс логина.

    Args:
        call (CallbackQuery): Входящий колбэк.
        state (FSMContext): Контекст FSM.
        bot (Bot): Экземпляр бота.
        session (AsyncSession): Сессия базы данных.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Колбэк без `from_user` в 'start_logging_handler'.")
        return

    user_id = call.from_user.id
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")

    log.info(f"Хэндлер 'start_logging_handler' [lobby:login] вызван user_id={user_id}, char_id={char_id}")

    message_content = session_context.get("message_content")
    message_menu = session_context.get("message_menu")

    if not isinstance(char_id, int) or not isinstance(message_content, dict):
        log.warning(
            f"User {user_id} в 'start_logging_handler' имеет невалидные данные в FSM: char_id={char_id}, message_content={type(message_content)}. Отправка ошибки."
        )
        await Err.generic_error(call)
        return

    await call.answer()

    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)
    login_service = LoginService(char_id=char_id, state_data=state_data)

    async def run_logic() -> Any:
        return await login_service.handle_login(session=session)

    log.debug(f"Запуск анимации и логики входа для user_id={user_id}")
    results = await asyncio.gather(
        anim_service.animate_loading(duration=2.0, text="📡 <b>Установка нейро-связи...</b>"),
        run_logic(),
    )
    login_result = results[1]
    log.debug(f"Результат логина для user_id={user_id}: {login_result}")

    if not isinstance(login_result, (str, tuple)):
        log.warning(f"Некорректный результат от LoginService для user_id={user_id}: {login_result}")
        await Err.generic_error(call)
        return

    if isinstance(login_result, str):
        game_stage = login_result
        log.debug(f"Редирект на game_stage='{game_stage}' для user_id={user_id}")
        await fsm_clean_core_state(state=state, event_source=call)

        if isinstance(message_menu, dict):
            try:
                ms = MenuService(game_stage=game_stage, state_data=await state.get_data())
                menu_text, menu_kb = ms.get_data_menu()
                await bot.edit_message_text(
                    chat_id=message_menu["chat_id"],
                    message_id=message_menu["message_id"],
                    text=menu_text,
                    reply_markup=menu_kb,
                    parse_mode="HTML",
                )
            except TelegramAPIError as e:
                log.debug(f"Не удалось обновить меню для user_id={user_id}: {e}")

        if game_stage == GameStage.TUTORIAL_STATS:
            await _handle_tutorial_stats(char_id, state, bot, message_content)
        elif game_stage == GameStage.TUTORIAL_SKILL:
            await _handle_tutorial_skills(char_id, state, bot, message_content)
        elif game_stage == GameStage.CREATION:
            if isinstance(message_menu, dict):
                await start_creation_handler(call, state, bot, user_id, char_id, message_menu)
        elif game_stage == "combat":
            await _handle_combat_restore(user_id, char_id, state, bot, state_data, session_context, call)
        else:
            log.warning(f"Неизвестный game_stage='{game_stage}' для user_id={user_id}")
            await Err.generic_error(call)

    elif isinstance(login_result, tuple):
        state_name, loc_id = login_result
        log.debug(f"Успешный вход для user_id={user_id}. State: {state_name}, Loc: {loc_id}")

        if state_name == "combat":
            await _handle_combat_restore(user_id, char_id, state, bot, state_data, session_context, call)
        else:
            await _handle_in_game_login(
                user_id,
                char_id,
                state,
                bot,
                state_data,
                session_context,
                state_name,
                loc_id,
                call,
            )
