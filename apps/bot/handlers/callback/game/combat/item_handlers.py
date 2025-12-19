"""
Обработчики, связанные с использованием предметов (расходников) в бою.
"""

from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log

from apps.bot.resources.fsm_states.states import InGame
from apps.bot.resources.keyboards.combat_callback import CombatItemCallback
from apps.bot.ui_service.combat.combat_bot_orchestrator import CombatBotOrchestrator
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.game_core.game_service.combat.combat_orchestrator_rbc import CombatOrchestratorRBC

item_router = Router(name="combat_items")


@item_router.callback_query(InGame.combat, CombatItemCallback.filter(F.action == "use"))
async def combat_item_use_handler(
    call: CallbackQuery,
    callback_data: CombatItemCallback,
    state: FSMContext,
    orchestrator: CombatBotOrchestrator,
    rbc_orchestrator: CombatOrchestratorRBC,
) -> None:
    if not call.from_user or not isinstance(call.message, Message):
        return

    state_data = await state.get_data()
    char_id = state_data.get("char_id")
    user_id = call.from_user.id
    session_id = state_data.get("combat_session_id")
    item_id = callback_data.item_id

    log.info(f"Combat | event=item_use user_id={user_id} char_id={char_id} item_id={item_id}")

    if not session_id or not char_id:
        await Err.generic_error(call)
        return

    success, msg = await rbc_orchestrator.use_consumable(session_id, char_id, item_id)

    await call.answer(msg, show_alert=True)

    if success:
        text, kb = await orchestrator.get_menu_view(session_id, char_id, "items")
        with suppress(TelegramAPIError):
            await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
