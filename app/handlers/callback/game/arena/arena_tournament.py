# app/handlers/callback/game/arena/arena_tournament.py
from aiogram import F, Router
from aiogram.types import CallbackQuery
from loguru import logger as log

router = Router(name="arena_tournament_router")


# --- ЗАГЛУШКА ---
@router.callback_query(F.data == "ignore_tournament_handler")
async def tournament_handler_placeholder(call: CallbackQuery) -> None:
    log.debug(f"Вызван placeholder для турниров. User {call.from_user.id}.")
    await call.answer("Турниры (WIP)", show_alert=True)
