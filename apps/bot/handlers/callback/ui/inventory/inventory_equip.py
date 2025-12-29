from typing import Any

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import BotState
from apps.bot.resources.keyboards.inventory_callback import InventoryCallback

# from apps.common.core.container import AppContainer

router = Router(name="inventory_equip_router")


@router.callback_query(
    BotState.inventory,
    InventoryCallback.filter(),  # Ловим ВСЕ уровни и действия
)
async def inventory_equip_handler(
    call: CallbackQuery,
    callback_data: InventoryCallback,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    container: Any,  # AppContainer
) -> None:
    pass
