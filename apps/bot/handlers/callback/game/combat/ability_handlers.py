"""
Обработчики, связанные с использованием способностей (умений) в бою.
"""

from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import BotState
from apps.bot.resources.keyboards.combat_callback import CombatAbilityCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.core.container import AppContainer

ability_router = Router(name="combat_abilities")


@ability_router.callback_query(BotState.combat, CombatAbilityCallback.filter(F.action == "select"))
async def handle_skill_select(
    call: CallbackQuery,
    callback_data: CombatAbilityCallback,
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

    ability_id = callback_data.ability_id

    log.info(f"Combat | event=ability_select user_id={call.from_user.id} char_id={char_id} ability={ability_id}")

    if not session_id or not char_id:
        await Err.generic_error(call)
        return

    # Создаем оркестратор через контейнер
    orchestrator = container.get_combat_bot_orchestrator(session)

    # Выбираем способность через оркестратор
    result_dto = await orchestrator.select_ability(session_id, char_id, ability_id, state_data)

    # Обновляем FSM (сохраняем выбранную способность)
    if result_dto.fsm_update:
        await state.update_data(**result_dto.fsm_update)
        log.debug(f"FSM | data_updated user_id={call.from_user.id} update='{result_dto.fsm_update}'")

    await call.answer(f"Выбрано: {ability_id}")

    # Обновляем меню (скиллы)
    if result_dto.menu and (coords := orchestrator.get_menu_coords(state_data)):
        with suppress(TelegramAPIError):
            await bot.edit_message_text(
                chat_id=coords.chat_id,
                message_id=coords.message_id,
                text=result_dto.menu.text,
                reply_markup=result_dto.menu.kb,
                parse_mode="HTML",
            )
