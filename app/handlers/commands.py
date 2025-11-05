# app/handlers/commands.py
import logging
import time

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message


from app.resources.keyboards.inline_kb.loggin_und_new_character import get_start_adventure_kb
from app.resources.texts.ui_messages import START_GREETING
from app.services.game_service.command_service import CommandService
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay

log = logging.getLogger(__name__)

router = Router(name="commands_router")


@router.message(Command("start"))
async def cmd_start(m: Message, state: FSMContext)-> None:
    log.info("Команда /start")
    start_time = time.monotonic()

    # Мы не можем продолжать, если нет message.from_user
    if not m.from_user:
        return None
    # Очищаем контекст
    await state.clear()
    # получаем объект Пользователя
    user = m.from_user

    # создаем сервис и вызываем его метод, что бы сохранить в базу пользователя
    com_service = CommandService(user)
    await com_service.create_user_in_db()

    if start_time:
        await await_min_delay(start_time, min_delay=0.5)



    # Отправляем сообщение пользователю и сохраняем сообщение для получения айди чата и сообщения
    mes = await m.answer(
        START_GREETING.format(first_name=user.first_name),
        reply_markup=get_start_adventure_kb())

    message_menu = {
        "message_id": mes.message_id,
        "chat_id": mes.chat.id
    }

    await state.update_data(message_menu=message_menu)

    try:
        await m.delete()
    except Exception as e:
        # На всякий случай, если у бота нет прав или сообщение старое
        log.warning(f"Не удалось удалить сообщение /start: {e}")

    return None



@router.message(Command("setting"))
async def cmd_setting(m: Message)->None:
    pass


@router.message(Command("help"))
async def cmd_help(m: Message)->None:
    pass


@router.message(Command("game_menu"))
async def cmd_game_menu(m: Message)->None:
    pass