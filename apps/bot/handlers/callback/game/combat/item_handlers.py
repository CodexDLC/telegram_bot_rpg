"""
Обработчики, связанные с использованием предметов (расходников) в бою.
"""

from contextlib import suppress
from typing import Any

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log

from apps.bot.resources.fsm_states.states import InGame
from apps.bot.resources.keyboards.combat_callback import CombatItemCallback
from apps.bot.ui_service.combat.combat_ui_service import CombatUIService
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.combat_manager import CombatManager
from apps.game_core.game_service.combat.combat_service import CombatService

item_router = Router(name="combat_items")


@item_router.callback_query(InGame.combat, CombatItemCallback.filter(F.action == "use"))
async def combat_item_use_handler(
    call: CallbackQuery,
    callback_data: CombatItemCallback,
    state: FSMContext,
    combat_manager: CombatManager,
    account_manager: AccountManager,
) -> None:
    if not call.from_user or not isinstance(call.message, Message):
        return

    state_data = await state.get_data()
    session_context: dict[str, Any] = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    user_id = call.from_user.id
    session_id = session_context.get("combat_session_id")
    item_id = callback_data.item_id

    log.info(f"Combat | event=item_use user_id={user_id} char_id={char_id} item_id={item_id}")

    if not session_id or not char_id:
        await Err.generic_error(call)
        return

    combat_service = CombatService(str(session_id), combat_manager, account_manager)
    success, msg = await combat_service.use_consumable(char_id, item_id)

    await call.answer(msg, show_alert=True)

    if success:
        ui_service = CombatUIService(user_id, char_id, str(session_id), state_data, combat_manager, account_manager)
        text, kb = await ui_service.render_items_menu()
        with suppress(TelegramAPIError):
            await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
