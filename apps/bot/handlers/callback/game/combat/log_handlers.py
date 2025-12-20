"""
Обработчик пагинации в логе боя.
"""

from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import InGame
from apps.bot.resources.keyboards.combat_callback import CombatLogCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.core.container import AppContainer

log_router = Router(name="combat_log")


@log_router.callback_query(InGame.combat, CombatLogCallback.filter())
async def combat_log_pagination(
    call: CallbackQuery,
    callback_data: CombatLogCallback,
    state: FSMContext,
    bot: Bot,
    container: AppContainer,
    session: AsyncSession,
) -> None:
    if not call.from_user or not isinstance(call.message, Message):
        return

    page = callback_data.page
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})

    # Читаем из session_context
    char_id = session_context.get("char_id")
    session_id = session_context.get("combat_session_id")

    user_id = call.from_user.id

    log.info(f"CombatLog | event=pagination user_id={user_id} char_id={char_id} page={page}")

    if not session_id or not char_id:
        log.warning(f"CombatLog | status=failed reason='session_id or char_id missing' user_id={user_id}")
        await Err.generic_error(call)
        return

    # Создаем оркестратор через контейнер
    orchestrator = container.get_combat_bot_orchestrator(session)

    view_result = await orchestrator.get_log_view(session_id, char_id, page, state_data)

    # Обновляем сообщение через координаты (по стандарту)
    # Лог боя - это нижнее сообщение (menu)
    if coords := orchestrator.get_menu_coords(state_data):
        try:
            await bot.edit_message_text(
                chat_id=coords.chat_id,
                message_id=coords.message_id,
                text=view_result.text,
                reply_markup=view_result.kb,
                parse_mode="HTML",
            )
        except TelegramAPIError as e:
            log.warning(f"UIRender | component=combat_log status=failed user_id={user_id} error='{e}'")

    await call.answer()
