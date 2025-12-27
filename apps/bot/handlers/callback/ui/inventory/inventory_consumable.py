# app/handlers/callback/ui/inventory/inventory_consumable.py
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import BotState
from apps.bot.resources.keyboards.inventory_callback import InventoryCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.core.container import AppContainer

router = Router(name="inventory_consumable_router")


# 1. ОБРАБОТЧИК КНОПКИ "РАСХОДНИКИ" -> ОТКРЫВАЕТ ПОЯС
@router.callback_query(
    BotState.inventory,
    InventoryCallback.filter((F.section == "consumable") & (F.level == 1) & (F.action != "open_slot_filler")),
)
async def inventory_belt_view_handler(
    call: CallbackQuery,
    callback_data: InventoryCallback,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    container: AppContainer,
) -> None:
    user_id = call.from_user.id
    state_data = await state.get_data()
    char_id = state_data.get(FSM_CONTEXT_KEY, {}).get("char_id")

    if not char_id:
        await Err.char_id_not_found_in_fsm(call)
        return

    # Создаем оркестратор через контейнер
    orchestrator = container.get_inventory_bot_orchestrator(session)

    # Получаем обзор пояса
    result_dto = await orchestrator.get_belt_overview(char_id, user_id, state_data)

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


# 2. ОБРАБОТЧИК НАЖАТИЯ НА ЦИФРУ СЛОТА -> ОТКРЫВАЕТ СПИСОК ПРЕДМЕТОВ
@router.callback_query(
    BotState.inventory,
    InventoryCallback.filter(F.action == "open_slot_filler"),
)
async def inventory_fill_slot_handler(
    call: CallbackQuery,
    callback_data: InventoryCallback,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    container: AppContainer,
) -> None:
    user_id = call.from_user.id
    state_data = await state.get_data()
    char_id = state_data.get(FSM_CONTEXT_KEY, {}).get("char_id")

    if not char_id:
        await Err.char_id_not_found_in_fsm(call)
        return

    # Создаем оркестратор через контейнер
    orchestrator = container.get_inventory_bot_orchestrator(session)

    # Мы передали "assign_to_quick_slot_1" в поле filter_type
    target_slot = callback_data.filter_type

    # Теперь открываем ОБЫЧНЫЙ СПИСОК, но с особым filter_type
    result_dto = await orchestrator.get_item_list(
        char_id,
        user_id,
        section="consumable",
        category="all",
        page=callback_data.page,
        state_data=state_data,
        filter_type=target_slot,  # Это важно! UI списка поймет, что мы выбираем предмет для слота
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
