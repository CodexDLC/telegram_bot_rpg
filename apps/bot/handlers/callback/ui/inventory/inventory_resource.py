from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import BotState
from apps.bot.resources.keyboards.inventory_callback import InventoryCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.core.container import AppContainer

router = Router(name="inventory_resource_router")


@router.callback_query(
    BotState.inventory,
    InventoryCallback.filter((F.section == "resource") & (F.level == 1)),
)
async def inventory_resource_list_handler(
    call: CallbackQuery,
    callback_data: InventoryCallback,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    container: AppContainer,
) -> None:
    """Обрабатывает список ресурсов, фильтры и пагинацию."""
    user_id = call.from_user.id
    if user_id != callback_data.user_id:
        log.warning(
            f"InventoryResource | status=access_denied user_id={user_id} callback_user_id={callback_data.user_id}"
        )
        await Err.access_denied(call)
        return

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")

    if not char_id:
        log.error(f"InventoryResource | status=failed reason='char_id not found in FSM' user_id={user_id}")
        await Err.char_id_not_found_in_fsm(call)
        return

    # Создаем оркестратор через контейнер
    orchestrator = container.get_inventory_bot_orchestrator(session)

    # Получаем список предметов
    result_dto = await orchestrator.get_item_list(
        char_id, user_id, "resource", callback_data.category, callback_data.page, state_data
    )

    # Обновляем сообщение через координаты
    if result_dto.content and (coords := orchestrator.get_content_coords(state_data, user_id)):
        await bot.edit_message_text(
            chat_id=coords.chat_id,
            message_id=coords.message_id,
            text=result_dto.content.text,
            reply_markup=result_dto.content.kb,
            parse_mode="HTML",
        )
        await call.answer()
        log.info(
            f"InventoryResource | event=list_rendered user_id={user_id} char_id={char_id} category='{callback_data.category}' page={callback_data.page}"
        )
    else:
        log.error(f"InventoryResource | status=failed reason='message_content not found' user_id={user_id}")
        await Err.generic_error(call)
