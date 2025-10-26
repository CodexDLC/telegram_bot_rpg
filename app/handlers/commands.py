# app/handlers/commands.py
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.resources.keyboards.inline_kb.loggin_und_new_character import get_start_adventure_kb
from app.resources.models.user_dto import UserUpsertDTO
from app.resources.texts.ui_messages import START_GREETING
from database.db import get_db_connection
from database.repositories import get_user_repo

log = logging.getLogger(__name__)

router = Router(name="commands_router")


@router.message(Command("start"))
async def cmd_start(m: Message)-> None:
    log.info("Команда /start")
    # 1. Мы не можем продолжать, если нет message.from_user
    if not m.from_user:
        return

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


@router.message(Command("setting"))
async def cmd_setting(m: Message)->None:
    pass


@router.message(Command("help"))
async def cmd_help(m: Message)->None:
    pass


@router.message(Command("game_menu"))
async def cmd_game_menu(m: Message)->None:
    pass