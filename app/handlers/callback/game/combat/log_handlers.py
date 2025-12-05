"""
Обработчик пагинации в логе боя.
"""

from typing import Any

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log

from app.resources.fsm_states.states import InGame
from app.resources.keyboards.combat_callback import CombatLogCallback
from app.services.core_service.manager.account_manager import AccountManager
from app.services.core_service.manager.combat_manager import CombatManager
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.combat.combat_ui_service import CombatUIService

log_router = Router(name="combat_log")


@log_router.callback_query(InGame.combat, CombatLogCallback.filter())
async def combat_log_pagination(
    call: CallbackQuery,
    callback_data: CombatLogCallback,
    state: FSMContext,
    combat_manager: CombatManager,
    account_manager: AccountManager,
) -> None:
    if not call.from_user or not isinstance(call.message, Message):
        return

    page = callback_data.page
    state_data = await state.get_data()
    session_context: dict[str, Any] = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    user_id = call.from_user.id
    session_id = session_context.get("combat_session_id")

    log.info(f"CombatLog | event=pagination user_id={user_id} char_id={char_id} page={page}")

    if not session_id or not char_id:
        log.warning(f"CombatLog | status=failed reason='session_id or char_id missing' user_id={user_id}")
        await Err.generic_error(call)
        return

    ui_service = CombatUIService(user_id, char_id, str(session_id), state_data, combat_manager, account_manager)
    text, kb = await ui_service.render_combat_log(page=page)

    try:
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    except TelegramAPIError as e:
        log.warning(f"UIRender | component=combat_log status=failed user_id={user_id} error='{e}'")
    await call.answer()
