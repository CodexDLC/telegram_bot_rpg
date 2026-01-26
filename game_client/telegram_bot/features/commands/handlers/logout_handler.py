from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, User
from loguru import logger as log

from game_client.telegram_bot.core.container import BotContainer
from game_client.telegram_bot.features.commands.resources.keyboards.commands_callbacks import SystemCallback
from game_client.telegram_bot.features.commands.system.orchestrator import StartBotOrchestrator
from game_client.telegram_bot.features.commands.system.ui import StartUI
from game_client.telegram_bot.services.sender.view_sender import ViewSender

router = Router(name="logout_handler")


@router.callback_query(StateFilter("*"), SystemCallback.filter(F.action == "logout"))
async def on_logout(
    call: CallbackQuery,
    state: FSMContext,
    user: User,
    container: BotContainer,
) -> None:
    """
    Глобальный обработчик выхода (Logout).
    Работает в любом состоянии FSM.
    """
    log.info(f"Logout | user_id={user.id}")
    await call.answer("Возвращаемся в главное меню...")

    if not call.bot:
        return

    # Snapshot state data before clear
    old_state_data = await state.get_data()

    # Clear FSM
    await state.clear()

    # Build orchestrator
    # TODO: use container.auth when available
    from game_client.telegram_bot.features.commands.client import AuthClient

    auth_client = AuthClient(
        base_url=container.settings.backend_api_url,
        api_key=container.settings.backend_api_key,
    )

    ui_service = StartUI()
    orchestrator = StartBotOrchestrator(auth_client, ui_service, user)

    view_dto = await orchestrator.handle_logout()

    sender = ViewSender(bot=call.bot, state=state, state_data=old_state_data, user_id=user.id)
    await sender.send(view_dto)
