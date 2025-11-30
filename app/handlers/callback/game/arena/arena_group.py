# app/handlers/callback/game/arena/arena_group.py
from aiogram import F, Router
from aiogram.types import CallbackQuery
from loguru import logger as log

router = Router(name="arena_group_router")


# --- ЗАГЛУШКА ---
# (Ловится тем же хендлером, что и 1v1, но мы оставляем файл для будущей логики)
@router.callback_query(F.data == "ignore_group_handler")
async def group_handler_placeholder(call: CallbackQuery) -> None:
    log.debug(f"Вызван placeholder для группового боя. User {call.from_user.id}.")
    await call.answer("Групповой бой (WIP)", show_alert=True)
