import contextlib
import time

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.keyboards.inline_kb.loggin_und_new_character import get_start_adventure_kb
from app.resources.keyboards.reply_kb import RESTART_BUTTON_TEXT, SETTINGS_BUTTON_TEXT
from app.resources.texts.ui_messages import START_GREETING
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.base_service import BaseUIService
from app.services.ui_service.command_service import CommandService
from app.services.ui_service.helpers_ui.message_info_formatter import MessageInfoFormatter
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay

router = Router(name="commands_router")


@router.message(Command("start"))
async def cmd_start(m: Message, state: FSMContext, bot: Bot, session: AsyncSession) -> None:
    """
    Обрабатывает команду /start, сбрасывает состояние и очищает UI.
    """
    if not m.from_user:
        log.warning("Handler 'cmd_start' received update without 'from_user'.")
        return

    user_id = m.from_user.id
    log.info(f"HandlerStart | command=/start user_id={user_id}")
    start_time = time.monotonic()

    try:
        state_data = await state.get_data()
        ui_service = BaseUIService(state_data=state_data)

        menu_data = ui_service.get_message_menu_data()
        if menu_data:
            await bot.delete_message(chat_id=menu_data[0], message_id=menu_data[1])
            log.debug(f"UICleanup | message=menu_message id={menu_data[1]} user_id={user_id}")

        content_data = ui_service.get_message_content_data()
        if content_data:
            await bot.delete_message(chat_id=content_data[0], message_id=content_data[1])
            log.debug(f"UICleanup | message=content_message id={content_data[1]} user_id={user_id}")

    except TelegramAPIError as e:
        log.warning(f"UICleanup | status=failed user_id={user_id} error='{e}'")

    await state.clear()
    log.debug(f"FSM | action=clear user_id={user_id}")

    try:
        com_service = CommandService(m.from_user)
        await com_service.create_user_in_db(session)
        log.debug(f"UserInit | status=success user_id={user_id}")
    except SQLAlchemyError:
        log.error(f"UserInit | status=db_error user_id={user_id}", exc_info=True)
        await m.answer("⚠️ Не удалось подключиться к базе данных.\nПожалуйста, попробуйте снова через несколько минут.")
        await m.answer("...", reply_markup=ReplyKeyboardRemove())
        return

    await await_min_delay(start_time, min_delay=0.5)

    mes = await m.answer(
        START_GREETING.format(first_name=m.from_user.first_name),
        reply_markup=get_start_adventure_kb(),
    )

    message_menu = {"message_id": mes.message_id, "chat_id": mes.chat.id}
    await state.update_data({FSM_CONTEXT_KEY: {"message_menu": message_menu}})
    log.debug(f"FSM | action=update_data user_id={user_id} message_id={mes.message_id}")

    with contextlib.suppress(TelegramAPIError):
        await m.delete()


@router.message(F.text == RESTART_BUTTON_TEXT)
async def handle_restart_button(m: Message, state: FSMContext, bot: Bot, session: AsyncSession) -> None:
    """
    Обрабатывает нажатие Reply-кнопки "Рестарт", вызывая `cmd_start`.
    """
    if not m.from_user:
        return
    log.info(f"HandlerRestart | user_id={m.from_user.id} trigger=reply_button")
    await cmd_start(m, state, bot, session)


@router.message(F.text == SETTINGS_BUTTON_TEXT)
async def handle_settings_button(m: Message) -> None:
    """
    Обрабатывает нажатие Reply-кнопки "Настройки" (заглушка).
    """
    # TODO: Реализовать меню настроек.
    if not m.from_user:
        return
    log.info(f"HandlerStub | user_id={m.from_user.id} name=settings_button")
    with contextlib.suppress(TelegramAPIError):
        await m.delete()
    await m.answer("⚠️ Меню настроек находится в разработке.")


@router.message(Command("setting"))
async def cmd_setting(m: Message) -> None:
    """
    Обрабатывает команду /setting (заглушка).
    """
    # TODO: Реализовать команду /setting.
    if not m.from_user:
        return
    log.info(f"HandlerStub | user_id={m.from_user.id} name=setting_command")
    with contextlib.suppress(TelegramAPIError):
        await m.delete()
    await m.answer("⚠️ Меню настроек находится в разработке.")


@router.message(Command("help"))
async def cmd_help(m: Message) -> None:
    """
    Обрабатывает команду /help (заглушка).
    """
    # TODO: Реализовать команду /help.
    if not m.from_user:
        return
    log.info(f"HandlerStub | user_id={m.from_user.id} name=help_command")
    with contextlib.suppress(TelegramAPIError):
        await m.delete()
    await m.answer("⚠️ Раздел помощи находится в разработке.")


@router.message(Command("get_data_message"))
async def cmd_get_data_message(m: Message) -> None:
    """
    Отправляет полную debug-информацию о сообщении.
    """
    if not m.from_user:
        return
    log.debug(f"DebugCommand | command=get_data_message user_id={m.from_user.id}")
    formatted_info = MessageInfoFormatter.format_full_info(m)
    await m.answer(formatted_info, parse_mode="HTML")


@router.message(Command("get_ids"))
async def cmd_get_ids(m: Message) -> None:
    """
    Отправляет ID пользователя и чата для быстрой отладки.
    """
    if not m.from_user:
        return
    log.debug(f"DebugCommand | command=get_ids user_id={m.from_user.id}")
    formatted_info = MessageInfoFormatter.format_chat_ids_only(m)
    await m.answer(formatted_info, parse_mode="HTML")
