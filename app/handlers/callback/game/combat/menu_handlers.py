# app/handlers/callback/game/combat/menu_handlers.py
"""
Обработчики навигации по меню боя: открытие меню, переключение вкладок (скиллы/предметы).
"""

from contextlib import suppress
from typing import Any

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log

from app.resources.fsm_states.states import InGame
from app.resources.keyboards.combat_callback import CombatActionCallback
from app.services.core_service.manager.account_manager import AccountManager
from app.services.core_service.manager.combat_manager import CombatManager
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.combat.combat_ui_service import CombatUIService

menu_router = Router(name="combat_menu")


async def get_services(
    call: CallbackQuery, state: FSMContext, combat_manager: CombatManager, account_manager: AccountManager
) -> CombatUIService | None:
    """
    Хелпер для инициализации сервисов боя из хэндлера.
    Возвращает CombatUIService или None, если данные сессии не найдены.
    """
    if not call.from_user or not call.message:
        return None

    user_id = call.from_user.id
    state_data = await state.get_data()
    session_context: dict[str, Any] = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    session_id = session_context.get("combat_session_id")

    if not char_id or not session_id:
        return None

    ui_service = CombatUIService(user_id, char_id, str(session_id), state_data, combat_manager, account_manager)
    return ui_service


@menu_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action == "menu"))
async def open_combat_menu_handler(
    call: CallbackQuery, state: FSMContext, combat_manager: CombatManager, account_manager: AccountManager
):
    ui_service = await get_services(call, state, combat_manager, account_manager)
    if not ui_service or not isinstance(call.message, Message):
        return

    log.debug(f"Combat | action=open_menu user_id={call.from_user.id}")
    text, kb = await ui_service.render_skills_menu()
    with suppress(TelegramAPIError):
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@menu_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action == "menu_skills"))
async def switch_to_skills_handler(
    call: CallbackQuery, state: FSMContext, combat_manager: CombatManager, account_manager: AccountManager
):
    ui_service = await get_services(call, state, combat_manager, account_manager)
    if not ui_service or not isinstance(call.message, Message):
        return

    text, kb = await ui_service.render_skills_menu()
    with suppress(TelegramAPIError):
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@menu_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action == "menu_items"))
async def switch_to_items_handler(
    call: CallbackQuery, state: FSMContext, combat_manager: CombatManager, account_manager: AccountManager
):
    ui_service = await get_services(call, state, combat_manager, account_manager)
    if not ui_service or not isinstance(call.message, Message):
        return

    text, kb = await ui_service.render_items_menu()
    with suppress(TelegramAPIError):
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await call.answer()
