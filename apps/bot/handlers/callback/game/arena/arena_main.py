# apps/bot/handlers/callback/game/arena/arena_main.py
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import ArenaState
from apps.bot.resources.keyboards.callback_data import ArenaQueueCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.common.core.container import AppContainer

router = Router(name="arena_main_router")


@router.callback_query(ArenaState.menu, ArenaQueueCallback.filter(F.action == "menu_main"))
async def arena_render_main_menu_handler(
    call: CallbackQuery,
    callback_data: ArenaQueueCallback,
    state: FSMContext,
    bot: Bot,
    container: AppContainer,
    session: AsyncSession,
) -> None:
    if not call.from_user:
        return
    char_id = callback_data.char_id
    user_id = call.from_user.id
    log.info(f"Arena | event=view_main_menu user_id={user_id} char_id={char_id}")

    state_data = await state.get_data()

    # Создаем оркестратор через контейнер
    orchestrator = container.get_arena_bot_orchestrator(session)

    # Получаем меню через оркестратор
    result_dto = await orchestrator.get_main_menu(state_data)

    # Обновляем сообщение через координаты
    if result_dto.content and (coords := orchestrator.get_content_coords(state_data)):
        await bot.edit_message_text(
            chat_id=coords.chat_id,
            message_id=coords.message_id,
            text=result_dto.content.text,
            reply_markup=result_dto.content.kb,
            parse_mode="HTML",
        )
        await call.answer()
    else:
        log.error(f"Arena | status=failed reason='message_content or view data missing' user_id={user_id}")
        await Err.message_content_not_found_in_fsm(call)


@router.callback_query(ArenaState.menu, ArenaQueueCallback.filter(F.action == "exit_service"))
async def arena_exit_service_handler(
    call: CallbackQuery,
    callback_data: ArenaQueueCallback,
    state: FSMContext,
    bot: Bot,
    container: AppContainer,
    session: AsyncSession,
) -> None:
    if not call.from_user:
        return
    user_id = call.from_user.id
    char_id = callback_data.char_id
    log.info(f"Arena | event=exit_service user_id={user_id} char_id={char_id}")

    await call.answer("Вы покидаете Полигон.")

    state_data = await state.get_data()

    # Создаем оркестратор через контейнер
    orchestrator = container.get_arena_bot_orchestrator(session)

    # Выходим с арены через оркестратор
    result_dto = await orchestrator.leave_arena(char_id, state_data)

    if result_dto.new_state:
        await state.set_state(result_dto.new_state)
        log.info(f"FSM | state={result_dto.new_state} user_id={user_id}")

    if result_dto.content and (coords := orchestrator.get_content_coords(state_data)):
        await bot.edit_message_text(
            chat_id=coords.chat_id,
            message_id=coords.message_id,
            text=result_dto.content.text,
            parse_mode="html",
            reply_markup=result_dto.content.kb,
        )
    else:
        log.error(f"Arena | status=failed reason='Could not render navigation UI on exit' user_id={user_id}")
        await Err.generic_error(call)
