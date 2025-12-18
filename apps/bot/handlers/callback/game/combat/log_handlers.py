"""
Обработчик пагинации в логе боя.
"""

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log

from apps.bot.resources.fsm_states.states import InGame
from apps.bot.resources.keyboards.combat_callback import CombatLogCallback
from apps.bot.ui_service.combat.combat_bot_orchestrator import CombatBotOrchestrator
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err

log_router = Router(name="combat_log")


@log_router.callback_query(InGame.combat, CombatLogCallback.filter())
async def combat_log_pagination(
    call: CallbackQuery,
    callback_data: CombatLogCallback,
    state: FSMContext,
    orchestrator: CombatBotOrchestrator,
) -> None:
    if not call.from_user or not isinstance(call.message, Message):
        return

    page = callback_data.page
    state_data = await state.get_data()
    char_id = state_data.get("char_id")
    user_id = call.from_user.id
    session_id = state_data.get("combat_session_id")

    log.info(f"CombatLog | event=pagination user_id={user_id} char_id={char_id} page={page}")

    if not session_id or not char_id:
        log.warning(f"CombatLog | status=failed reason='session_id or char_id missing' user_id={user_id}")
        await Err.generic_error(call)
        return

    text, kb = await orchestrator.get_log_view(session_id, char_id, page)

    try:
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    except TelegramAPIError as e:
        log.warning(f"UIRender | component=combat_log status=failed user_id={user_id} error='{e}'")
    await call.answer()
