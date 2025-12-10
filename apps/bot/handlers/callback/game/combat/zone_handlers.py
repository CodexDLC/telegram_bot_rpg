"""
Обработчик нажатий на зоны атаки/защиты в бою.
"""

from typing import Any

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log

from apps.bot.resources.fsm_states.states import InGame
from apps.bot.resources.keyboards.combat_callback import CombatZoneCallback
from apps.bot.ui_service.combat.combat_ui_service import CombatUIService
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.combat_manager import CombatManager

zone_router = Router(name="combat_zones")


@zone_router.callback_query(InGame.combat, CombatZoneCallback.filter())
async def combat_zone_toggle_handler(
    call: CallbackQuery,
    callback_data: CombatZoneCallback,
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
    layer, zone_id = callback_data.layer, callback_data.zone_id

    log.info(f"Combat | event=zone_toggle user_id={user_id} char_id={char_id} layer={layer} zone={zone_id}")

    selection: dict[str, list[str]] = state_data.get("combat_selection", {"atk": [], "def": []})
    current_list = selection.get(layer, [])

    if zone_id in current_list:
        current_list.remove(zone_id)
    else:
        if layer == "def":
            current_list.clear()
        current_list.append(zone_id)

    selection[layer] = current_list
    await state.update_data(combat_selection=selection)
    log.debug(f"FSM | data_updated key=combat_selection user_id={user_id} selection='{selection}'")

    session_id = session_context.get("combat_session_id")
    if not session_id or not char_id:
        log.warning(f"Combat | status=failed reason='session_id or char_id missing' user_id={user_id}")
        await Err.generic_error(call)
        return

    ui_service = CombatUIService(user_id, char_id, str(session_id), state_data, combat_manager, account_manager)
    text, kb = await ui_service.render_dashboard(current_selection=selection)

    try:
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    except TelegramAPIError as e:
        log.warning(f"UIRender | component=combat_dashboard status=failed user_id={user_id} error='{e}'")
    await call.answer()
