import contextlib

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.keyboards.reply_kb import RESTART_BUTTON_TEXT, SETTINGS_BUTTON_TEXT
from apps.bot.ui_service.command_service import CommandService
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY, fsm_store
from apps.bot.ui_service.helpers_ui.formatters.message_info_formatter import MessageInfoFormatter
from apps.common.core.container import AppContainer
from apps.common.schemas_dto import SessionDataDTO

router = Router(name="commands_router")


@router.message(Command("start"))
async def cmd_start(m: Message, state: FSMContext, bot: Bot, session: AsyncSession, container: AppContainer) -> None:
    """
    Обрабатывает команду /start.
    """
    if not m.from_user:
        return

    user_id = m.from_user.id
    log.info(f"HandlerStart | command=/start user_id={user_id}")

    com_service = CommandService(m.from_user)
    auth_client = container.get_auth_client(session)

    try:
        # Сервис готовит почву и возвращает DTO
        view_dto = await com_service.prepare_start(state, bot, auth_client)

        # Хендлер отправляет сообщение
        mes = await m.answer(view_dto.text, reply_markup=view_dto.keyboard)

        # Хендлер обновляет стейт, используя SessionDataDTO
        message_menu = {"message_id": mes.message_id, "chat_id": mes.chat.id}

        session_data = SessionDataDTO(user_id=user_id, message_menu=message_menu)

        # Сериализуем и сохраняем
        await state.update_data({FSM_CONTEXT_KEY: await fsm_store(session_data)})
        log.debug(f"FSM | action=update_data user_id={user_id} message_id={mes.message_id}")

        # Удаляем сообщение с командой /start
        with contextlib.suppress(TelegramAPIError):
            await m.delete()

    except SQLAlchemyError:
        log.error(f"HandlerStart | status=db_error user_id={user_id}", exc_info=True)
        await m.answer("⚠️ Не удалось подключиться к базе данных.\nПожалуйста, попробуйте снова через несколько минут.")
        await m.answer("...", reply_markup=ReplyKeyboardRemove())


@router.callback_query(F.data == "settings")
async def handle_settings_callback(call: CallbackQuery):
    """
    Обрабатывает нажатие Inline-кнопки "Настройки".
    """
    await call.answer("⚠️ Меню настроек находится в разработке.", show_alert=True)


@router.message(F.text == RESTART_BUTTON_TEXT)
async def handle_restart_button(
    m: Message, state: FSMContext, bot: Bot, session: AsyncSession, container: AppContainer
) -> None:
    """
    Обрабатывает нажатие Reply-кнопки "Рестарт", вызывая `cmd_start`.
    """
    if not m.from_user:
        return
    log.info(f"HandlerRestart | user_id={m.from_user.id} trigger=reply_button")
    await cmd_start(m, state, bot, session, container)


@router.message(F.text == SETTINGS_BUTTON_TEXT)
async def handle_settings_button(m: Message) -> None:
    """
    Обрабатывает нажатие Reply-кнопки "Настройки" (заглушка).
    """
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
