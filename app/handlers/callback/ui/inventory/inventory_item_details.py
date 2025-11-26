# app/handlers/callback/ui/inventory/inventory_item_details.py
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import InGame
from app.resources.keyboards.inventory_callback import InventoryCallback
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.inventory.inventory_ui_service import InventoryUIService

router = Router(name="inventory_details_router")


# Ловим ВСЕ действия уровня 2 (Просмотр, Надеть, Снять, Выбросить)
@router.callback_query(
    InGame.inventory,
    InventoryCallback.filter(F.level == 2),
)
async def inventory_item_actions_handler(
    call: CallbackQuery,
    callback_data: InventoryCallback,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    # 1. Security
    if call.from_user.id != callback_data.user_id:
        await Err.access_denied(call)
        return

    # 2. Init
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    user_id = session_context.get("user_id") or call.from_user.id
    char_id = session_context.get("char_id")

    if not char_id:
        await Err.char_id_not_found_in_fsm(call)
        return

    service = InventoryUIService(char_id=char_id, user_id=user_id, session=session, state_data=state_data)

    item_id = callback_data.item_id
    action = callback_data.action

    # --- ЛОГИКА ДЕЙСТВИЙ ---

    if action == "view":
        # Просто просмотр - ничего не делаем, идем к рендеру
        pass

    elif action == "equip":
        # Вызываем бизнес-логику (GameService внутри UIService)
        success, msg = await service.inventory_service.equip_item(item_id)
        if success:
            await call.answer(f"⚔️ {msg}")
        else:
            await call.answer(f"🚫 {msg}", show_alert=True)
            return  # Не обновляем UI, если ошибка (хотя можно и обновить)

    elif action == "unequip":
        success, msg = await service.inventory_service.unequip_item(item_id)
        if success:
            await call.answer(f"🎒 {msg}")
        else:
            await call.answer(f"🚫 {msg}", show_alert=True)

    elif action == "drop":
        # Тут можно добавить подтверждение (Level 3), но пока удаляем сразу
        success = await service.inventory_service.drop_item(item_id)
        if success:
            await call.answer("🗑 Предмет выброшен.")
            # После удаления предмета его ID больше не существует.
            # Возвращаемся в список (Level 1)
            text, kb = await service.render_item_list("equip", "all", 0)
            # ... (код рендера списка, см. ниже) ...
            # Для простоты сделаем return и вызовем рендер списка прямо здесь
            message_data = service.get_message_content_data()
            if message_data:
                await bot.edit_message_text(
                    chat_id=message_data[0], message_id=message_data[1], text=text, reply_markup=kb, parse_mode="HTML"
                )
            return
        else:
            await call.answer("Не удалось выбросить.", show_alert=True)

    # --- РЕНДЕР КАРТОЧКИ (Для view, equip, unequip) ---
    # После действия (надел/снял) мы перерисовываем карточку,
    # чтобы обновились кнопки (Надеть -> Снять) и статы сравнения.

    text, kb = await service.render_item_details(item_id)

    message_data = service.get_message_content_data()
    if not message_data:
        await Err.generic_error(call)
        return

    # Используем try-except, так как если текст не изменился (при view), телеграм кинет ошибку
    try:
        await bot.edit_message_text(
            chat_id=message_data[0], message_id=message_data[1], text=text, reply_markup=kb, parse_mode="HTML"
        )
    except TelegramBadRequest:
        # Игнорируем ошибку "message is not modified", если юзер спамит кликами
        await call.answer()
