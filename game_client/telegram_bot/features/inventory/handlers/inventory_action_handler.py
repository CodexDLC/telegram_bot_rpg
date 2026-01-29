from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from game_client.telegram_bot.core.container import BotContainer
from game_client.telegram_bot.features.inventory.resources.keyboards.callbacks import InventoryActionCB
from game_client.telegram_bot.services.director.director import GameDirector
from game_client.telegram_bot.services.sender.view_sender import ViewSender

router = Router()


@router.callback_query(InventoryActionCB.filter())
async def handle_inventory_action(
    call: CallbackQuery, callback_data: InventoryActionCB, state: FSMContext, container: BotContainer
):
    if not call.bot:
        return

    # 1. Сборка контекста
    director = GameDirector(container, state)
    orchestrator = container.inventory_orchestrator()
    orchestrator.set_director(director)

    # 2. Вызов логики
    view_dto = await orchestrator.handle_action_request(callback_data)

    # 3. Рендеринг
    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=call.from_user.id)
    await sender.send(view_dto)
