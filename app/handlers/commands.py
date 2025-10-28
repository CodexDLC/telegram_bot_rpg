# app/handlers/commands.py
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.resources.keyboards.inline_kb.loggin_und_new_character import get_start_adventure_kb
from app.resources.models.user_dto import UserUpsertDTO
from app.resources.texts.ui_messages import START_GREETING
from database.db import get_db_connection
from database.repositories import get_user_repo

log = logging.getLogger(__name__)

router = Router(name="commands_router")


@router.message(Command("start"))
async def cmd_start(m: Message, state: FSMContext)-> None:
    log.info("Команда /start")
    # 1. Мы не можем продолжать, если нет message.from_user
    if not m.from_user:
        return None

    current_state = await state.get_state()

    try:
        await m.delete()
    except Exception as e:
        # (На всякий случай, если у бота нет прав или сообщение старое)
        log.warning(f"Не удалось удалить сообщение /start: {e}")

    if current_state is not None:
        #TODO: написать реализацию очистки FSM state если игрок не стадии создания персонажа или Tutorial.
        return None

    await state.clear()

    user = m.from_user

    # 2. "ЗАПЕЧАТЫВАНИЕ" ДАННЫХ В DTO

    user_dto = UserUpsertDTO(
        telegram_id=user.id,
        first_name=user.first_name,
        username=user.username,
        last_name=user.last_name,
        language_code=user.language_code,
        is_premium=bool(user.is_premium)
    )
    # 3. Используем DTO для записи в БД
    async with get_db_connection() as db:
        user_repo = get_user_repo(db)
        await user_repo.upsert_user(user_dto)

    # 4. Отправляем сообщение пользователю
    await m.answer(
        START_GREETING.format(first_name=user.first_name),
        reply_markup=get_start_adventure_kb())
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