# app/handlers/callback/game/arena/arena_main.py

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

# --- FSM & Keyboards ---
from app.resources.fsm_states.states import ArenaState, InGame
from app.resources.keyboards.callback_data import ArenaQueueCallback

# --- Services & Helpers ---
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.arena_ui_service.arena_builder import ArenaUIBuilder
from app.services.ui_service.navigation_service import NavigationService

router = Router(name="arena_main_router")


# =================================================================
# 1. ГЛАВНОЕ МЕНЮ АРЕНЫ (Start Page / Back to Main)
# =================================================================
@router.callback_query(ArenaState.menu, ArenaQueueCallback.filter(F.action == "menu_main"))
async def arena_render_main_menu_handler(
    call: CallbackQuery,
    callback_data: ArenaQueueCallback,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
) -> None:
    """
    Рендерит Главное Меню Арены.
    Используется при входе (через HubEntry) или при нажатии "Назад" из подменю.
    """
    if not call.from_user:
        return

    # 1. Инициализация данных
    user_id = call.from_user.id
    char_id = callback_data.char_id
    state_data = await state.get_data()

    log.debug(f"User {user_id} запрашивает Главное Меню Арены.")

    # 2. Вызов UI Builder
    try:
        # Создаем билдер, который умеет рисовать интерфейс Арены
        ui_builder = ArenaUIBuilder(char_id, state_data, session)
        text, kb = await ui_builder.render_menu()
    except RuntimeError as e:
        log.error(f"Ошибка в ArenaUIBuilder: {e}")
        await Err.generic_error(call)
        return

    # 3. Обновление сообщения
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
        await call.answer()
    else:
        await Err.message_content_not_found_in_fsm(call)


# =================================================================
# 2. ВЫХОД ИЗ СЕРВИСА (Exit to World)
# =================================================================
@router.callback_query(ArenaState.menu, ArenaQueueCallback.filter(F.action == "exit_service"))
async def arena_exit_service_handler(
    call: CallbackQuery,
    callback_data: ArenaQueueCallback,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
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

    # 1. Возвращаемся в состояние Навигации
    await state.set_state(InGame.navigation)

    # 2. Инициируем релоад UI Навигации
    state_data = await state.get_data()

    # NavigationService сам найдет текущую локацию (svc_arena_main)
    # и отрисует её "внешний вид" (training_ground_entrance)
    nav_service = NavigationService(char_id=char_id, state_data=state_data)
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
