"""
Обработчик нажатий на зоны атаки/защиты в бою.
"""

from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import BotState
from apps.bot.resources.keyboards.combat_callback import CombatZoneCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.core.container import AppContainer

zone_router = Router(name="combat_zones")


@zone_router.callback_query(BotState.combat, CombatZoneCallback.filter())
async def combat_zone_toggle_handler(
    call: CallbackQuery,
    callback_data: CombatZoneCallback,
    state: FSMContext,
    bot: Bot,
    container: AppContainer,
    session: AsyncSession,
) -> None:
    if not call.from_user or not isinstance(call.message, Message):
        return

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})

    # Читаем из session_context
    char_id = session_context.get("char_id")
    session_id = session_context.get("combat_session_id")

    user_id = call.from_user.id
    layer, zone_id = callback_data.layer, callback_data.zone_id

    log.info(f"Combat | event=zone_toggle user_id={user_id} char_id={char_id} layer={layer} zone={zone_id}")

    if not session_id or not char_id:
        log.warning(f"Combat | status=failed reason='session_id or char_id missing' user_id={user_id}")
        await Err.generic_error(call)
        return

    # Создаем оркестратор через контейнер
    orchestrator = container.get_combat_bot_orchestrator(session)

    # Переключаем зону через оркестратор
    result_dto = await orchestrator.toggle_zone(session_id, char_id, layer, zone_id, state_data)

    # Обновляем FSM, если оркестратор вернул новые данные
    if result_dto.fsm_update:
        await state.update_data(**result_dto.fsm_update)
        log.debug(f"FSM | data_updated user_id={user_id} update='{result_dto.fsm_update}'")

    # Обновляем контентное сообщение (Дашборд)
    if result_dto.content and (coords := orchestrator.get_content_coords(state_data)):
        try:
            await bot.edit_message_text(
                chat_id=coords.chat_id,
                message_id=coords.message_id,
                text=result_dto.content.text,
                reply_markup=result_dto.content.kb,
                parse_mode="HTML",
            )
        except TelegramAPIError as e:
            log.warning(f"UIRender | component=combat_dashboard status=failed user_id={user_id} error='{e}'")

    await call.answer()
