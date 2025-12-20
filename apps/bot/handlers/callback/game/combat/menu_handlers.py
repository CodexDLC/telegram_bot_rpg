# app/handlers/callback/game/combat/menu_handlers.py
"""
Обработчики навигации по меню боя: открытие меню, переключение вкладок (скиллы/предметы).
"""

from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import InGame
from apps.bot.resources.keyboards.combat_callback import CombatActionCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.core.container import AppContainer

menu_router = Router(name="combat_menu")


@menu_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action == "menu"))
async def open_combat_menu_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    container: AppContainer,
    session: AsyncSession,
):
    if not call.from_user or not isinstance(call.message, Message):
        return

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})

    # Читаем из session_context
    char_id = session_context.get("char_id")
    session_id = session_context.get("combat_session_id")

    if not char_id or not session_id:
        return await Err.report_and_restart(call, "Данные сессии боя утеряны.")

    # Создаем оркестратор через контейнер
    orchestrator = container.get_combat_bot_orchestrator(session)

    log.debug(f"Combat | action=open_menu user_id={call.from_user.id}")

    view_result = await orchestrator.get_menu_view(session_id, char_id, "skills", state_data)

    if coords := orchestrator.get_menu_coords(state_data):
        with suppress(TelegramAPIError):
            await bot.edit_message_text(
                chat_id=coords.chat_id,
                message_id=coords.message_id,
                text=view_result.text,
                reply_markup=view_result.kb,
                parse_mode="HTML",
            )
    await call.answer()


@menu_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action == "menu_skills"))
async def switch_to_skills_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    container: AppContainer,
    session: AsyncSession,
):
    if not call.from_user or not isinstance(call.message, Message):
        return

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})

    # Читаем из session_context
    char_id = session_context.get("char_id")
    session_id = session_context.get("combat_session_id")

    if not char_id or not session_id:
        return await Err.report_and_restart(call, "Данные сессии боя утеряны.")

    # Создаем оркестратор через контейнер
    orchestrator = container.get_combat_bot_orchestrator(session)

    view_result = await orchestrator.get_menu_view(session_id, char_id, "skills", state_data)

    if coords := orchestrator.get_menu_coords(state_data):
        with suppress(TelegramAPIError):
            await bot.edit_message_text(
                chat_id=coords.chat_id,
                message_id=coords.message_id,
                text=view_result.text,
                reply_markup=view_result.kb,
                parse_mode="HTML",
            )
    await call.answer()


@menu_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action == "menu_items"))
async def switch_to_items_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    container: AppContainer,
    session: AsyncSession,
):
    if not call.from_user or not isinstance(call.message, Message):
        return

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})

    # Читаем из session_context
    char_id = session_context.get("char_id")
    session_id = session_context.get("combat_session_id")

    if not char_id or not session_id:
        return await Err.report_and_restart(call, "Данные сессии боя утеряны.")

    # Создаем оркестратор через контейнер
    orchestrator = container.get_combat_bot_orchestrator(session)

    view_result = await orchestrator.get_menu_view(session_id, char_id, "items", state_data)

    if coords := orchestrator.get_menu_coords(state_data):
        with suppress(TelegramAPIError):
            await bot.edit_message_text(
                chat_id=coords.chat_id,
                message_id=coords.message_id,
                text=view_result.text,
                reply_markup=view_result.kb,
                parse_mode="HTML",
            )
    await call.answer()
