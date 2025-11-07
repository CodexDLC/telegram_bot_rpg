# app/handlers/commands.py
import logging
import time

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message


from app.resources.keyboards.inline_kb.loggin_und_new_character import get_start_adventure_kb
from app.resources.texts.ui_messages import START_GREETING
from app.services.ui_service.command_service import CommandService
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay

log = logging.getLogger(__name__)

router = Router(name="commands_router")


@router.message(Command("start"))
async def cmd_start(m: Message, state: FSMContext) -> None:
    """
    Обрабатывает команду /start.

    Эта функция запускается, когда пользователь отправляет команду /start.
    Она очищает предыдущее состояние FSM, регистрирует или находит
    пользователя в базе данных, отправляет приветственное сообщение
    с основной клавиатурой и сохраняет информацию о сообщении в FSM.

    Args:
        m (Message): Входящее сообщение от пользователя.
        state (FSMContext): Состояние FSM для управления данными пользователя.

    Returns:
        None
    """
    # Защитная проверка: мы не можем продолжать, если нет message.from_user.
    if not m.from_user:
        log.warning("Хэндлер 'cmd_start' получил обновление без 'from_user'.")
        return

    log.info(f"Хэндлер 'cmd_start' [/start] вызван user_id={m.from_user.id}")
    start_time = time.monotonic()

    # Полностью очищаем состояние FSM, чтобы избежать проблем
    # от предыдущих "зависших" сессий пользователя.
    await state.clear()
    log.debug(f"Состояние FSM очищено для user_id={m.from_user.id}")

    user = m.from_user

    # Инициализируем сервис для работы с командами,
    # который инкапсулирует логику создания или поиска пользователя.
    com_service = CommandService(user)
    await com_service.create_user_in_db()
    log.debug(f"Пользователь {user.id} обработан сервисом CommandService.")

    # Обеспечиваем минимальную задержку для плавности UI.
    if start_time:
        await await_min_delay(start_time, min_delay=0.5)

    # Отправляем приветственное сообщение и сохраняем его данные.
    # Это сообщение будет служить "главным меню", которое мы будем редактировать.
    mes = await m.answer(
        START_GREETING.format(first_name=user.first_name),
        reply_markup=get_start_adventure_kb())

    message_menu = {
        "message_id": mes.message_id,
        "chat_id": mes.chat.id
    }
    await state.update_data(message_menu=message_menu)
    log.debug(f"Состояние FSM обновлено для user_id={user.id} с message_id={mes.message_id}")

    # Удаляем исходное сообщение /start, чтобы не засорять чат.
    try:
        await m.delete()
    except Exception as e:
        # На всякий случай, если у бота нет прав или сообщение старое.
        log.warning(f"Не удалось удалить сообщение /start для user_id={user.id}: {e}")

    return None


@router.message(Command("setting"))
async def cmd_setting(m: Message) -> None:
    """
    Обрабатывает команду /setting (заглушка).

    Args:
        m (Message): Входящее сообщение от пользователя.

    Returns:
        None
    """
    if not m.from_user:
        log.warning("Хэндлер 'cmd_setting' получил обновление без 'from_user'.")
        return

    log.info(f"Хэндлер 'cmd_setting' [/setting] вызван user_id={m.from_user.id}")
    pass


@router.message(Command("help"))
async def cmd_help(m: Message) -> None:
    """
    Обрабатывает команду /help (заглушка).

    Args:
        m (Message): Входящее сообщение от пользователя.

    Returns:
        None
    """
    if not m.from_user:
        log.warning("Хэндлер 'cmd_help' получил обновление без 'from_user'.")
        return

    log.info(f"Хэндлер 'cmd_help' [/help] вызван user_id={m.from_user.id}")
    pass


@router.message(Command("game_menu"))
async def cmd_game_menu(m: Message) -> None:
    """
    Обрабатывает команду /game_menu (заглушка).

    Args:
        m (Message): Входящее сообщение от пользователя.

    Returns:
        None
    """
    if not m.from_user:
        log.warning("Хэндлер 'cmd_game_menu' получил обновление без 'from_user'.")
        return

    log.info(f"Хэндлер 'cmd_game_menu' [/game_menu] вызван user_id={m.from_user.id}")
    pass
