from aiogram import F, Router
from aiogram.types import CallbackQuery
from loguru import logger as log

router = Router(name="arena_tournament_router")


# TODO: Реализовать логику для турниров на арене.
@router.callback_query(F.data == "arena_tournament_placeholder")
async def tournament_handler_placeholder(call: CallbackQuery) -> None:
    """Заглушка для обработки турниров."""
    if not call.from_user:
        return
    user_id = call.from_user.id
    log.info(f"Arena | event=placeholder_triggered user_id={user_id} type=tournament")
    await call.answer("Турниры (в разработке)", show_alert=True)
