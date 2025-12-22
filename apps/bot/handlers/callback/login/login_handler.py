# apps/bot/handlers/callback/login/login_handler.py
import asyncio
from typing import cast

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.handlers.callback.onboarding.onboarding_handler import start_onboarding_process
from apps.bot.resources.keyboards.callback_data import LobbySelectionCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY, fsm_clean_core_state
from apps.bot.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from apps.common.core.container import AppContainer
from apps.common.schemas_dto import SessionDataDTO
from apps.common.schemas_dto.auth_dto import GameStage

router = Router(name="login_handler_router")


@router.callback_query(LobbySelectionCallback.filter(F.action == "login"))
async def start_logging_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    container: AppContainer,
) -> None:
    if not call.from_user:
        return
    user_id = call.from_user.id
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    log.info(f"Login | event=start user_id={user_id} char_id={char_id}")

    if not isinstance(char_id, int):
        await Err.generic_error(call)
        return
    await call.answer()

    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)

    orchestrator = container.get_auth_bot_orchestrator(session)

    async def run_logic():
        return await orchestrator.handle_login(char_id, state_data)

    results = await asyncio.gather(
        anim_service.animate_loading(duration=2.0, text="📡 <b>Установка нейро-связи...</b>"),
        run_logic(),
    )
    result_dto = results[1]

    # Обновляем FSM
    if result_dto.fsm_update:
        session_context.update(result_dto.fsm_update)
        await state.update_data({FSM_CONTEXT_KEY: session_context})

    if result_dto.new_state:
        await fsm_clean_core_state(state=state, event_source=call)
        await state.set_state(result_dto.new_state)
        log.info(f"FSM | state={result_dto.new_state} char_id={char_id}")

    # Обработка создания персонажа (пока оставим как есть, так как это отдельный флоу)
    if result_dto.game_stage == GameStage.CREATION:
        if call.message:
            # mypy считает, что call.message может быть InaccessibleMessage,
            # но мы знаем, что в данном контексте это Message.
            # Используем cast для явного указания типа.
            message = cast(Message, call.message)
            await start_onboarding_process(
                message=message, state=state, char_id=char_id, session=session, container=container
            )
        return

    # Рендеринг меню
    if result_dto.menu and (coords := orchestrator.get_menu_coords(state_data)):
        try:
            await bot.edit_message_text(
                chat_id=coords.chat_id,
                message_id=coords.message_id,
                text=result_dto.menu.text,
                reply_markup=result_dto.menu.kb,
                parse_mode="HTML",
            )
        except TelegramAPIError as e:
            log.warning(f"Login | action=update_menu status=failed char_id={char_id} error='{e}'")

    # Рендеринг контента
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
            log.warning(f"Login | action=update_content status=failed char_id={char_id} error='{e}'")
