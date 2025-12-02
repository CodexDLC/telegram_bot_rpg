from aiogram import F, Router
from aiogram.types import CallbackQuery
from loguru import logger as log

router = Router(name="arena_group_router")


# TODO: Реализовать логику для групповых боев на арене.
@router.callback_query(F.data == "arena_group_placeholder")
async def group_handler_placeholder(call: CallbackQuery) -> None:
    """Заглушка для обработки групповых боев."""
    if not call.from_user:
        return
    user_id = call.from_user.id
    log.info(f"Arena | event=placeholder_triggered user_id={user_id} type=group_battle")
    await call.answer("Групповой бой (в разработке)", show_alert=True)
