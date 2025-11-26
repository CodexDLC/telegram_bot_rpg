from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import InGame
from app.resources.keyboards.callback_data import MeinMenuCallback
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.inventory.inventory_ui_service import InventoryUIService
from app.services.ui_service.navigation_service import NavigationService

router = Router(name="ui_menu_dispatch")


@router.callback_query(MeinMenuCallback.filter())
async def main_menu_dispatcher(
    call: CallbackQuery, callback_data: MeinMenuCallback, state: FSMContext, bot: Bot, session: AsyncSession
) -> None:
    """
    Единая точка входа из Главного Меню.
    Переключает режимы (FSM) и вызывает соответствующие сервисы UI.
    """
    if not call.from_user:
        return

    await call.answer()

    user_id = call.from_user.id
    char_id = callback_data.char_id
    action = callback_data.action

    log.info(f"Меню-диспетчер: User {user_id} выбрал action='{action}'")

    # 1. Базовая проверка сессии
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})

    # Проверяем, совпадает ли char_id в кнопке с текущим в сессии
    if session_context.get("char_id") != char_id:
        log.warning(f"User {user_id}: Нажата кнопка от старой сессии/персонажа ({char_id}).")
        await Err.generic_error(call)
        return

    # Получаем ID сообщения для редактирования (Нижнее сообщение - Контент)
    content_msg = session_context.get("message_content")
    if not content_msg:
        await Err.message_content_not_found_in_fsm(call)
        return

    chat_id = content_msg["chat_id"]
    message_id = content_msg["message_id"]

    try:
        text, kb = None, None

        # === ВЕТКА 1: ИНВЕНТАРЬ ===
        if action == "inventory":
            # 1. Меняем состояние (Изоляция)
            await state.set_state(InGame.inventory)

            # 2. Рендерим "Куклу" (Главная страница инвентаря)
            service = InventoryUIService(state_data=state_data, char_id=char_id, session=session, user_id=user_id)
            text, kb = await service.render_main_menu()

        # === ВЕТКА 2: НАВИГАЦИЯ ===
        elif action == "navigation":
            # 1. Меняем состояние
            await state.set_state(InGame.navigation)

            # 2. Получаем текущую локацию из Redis (через сервис)
            nav_service = NavigationService(char_id=char_id, state_data=state_data)
            text, kb = await nav_service.reload_current_ui()

        # === (ТУТ БУДУТ ДРУГИЕ ВЕТКИ) ===
        # else: ...

        # 3. Обновляем UI
        if text and kb:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text, reply_markup=kb, parse_mode="HTML"
            )
        else:
            await call.answer("Раздел недоступен или пуст.", show_alert=True)

    except RuntimeError as e:
        log.exception(f"Ошибка в диспетчере меню для user {user_id}: {e}")
        await Err.generic_error(call)
