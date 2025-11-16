# app/handlers/callback/login/logout.py
from aiogram.filters import StateFilter
from loguru import logger as log
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.resources.fsm_states.states import FSM_CONTEX_CHARACTER_STATUS
# 1. --- (ТЕПЕРЬ НУЖЕН ТОЛЬКО ОДИН КОЛБЭК) ---
from app.resources.keyboards.callback_data import LobbySelectionCallback
from app.resources.texts.ui_messages import START_GREETING
from app.resources.keyboards.inline_kb.loggin_und_new_character import get_start_adventure_kb
from app.services.ui_service.base_service import BaseUIService

# (FSM импорты не нужны, так как он ловит ВСЕ состояния)

router = Router(name="logout_router")


@router.callback_query(LobbySelectionCallback.filter(F.action == "logout"),
                       StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def global_logout_handler(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Глобальный обработчик выхода из мира (Logout).
    Срабатывает из ЛЮБОГО FSM-состояния.
    """
    log.info(f"User {call.from_user.id} нажал [Выйти из мира]. Глобальный сброс.")
    await call.answer("Возвращаемся в главное меню...")

    # 1. Получаем данные о сообщениях ДО очистки
    state_data = await state.get_data()
    message_menu = state_data.get("message_menu")

    # 2. Полностью очищаем FSM
    await state.clear()

    # 3. Восстанавливаем ВЕРХНЕЕ сообщение (message_menu)
    if message_menu and message_menu.get("chat_id"):
        try:
            await bot.edit_message_text(
                chat_id=message_menu.get("chat_id"),
                message_id=message_menu.get("message_id"),
                text=START_GREETING.format(first_name=call.from_user.first_name),
                reply_markup=get_start_adventure_kb()
            )
        except Exception as e:
            log.warning(f"Не удалось отредактировать message_menu при logout: {e}")
            # (Если не вышло, отправим новое сообщение ниже)
            message_menu = None  # Сбрасываем, чтобы отправить новое

    # Если message_menu не было или его не удалось отредактировать
    if not message_menu:
        try:
            # Отправляем новое стартовое сообщение
            mes = await call.bot.send_message(  # Используем call.bot
                chat_id=call.message.chat.id,
                text=START_GREETING.format(first_name=call.from_user.first_name),
                reply_markup=get_start_adventure_kb()
            )
            message_menu = {"message_id": mes.message_id, "chat_id": mes.chat.id}
        except Exception as e:
            log.error(f"Не удалось отправить новое меню при logout: {e}")

    # 4. Удаляем НИЖНЕЕ сообщение (message_content), если оно было
    ui_service = BaseUIService(char_id=0, state_data=state_data)
    message_content_data = ui_service.get_message_content_data()

    if message_content_data:
        # Убедимся, что не пытаемся удалить то же самое сообщение
        if not (message_menu and message_content_data[1] == message_menu.get("message_id")):
            try:
                await bot.delete_message(chat_id=message_content_data[0], message_id=message_content_data[1])
                log.debug(f"Message_content {message_content_data[1]} удалено при logout.")
            except Exception as e:
                log.warning(f"Не удалось удалить message_content {message_content_data[1]} при logout: {e}")

    # 5. Сохраняем только message_menu обратно в (теперь уже чистый) FSM
    await state.update_data(message_menu=message_menu)