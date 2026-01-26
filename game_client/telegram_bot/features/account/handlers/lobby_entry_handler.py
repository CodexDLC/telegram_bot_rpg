from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, User

from game_client.telegram_bot.core.container import BotContainer
from game_client.telegram_bot.features.account.resources.keyboards.account_callbacks import LobbyEntryCallback
from game_client.telegram_bot.features.account.system.lobby_orchestrator import LobbyOrchestrator
from game_client.telegram_bot.services.director.director import GameDirector
from game_client.telegram_bot.services.sender.view_sender import ViewSender

router = Router(name="lobby_entry_handler")


@router.callback_query(LobbyEntryCallback.filter())
async def on_lobby_entry(
    call: CallbackQuery,
    state: FSMContext,
    user: User,
    container: BotContainer,
) -> None:
    await call.answer()

    if not call.bot:
        return

    client = container.account
    orchestrator = LobbyOrchestrator(client)

    director = GameDirector(container, state)
    orchestrator.set_director(director)

    view_dto = await orchestrator.handle_lobby_initialize(user)

    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)
    await sender.send(view_dto)
