# apps/bot/handlers/callback/login/logout.py
from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from game_client.bot.bot_container import BotContainer
from game_client.bot.resources.keyboards.callback_data import SystemCallback
from game_client.bot.ui_service.command.command_bot_orchestrator import CommandBotOrchestrator
from game_client.bot.ui_service.command.command_ui_service import CommandUIService
from game_client.bot.ui_service.game_director.director import GameDirector
from game_client.bot.ui_service.view_sender import ViewSender

router = Router(name="logout_router")


@router.callback_query(StateFilter("*"), SystemCallback.filter(F.action == "logout"))
async def global_logout_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    bot_container: BotContainer,
) -> None:
    """
    Глобальный обработчик выхода из мира (Logout).
    Работает в любом состоянии FSM.
    """
    if not call.from_user:
        return

    user_id = call.from_user.id
    log.info(f"Logout | event=global_logout user_id={user_id}")
    await call.answer("Возвращаемся в главное меню...")

    # 1. Инициализация
    state_data = await state.get_data()

    # Используем новый контейнер
    auth_client = bot_container.get_auth_client()
    ui_service = CommandUIService()
    orchestrator = CommandBotOrchestrator(auth_client, ui_service, call.from_user)

    director = GameDirector(bot_container, state, session)
    orchestrator.set_director(director)

    # 2. Выполнение действия
    view_dto = await orchestrator.handle_logout()

    # 3. Отправка ответа
    sender = ViewSender(bot, state, state_data, user_id)
    await sender.send(view_dto)
