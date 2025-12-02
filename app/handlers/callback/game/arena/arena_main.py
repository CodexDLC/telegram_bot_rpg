# app/handlers/callback/game/arena/arena_main.py

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

# --- FSM & Keyboards ---
from app.resources.fsm_states.states import ArenaState, InGame
from app.resources.keyboards.callback_data import ArenaQueueCallback

# --- Services & Helpers ---
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.arena_ui_service.arena_ui_service import ArenaUIService
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
    session: AsyncSession,
    bot: Bot,
) -> None:
    """
    Показывает главное меню Арены (выбор режима: 1v1, Group).
    Срабатывает при входе или нажатии "Назад" из подменю.
    """
    if not call.from_user:
        return

    char_id = callback_data.char_id
    state_data = await state.get_data()

    # 1. Init UI
    # 🔥 ИСПРАВЛЕНО: Порядок (ID, Session, Data)
    ui = ArenaUIService(char_id, session, state_data)

    # 2. View
    text, kb = await ui.view_main_menu()

    # 3. Update Message
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_content = session_context.get("message_content")

    if message_content and text and kb:
        chat_id = message_content["chat_id"]
        message_id = message_content["message_id"]

        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=kb,
            parse_mode="HTML",
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


# =================================================================
# 3. ОТМЕНА (Выход из очереди)
# =================================================================
@router.callback_query(ArenaState.waiting, ArenaQueueCallback.filter(F.action == "cancel_queue"))
async def arena_universal_cancel_handler(
    call: CallbackQuery,
    callback_data: ArenaQueueCallback,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not call.from_user:
        return

    char_id = callback_data.char_id
    mode = callback_data.match_type

    # 1. Init UI
    state_data = await state.get_data()

    # 🔥 ИСПРАВЛЕНО: Порядок (ID, Session, Data)
    ui = ArenaUIService(char_id, session, state_data)

    # 2. Action (Cancel)
    await ui.action_cancel_queue(mode)

    # 3. State Change
    await state.set_state(ArenaState.menu)

    # 4. View (Back to Mode Menu)
    text, kb = await ui.view_mode_menu(mode)

    if text and kb and isinstance(call.message, Message):
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
        await call.answer("Поиск отменен.")
    else:
        await Err.generic_error(call)
