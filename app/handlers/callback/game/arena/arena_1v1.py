# app/handlers/callback/game/arena/arena_1v1.py
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import ArenaState
from app.resources.keyboards.callback_data import ArenaQueueCallback

router = Router(name="arena_1v1_router")


# =================================================================
# 1. ОБРАБОТЧИК ПОДМЕНЮ 1v1 (action="match_menu")
# =================================================================
@router.callback_query(ArenaState.menu, ArenaQueueCallback.filter(F.action == "match_menu"))
async def arena_1v1_menu_handler(
    call: CallbackQuery, callback_data: ArenaQueueCallback, state: FSMContext, session: AsyncSession
) -> None:
    """
    Обрабатывает переход в подменю 1v1 или Группового боя.
    """
    if not call.from_user:
        return

    match_type = callback_data.match_type
    log.info(f"User {call.from_user.id} вошел в меню: {match_type}.")
    await call.answer(f"Загрузка меню {match_type} (WIP).")

    # TODO: Здесь будет вызов ArenaMatchBuilder.render_match_menu(match_type)
    # TODO: await state.set_state(ArenaState.match_1v1_menu)
    pass


# =================================================================
# 2. ОБРАБОТЧИК ПОДАЧИ ЗАЯВКИ (action="submit_queue")
# =================================================================
@router.callback_query(ArenaState.menu, ArenaQueueCallback.filter(F.action == "submit_queue_1x1"))
async def arena_submit_queue_handler(
    call: CallbackQuery, callback_data: ArenaQueueCallback, state: FSMContext, session: AsyncSession
) -> None:
    """
    Обрабатывает подачу заявки 1v1 и переход в состояние ArenaState.waiting_in_queue.
    """
    if not call.from_user:
        return

    log.info(f"User {call.from_user.id} подал заявку 1v1 (WIP).")
    await call.answer("Заявка принята! Ожидание соперника...")

    # TODO: ArenaService.add_to_queue(char_id, match_type)
    # TODO: await state.set_state(ArenaState.waiting_in_queue)
    pass
