from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from game_client.telegram_bot.core.container import BotContainer
from game_client.telegram_bot.features.game_menu.resources.keyboards.menu_callback import MenuCallback
from game_client.telegram_bot.services.director.director import GameDirector
from game_client.telegram_bot.services.sender.view_sender import ViewSender

router = Router()


@router.callback_query(MenuCallback.filter())
async def handle_menu_action(
    call: CallbackQuery,
    callback_data: MenuCallback,
    state: FSMContext,
    container: BotContainer,
):
    if not call.bot or not call.message:
        return

    # 1. Init Director
    director = GameDirector(container, state)

    # 2. Get Orchestrator
    orchestrator = container.menu_orchestrator
    orchestrator.set_director(director)

    # 3. Get User ID
    char_id = await director.get_char_id()
    if not char_id:
        await call.answer("Character not found", show_alert=True)
        return

    # 4. Handle Request
    view_dto = await orchestrator.handle_request(char_id, callback_data)

    # 5. Send View
    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=call.from_user.id)
    await sender.send(view_dto)
