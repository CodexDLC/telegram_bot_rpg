# app/handlers/callback/login/logout.py
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log

# 1. --- (ТЕПЕРЬ НУЖЕН ТОЛЬКО ОДИН КОЛБЭК) ---
from app.resources.keyboards.callback_data import LobbySelectionCallback
from app.resources.keyboards.inline_kb.loggin_und_new_character import get_start_adventure_kb
from app.resources.schemas_dto.fsm_state_dto import SessionDataDTO
from app.resources.texts.ui_messages import START_GREETING
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY, fsm_store
from app.services.ui_service.base_service import BaseUIService

# (FSM импорты не нужны, так как он ловит ВСЕ состояния)

router = Router(name="logout_router")


@router.callback_query(LobbySelectionCallback.filter(F.action == "logout"))
async def global_logout_handler(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Глобальный обработчик выхода из мира (Logout).
    Срабатывает из ЛЮБОГО FSM-состояния.
    """
    if not call.from_user:
        return
    log.info(f"User {call.from_user.id} нажал [Выйти из мира]. Глобальный сброс.")
    await call.answer("Возвращаемся в главное меню...")

    # 1. Получаем данные о сообщениях ДО очистки
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_menu = session_context.get("message_menu")

    # 2. Сбрасываем FSM state
    await state.set_state(None)

    # 3. Восстанавливаем ВЕРХНЕЕ сообщение (message_menu)
    if message_menu and isinstance(message_menu, dict) and message_menu.get("chat_id"):
        try:
            await bot.edit_message_text(
                chat_id=message_menu.get("chat_id"),
                message_id=message_menu.get("message_id"),
                text=START_GREETING.format(first_name=call.from_user.first_name),
                reply_markup=get_start_adventure_kb(),
            )
        except TelegramAPIError as e:
            log.warning(f"Не удалось отредактировать message_menu при logout: {e}")
            message_menu = None

    # Если message_menu не было или его не удалось отредактировать
    if not message_menu:
        try:
            if call.message:
                mes = await bot.send_message(
                    chat_id=call.message.chat.id,
                    text=START_GREETING.format(first_name=call.from_user.first_name),
                    reply_markup=get_start_adventure_kb(),
                )
                message_menu = {"message_id": mes.message_id, "chat_id": mes.chat.id}
        except TelegramAPIError as e:
            log.error(f"Не удалось отправить новое меню при logout: {e}")

        # 4. Удаляем НИЖНЕЕ сообщение (message_content), если оно было
    ui_service = BaseUIService(state_data=state_data)
    message_content_data = ui_service.get_message_content_data()

    if (
        message_content_data
        and isinstance(message_menu, dict)
        and message_content_data[1] != message_menu.get("message_id")
    ):
        try:
            await bot.delete_message(chat_id=message_content_data[0], message_id=message_content_data[1])
            log.debug(f"Message_content {message_content_data[1]} удалено при logout.")
        except TelegramAPIError as e:
            log.warning(f"Не удалось удалить message_content {message_content_data[1]} при logout: {e}")

        # 5. Сохраняем только необходимое ядро в FSM, перезаписывая все старые данные
        # ИСПРАВЛЕНИЕ: Логика вынесена из 'if message_menu', чтобы гарантировать очистку FSM.
    clean_session = SessionDataDTO(
        user_id=call.from_user.id,
        # message_menu может быть None, если редактирование/отправка нового меню не удалась
        message_menu=message_menu,
        char_id=None,
        message_content=None,
    )

    # state.set_data полностью перезаписывает ВЕСЬ FSM новым, чистым DTO.
    await state.set_data({FSM_CONTEXT_KEY: await fsm_store(clean_session)})
