# app/handlers/callback/game/combat/menu_handlers.py
"""
Обработчики навигации по меню боя: открытие меню, переключение вкладок (скиллы/предметы).
"""

from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log

from apps.bot.resources.fsm_states.states import InGame
from apps.bot.resources.keyboards.combat_callback import CombatActionCallback
from apps.bot.ui_service.combat.combat_bot_orchestrator import CombatBotOrchestrator
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err

menu_router = Router(name="combat_menu")


@menu_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action == "menu"))
async def open_combat_menu_handler(call: CallbackQuery, state: FSMContext, orchestrator: CombatBotOrchestrator):
    if not call.from_user or not isinstance(call.message, Message):
        return

    state_data = await state.get_data()
    char_id = state_data.get("char_id")
    session_id = state_data.get("combat_session_id")

    if not char_id or not session_id:
        return await Err.report_and_restart(call, "Данные сессии боя утеряны.")

    log.debug(f"Combat | action=open_menu user_id={call.from_user.id}")
    text, kb = await orchestrator.get_menu_view(session_id, char_id, "skills")
    with suppress(TelegramAPIError):
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@menu_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action == "menu_skills"))
async def switch_to_skills_handler(call: CallbackQuery, state: FSMContext, orchestrator: CombatBotOrchestrator):
    if not call.from_user or not isinstance(call.message, Message):
        return

    state_data = await state.get_data()
    char_id = state_data.get("char_id")
    session_id = state_data.get("combat_session_id")

    if not char_id or not session_id:
        return await Err.report_and_restart(call, "Данные сессии боя утеряны.")

    text, kb = await orchestrator.get_menu_view(session_id, char_id, "skills")
    with suppress(TelegramAPIError):
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@menu_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action == "menu_items"))
async def switch_to_items_handler(call: CallbackQuery, state: FSMContext, orchestrator: CombatBotOrchestrator):
    if not call.from_user or not isinstance(call.message, Message):
        return

    state_data = await state.get_data()
    char_id = state_data.get("char_id")
    session_id = state_data.get("combat_session_id")

    if not char_id or not session_id:
        return await Err.report_and_restart(call, "Данные сессии боя утеряны.")

    text, kb = await orchestrator.get_menu_view(session_id, char_id, "items")
    with suppress(TelegramAPIError):
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await call.answer()
