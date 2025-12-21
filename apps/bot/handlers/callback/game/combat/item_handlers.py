"""
Обработчики, связанные с использованием предметов (расходников) в бою.
"""

from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import InGame
from apps.bot.resources.keyboards.combat_callback import CombatItemCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.core.container import AppContainer

item_router = Router(name="combat_items")


@item_router.callback_query(InGame.combat, CombatItemCallback.filter(F.action == "use"))
async def combat_item_use_handler(
    call: CallbackQuery,
    callback_data: CombatItemCallback,
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
    item_id = callback_data.item_id

    log.info(f"Combat | event=item_use user_id={user_id} char_id={char_id} item_id={item_id}")

    if not session_id or not char_id:
        await Err.generic_error(call)
        return

    # Создаем оркестратор через контейнер
    orchestrator = container.get_combat_bot_orchestrator(session)

    # Используем предмет через оркестратор
    result_dto = await orchestrator.use_item(session_id, char_id, item_id, state_data)

    # Используем alert_text из DTO для обратной связи
    alert_text = result_dto.alert_text or "Предмет использован"
    await call.answer(alert_text, show_alert=False)

    # Обновляем сообщение через координаты (по стандарту)
    if result_dto.menu and (coords := orchestrator.get_menu_coords(state_data)):
        with suppress(TelegramAPIError):
            await bot.edit_message_text(
                chat_id=coords.chat_id,
                message_id=coords.message_id,
                text=result_dto.menu.text,
                reply_markup=result_dto.menu.kb,
                parse_mode="HTML",
            )
