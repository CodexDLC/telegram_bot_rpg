# app/handlers/callback/game/arena/arena_main.py

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

# --- Импорты для FSM, Callback и Сервисов ---
from app.resources.fsm_states.states import ArenaState, InGame
from app.resources.keyboards.callback_data import ArenaQueueCallback

# from app.services.arena_service import ArenaService # УДАЛЕНО: СЕРВИС НЕ НУЖЕН ЗДЕСЬ
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY  # SessionDataDTO оставлен для UIAnimationService
from app.services.ui_service.navigation_service import NavigationService

router = Router(name="arena_main_router")


# =================================================================
# 1. ОБРАБОТЧИК ВЫХОДА ИЗ СЕРВИСА (action="exit_service")
# =================================================================
@router.callback_query(ArenaState.menu, ArenaQueueCallback.filter(F.action == "exit_service"))
async def arena_exit_service_handler(
    call: CallbackQuery, callback_data: ArenaQueueCallback, state: FSMContext, bot: Bot, session: AsyncSession
) -> None:
    """
    Обрабатывает выход из FSM-состояния Арены и возврат в Навигацию (мир).
    """
    if not call.from_user:
        return

    user_id = call.from_user.id
    char_id = callback_data.char_id

    log.info(f"User {user_id} покидает Сервис Арены и возвращается в мир.")
    await call.answer("Вы покидаете Полигон.")

    # 1. Возвращаемся в состояние Навигации (этот стейт ловит navigation_router)
    await state.set_state(InGame.navigation)

    # 2. Инициируем релоад UI Навигации
    state_data = await state.get_data()
    nav_service = NavigationService(char_id=char_id, state_data=state_data)

    # reload_current_ui находит текущую локацию персонажа (svc_arena_main)
    # и рендерит ее UI (который является training_ground_entrance)
    text, kb = await nav_service.reload_current_ui()

    # 3. Редактирование сообщения
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_content = session_context.get("message_content")

    if message_content and text and kb:
        await bot.edit_message_text(
            chat_id=message_content["chat_id"],
            message_id=message_content["message_id"],
            text=text,
            parse_mode="html",
            reply_markup=kb,
        )
    else:
        log.error(f"Не удалось обновить UI Навигации для user {user_id}.")
        await Err.generic_error(call)
