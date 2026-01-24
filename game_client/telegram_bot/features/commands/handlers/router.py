import contextlib

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log

from game_client.bot.resources.keyboards.reply_kb import RESTART_BUTTON_TEXT, SETTINGS_BUTTON_TEXT
from game_client.telegram_bot.common.resources.formatters import MessageInfoFormatter
from game_client.telegram_bot.common.ui.view_sender import ViewSender
from game_client.telegram_bot.core.container import BotContainer
from game_client.telegram_bot.features.commands.system.orchestrator import StartBotOrchestrator
from game_client.telegram_bot.features.commands.system.ui import StartUI

router = Router(name="commands_router")


@router.message(Command("start"))
async def cmd_start(m: Message, state: FSMContext, bot: Bot, container: BotContainer) -> None:
    if not m.from_user:
        return

    user_id = m.from_user.id

    # 1. SNAPSHOT: Запоминаем старые данные, пока не очистили
    old_state_data = await state.get_data()

    # 2. CLEANUP: Полный сброс FSM
    await state.clear()

    # Удаляем команду /start
    with contextlib.suppress(Exception):
        await m.delete()

    # 3. LOGIC
    # Используем новый контейнер для AuthClient
    # TODO: Добавить auth_client в BotContainer
    # auth_client = container.auth
    # Пока заглушка, так как мы еще не добавили auth в контейнер
    auth_client = None

    # ВАЖНО: Сейчас код упадет, если auth_client=None.
    # Нужно обновить BotContainer, добавив туда AuthClient.
    # Но пока я пишу код, предполагая, что он там будет.
    if hasattr(container, "auth"):
        auth_client = container.auth
    else:
        # Fallback: создаем на лету (не рекомендуется, но чтобы работало пока)
        from game_client.telegram_bot.features.commands.client import AuthClient

        auth_client = AuthClient(
            base_url=container.settings.backend_api_url, api_key=container.settings.backend_api_key
        )

    ui_service = StartUI()
    orchestrator = StartBotOrchestrator(auth_client, ui_service, m.from_user)

    view_dto = await orchestrator.handle_start()

    # 4. RENDER
    sender = ViewSender(bot, state, old_state_data, user_id)
    await sender.send(view_dto)


@router.message(F.text == RESTART_BUTTON_TEXT)
async def handle_restart_button(m: Message, state: FSMContext, bot: Bot, container: BotContainer) -> None:
    """Рестарт = тот же /start"""
    await cmd_start(m, state, bot, container)


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
