# app/handlers/callback/ui/inventory/inventory_item_details.py

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import InGame
from apps.bot.resources.keyboards.inventory_callback import InventoryCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.core.container import AppContainer

router = Router(name="inventory_item_details")


@router.callback_query(
    InGame.inventory,
    InventoryCallback.filter(F.level == 2),
)
async def inventory_item_details_handler(
    call: CallbackQuery,
    callback_data: InventoryCallback,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    container: AppContainer,
) -> None:
    """Обрабатывает детальный просмотр предмета."""
    user_id = call.from_user.id
    if user_id != callback_data.user_id:
        log.warning(
            f"InventoryDetails | status=access_denied user_id={user_id} callback_user_id={callback_data.user_id}"
        )
        await Err.access_denied(call)
        return

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")

    if not char_id:
        log.error(f"InventoryDetails | status=failed reason='char_id not found in FSM' user_id={user_id}")
        await Err.char_id_not_found_in_fsm(call)
        return

    # TODO: Реализовать обработку действий 'equip' и 'unequip' здесь или в отдельном хендлере.
    # Сейчас InventoryCallback с action='equip' попадает сюда, но get_item_details просто показывает детали заново.
    if callback_data.action in ("equip", "unequip"):
        log.warning(f"InventoryDetails | action='{callback_data.action}' is NOT IMPLEMENTED yet.")
        await call.answer("Функционал экипировки в разработке.", show_alert=True)
        return

    # Создаем оркестратор через контейнер
    orchestrator = container.get_inventory_bot_orchestrator(session)

    # Получаем детали предмета
    result_dto = await orchestrator.get_item_details(
        char_id,
        user_id,
        callback_data.item_id,
        callback_data.category,
        callback_data.page,
        callback_data.filter_type,
        state_data,
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
            f"InventoryDetails | event=details_rendered user_id={user_id} char_id={char_id} item_id={callback_data.item_id}"
        )
    else:
        log.error(f"InventoryDetails | status=failed reason='message_content not found' user_id={user_id}")
        await Err.generic_error(call)


@router.callback_query(
    InGame.inventory,
    InventoryCallback.filter(F.level == 3),
)
async def inventory_quick_slot_handler(
    call: CallbackQuery,
    callback_data: InventoryCallback,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    container: AppContainer,
) -> None:
    """
    Обрабатывает выбор Quick Slot.
    """
    if not call.from_user:
        return

    user_id = call.from_user.id
    state_data = await state.get_data()
    char_id = state_data.get(FSM_CONTEXT_KEY, {}).get("char_id")
    item_id = callback_data.item_id
    action = callback_data.action

    if not char_id:
        await Err.char_id_not_found_in_fsm(call)
        return

    log.info(f"InventoryQuickSlot | event=action user_id={user_id} item_id={item_id} action='{action}'")
    await call.answer()

    # Создаем оркестратор через контейнер
    orchestrator = container.get_inventory_bot_orchestrator(session)

    # --- 1. ACTION: Go to Quick Slot Selection Menu ---
    if action == "bind_quick_slot_menu":
        context_data = {
            "category": callback_data.category,
            "page": callback_data.page,
            "filter_type": callback_data.filter_type,
        }
        result_dto = await orchestrator.get_quick_slot_selection_menu(
            char_id, user_id, item_id, context_data, state_data
        )

        if result_dto.content and (coords := orchestrator.get_content_coords(state_data, user_id)):
            await bot.edit_message_text(
                chat_id=coords.chat_id,
                message_id=coords.message_id,
                text=result_dto.content.text,
                reply_markup=result_dto.content.kb,
                parse_mode="HTML",
            )

    # --- 2. ACTION: Bind/Unbind Item ---
    elif action in ("bind_quick_slot_select", "unbind_quick_slot"):
        slot_key = callback_data.section if action == "bind_quick_slot_select" else None
        action_key = "bind" if action == "bind_quick_slot_select" else "unbind"

        await orchestrator.handle_quick_slot_action(char_id, user_id, item_id, action_key, slot_key, state_data)

        # После действия возвращаемся к деталям предмета
        result_dto = await orchestrator.get_item_details(
            char_id,
            user_id,
            item_id,
            callback_data.category,
            callback_data.page,
            callback_data.filter_type,
            state_data,
        )

        if result_dto.content and (coords := orchestrator.get_content_coords(state_data, user_id)):
            await bot.edit_message_text(
                chat_id=coords.chat_id,
                message_id=coords.message_id,
                text=result_dto.content.text,
                reply_markup=result_dto.content.kb,
                parse_mode="HTML",
            )

        await call.answer("Готово!", show_alert=True)
