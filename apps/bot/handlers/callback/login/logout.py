from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log

from apps.bot.resources.keyboards.callback_data import LobbySelectionCallback
from apps.bot.resources.texts.ui_messages import START_GREETING
from apps.bot.ui_service.base_service import BaseUIService
from apps.bot.ui_service.command_service import CommandService
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY, fsm_store
from apps.common.schemas_dto import SessionDataDTO

router = Router(name="logout_router")


@router.callback_query(LobbySelectionCallback.filter(F.action == "logout"))
async def global_logout_handler(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Глобальный обработчик выхода из мира (Logout).
    Сбрасывает FSM и возвращает пользователя в главное меню.
    """
    if not call.from_user:
        return

    user_id = call.from_user.id
    log.info(f"Logout | event=global_logout user_id={user_id}")
    await call.answer("Возвращаемся в главное меню...")

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_menu = session_context.get("message_menu")

    await state.set_state(None)

    # Используем CommandService для получения клавиатуры
    com_service = CommandService(call.from_user)
    start_kb = com_service.get_start_menu_kb()

    if message_menu and isinstance(message_menu, dict) and message_menu.get("chat_id"):
        try:
            await bot.edit_message_text(
                chat_id=message_menu.get("chat_id"),
                message_id=message_menu.get("message_id"),
                text=START_GREETING.format(first_name=call.from_user.first_name),
                reply_markup=start_kb,
            )
        except TelegramAPIError as e:
            log.warning(f"Logout | action=edit_menu status=failed user_id={user_id} error='{e}'")
            message_menu = None

    if not message_menu:
        try:
            if call.message:
                mes = await bot.send_message(
                    chat_id=call.message.chat.id,
                    text=START_GREETING.format(first_name=call.from_user.first_name),
                    reply_markup=start_kb,
                )
                message_menu = {"message_id": mes.message_id, "chat_id": mes.chat.id}
        except TelegramAPIError:
            log.error(f"Logout | action=send_new_menu status=failed user_id={user_id}", exc_info=True)

    ui_service = BaseUIService(state_data=state_data)
    message_content_data = ui_service.get_message_content_data()

    if (
        message_content_data
        and isinstance(message_menu, dict)
        and message_content_data[1] != message_menu.get("message_id")
    ):
        try:
            await bot.delete_message(chat_id=message_content_data[0], message_id=message_content_data[1])
            log.debug(f"Logout | action=delete_content_message user_id={user_id} msg_id={message_content_data[1]}")
        except TelegramAPIError as e:
            log.warning(
                f"Logout | action=delete_content_message status=failed user_id={user_id} msg_id={message_content_data[1]} error='{e}'"
            )

    clean_session = SessionDataDTO(
        user_id=user_id,
        message_menu=message_menu,
        char_id=None,
        message_content=None,
    )

    await state.set_data({FSM_CONTEXT_KEY: await fsm_store(clean_session)})
    log.info(f"FSM | action=clear_and_reset reason=logout user_id={user_id}")
