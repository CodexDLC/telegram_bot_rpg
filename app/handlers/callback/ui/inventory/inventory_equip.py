# app/handlers/callback/ui/inventory/inventory_equip.py
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import InGame
from app.resources.keyboards.inventory_callback import InventoryCallback
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.inventory.inventory_ui_service import InventoryUIService

router = Router(name="inventory_equip_router")


@router.callback_query(
    InGame.inventory,
    InventoryCallback.filter((F.section == "equip") & (F.level == 1)),
)
async def inventory_equip_list_handler(
    call: CallbackQuery,
    callback_data: InventoryCallback,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """
    Уровень 1: Список Экипировки.
    Обрабатывает фильтры (category) и пагинацию (page).
    """
    # 1. Security Check (защита от нажатия чужих кнопок)
    if call.from_user.id != callback_data.user_id:
        await Err.access_denied(call)
        return

    # 2. Инициализация данных
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    user_id = session_context.get("user_id") or call.from_user.id
    char_id = session_context.get("char_id")

    if not char_id:
        log.error(f"char_id not found in FSM for user {call.from_user.id}")
        await Err.char_id_not_found_in_fsm(call)
        return

    # 3. Подготовка сервиса
    service = InventoryUIService(char_id=char_id, user_id=user_id, session=session, state_data=state_data)

    # 4. Получение данных (UI)
    # section берем жестко "equip" (или из callback_data), category и page — из кнопки
    text, kb = await service.render_item_list(section="equip", category=callback_data.category, page=callback_data.page)

    # 5. Отправка ответа
    # Получаем координаты сообщения для редактирования
    message_data = service.get_message_content_data()
    if not message_data:
        await Err.generic_error(call)
        return

    chat_id, message_id = message_data

    await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=kb, parse_mode="HTML")
    # Отвечаем, чтобы убрать "часики" (особенно важно при пагинации)
    await call.answer()
