from typing import Any

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from game_client.bot.resources.keyboards.inventory_callback import InventoryCallback

# from apps.common.core.container import AppContainer

router = Router()


@router.callback_query(InventoryCallback.filter())
async def on_inventory_resource(
    call: CallbackQuery,
    callback_data: InventoryCallback,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    container: Any,  # AppContainer
) -> None:
    await call.answer("Inventory Resource")
