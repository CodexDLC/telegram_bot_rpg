# app/handlers/commands.py
import contextlib
import time

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError

from app.resources.keyboards.inline_kb.loggin_und_new_character import get_start_adventure_kb

# Импорты для кнопок
from app.resources.keyboards.reply_kb import RESTART_BUTTON_TEXT, SETTINGS_BUTTON_TEXT
from app.resources.texts.ui_messages import START_GREETING
from app.services.ui_service.base_service import BaseUIService
from app.services.ui_service.command_service import CommandService
from app.services.ui_service.helpers_ui.message_info_formatter import MessageInfoFormatter
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay

router = Router(name="commands_router")


# =================================================================
# --- 1. ОСНОВНОЙ ХЭНДЛЕР (Полная логика) ---
# =================================================================


@router.message(Command("start"))
async def cmd_start(m: Message, state: FSMContext, bot: Bot) -> None:
    """
    Обрабатывает команду /start.
    (Очищает UI, сбрасывает FSM, обрабатывает ошибки БД и запускает меню)
    """
    if not m.from_user:
        log.warning("Хэндлер 'cmd_start' получил обновление без 'from_user'.")
        return

    log.info(f"Хэндлер 'cmd_start' [/start] вызван user_id={m.from_user.id}")
    start_time = time.monotonic()

    # --- (ЛОГИКА ОЧИСТКИ UI) ---
    try:
        state_data = await state.get_data()
        ui_service = BaseUIService(char_id=0, state_data=state_data)

        menu_data = ui_service.get_message_menu_data()
        if menu_data:
            await bot.delete_message(chat_id=menu_data[0], message_id=menu_data[1])
            log.debug(f"Старое message_menu {menu_data[1]} удалено.")

        content_data = ui_service.get_message_content_data()
        if content_data:
            await bot.delete_message(chat_id=content_data[0], message_id=content_data[1])
            log.debug(f"Старое message_content {content_data[1]} удалено.")

    except TelegramAPIError as e:
        log.warning(f"Не удалось удалить старые сообщения при /start: {e}")

    # Полностью очищаем состояние FSM
    await state.clear()
    log.debug(f"Состояние FSM очищено для user_id={m.from_user.id}")

    user = m.from_user

    # --- (БЛОК try...except ДЛЯ БД) ---
    try:
        com_service = CommandService(user)
        await com_service.create_user_in_db()
        log.debug(f"Пользователь {user.id} обработан сервисом CommandService.")
    except SQLAlchemyError as e:
        log.exception(f"Критическая ошибка БД при вызове create_user_in_db для user_id={user.id}: {e}")
        await m.answer("⚠️ Не удалось подключиться к базе данных.\nПожалуйста, попробуйте снова через несколько минут.")
        # (Удаляем Reply-клавиатуру, если она была)
        await m.answer("...", reply_markup=ReplyKeyboardRemove())
        return

    if start_time:
        await await_min_delay(start_time, min_delay=0.5)

    # Отправляем приветственное сообщение и УБИРАЕМ Reply-клавиатуру
    mes = await m.answer(
        START_GREETING.format(first_name=user.first_name),
        reply_markup=get_start_adventure_kb(),
    )

    message_menu = {"message_id": mes.message_id, "chat_id": mes.chat.id}
    await state.update_data(message_menu=message_menu)
    log.debug(f"Состояние FSM обновлено для user_id={m.from_user.id} с message_id={mes.message_id}")

    try:
        await m.delete()
    except TelegramAPIError as e:
        log.warning(f"Не удалось удалить сообщение /start для user_id={user.id}: {e}")


# =================================================================
# --- 2. ХЭНДЛЕРЫ REPLY-КНОПОК (Заглушки и Рестарт) ---
# =================================================================


@router.message(F.text == RESTART_BUTTON_TEXT)
async def handle_restart_button(m: Message, state: FSMContext, bot: Bot) -> None:
    """
    Обрабатывает нажатие Reply-кнопки "Рестарт".
    Просто вызывает /start, который все сделает сам.
    """
    if not m.from_user:
        return
    log.info(f"User {m.from_user.id} нажал Reply-кнопку 'Рестарт'. Вызов cmd_start...")
    # Передаем управление в `cmd_start`
    await cmd_start(m, state, bot)


@router.message(F.text == SETTINGS_BUTTON_TEXT)
async def handle_settings_button(m: Message) -> None:
    """
    ОБРАБАТЫВАЕТ КНОПКУ "Настройки".
    (Заглушка)
    """
    if not m.from_user:
        return
    log.info(f"User {m.from_user.id} нажал Reply-кнопку 'Настройки'. (Заглушка)")
    with contextlib.suppress(TelegramAPIError):
        await m.delete()  # Удаляем сообщение с текстом "⚙️ Настройки"

    await m.answer(
        "⚠️ Меню настроек находится в разработке.",
    )


# =================================================================
# --- 3. ХЭНДЛЕРЫ КОМАНД (Заглушки) ---
# =================================================================


@router.message(Command("setting"))
async def cmd_setting(m: Message) -> None:
    """
    ОБРАБАТЫВАЕТ КОМАНДУ /setting.
    (Заглушка)
    """
    if not m.from_user:
        log.warning("Хэндлер 'cmd_setting' получил обновление без 'from_user'.")
        return

    log.info(f"Хэндлер 'cmd_setting' [/setting] вызван user_id={m.from_user.id}. (Заглушка)")
    with contextlib.suppress(TelegramAPIError):
        await m.delete()

    await m.answer(
        "⚠️ Меню настроек находится в разработке.",
    )


@router.message(Command("help"))
async def cmd_help(m: Message) -> None:
    """
    ОБРАБАТЫВАЕТ КОМАНДУ /help.
    (Заглушка)
    """
    if not m.from_user:
        log.warning("Хэндлер 'cmd_help' получил обновление без 'from_user'.")
        return

    log.info(f"Хэндлер 'cmd_help' [/help] вызван user_id={m.from_user.id}. (Заглушка)")
    with contextlib.suppress(TelegramAPIError):
        await m.delete()

    await m.answer(
        "⚠️ Раздел помощи находится в разработке.",
    )


@router.message(Command("get_data_message"))
async def cmd_get_data_message(m: Message, state: FSMContext, bot: Bot) -> None:
    """Получить полную информацию о сообщении"""
    if not m.from_user:
        await m.answer("⚠️ Не удалось получить информацию о пользователе")
        return

    formatted_info = MessageInfoFormatter.format_full_info(m)
    await m.answer(formatted_info, parse_mode="HTML")


@router.message(Command("get_ids"))
async def cmd_get_ids(m: Message, state: FSMContext, bot: Bot) -> None:
    """Получить только ID (для быстрого копирования)"""
    formatted_info = MessageInfoFormatter.format_chat_ids_only(m)
    await m.answer(formatted_info, parse_mode="HTML")
