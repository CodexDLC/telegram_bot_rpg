import contextlib

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.keyboards.reply_kb import RESTART_BUTTON_TEXT, SETTINGS_BUTTON_TEXT
from apps.bot.ui_service.command.command_bot_orchestrator import CommandBotOrchestrator
from apps.bot.ui_service.command.command_ui_service import CommandUIService
from apps.bot.ui_service.helpers_ui.formatters.message_info_formatter import MessageInfoFormatter
from apps.bot.ui_service.view_sender import ViewSender
from apps.common.core.container import AppContainer

router = Router(name="commands_router")


@router.message(Command("start"))
async def cmd_start(m: Message, state: FSMContext, bot: Bot, session: AsyncSession, container: AppContainer) -> None:
    if not m.from_user:
        return

    user_id = m.from_user.id

    # 1. SNAPSHOT: Запоминаем старые данные, пока не очистили
    # Это нужно, чтобы ViewSender знал, какие сообщения удалять
    old_state_data = await state.get_data()

    # 2. CLEANUP: Полный сброс FSM
    # Теперь в Redis чисто, бот "забыл" старые диалоги
    await state.clear()

    # Удаляем команду /start
    with contextlib.suppress(Exception):
        await m.delete()

    # 3. LOGIC
    auth_client = container.get_auth_client(session)
    ui_service = CommandUIService()
    orchestrator = CommandBotOrchestrator(auth_client, ui_service, m.from_user)

    view_dto = await orchestrator.handle_start()

    # 4. RENDER
    # Передаем old_state_data в Sender!
    # Sender увидит flag clean_history, использует old_state_data для удаления старых сообщений,
    # а новые ID запишет уже в чистый стейт (так как мы сделали clear выше).
    sender = ViewSender(bot, state, old_state_data, user_id)

    await sender.send(view_dto)


@router.message(F.text == RESTART_BUTTON_TEXT)
async def handle_restart_button(
    m: Message, state: FSMContext, bot: Bot, session: AsyncSession, container: AppContainer
) -> None:
    """Рестарт = тот же /start"""
    await cmd_start(m, state, bot, session, container)


@router.callback_query(F.data == "settings")
async def handle_settings_callback(call: CallbackQuery):
    """
    Обрабатывает нажатие Inline-кнопки "Настройки".
    """
    await call.answer("⚠️ Меню настроек находится в разработке.", show_alert=True)


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
