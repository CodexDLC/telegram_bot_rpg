# apps/bot/handlers/callback/login/lobby.py
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.keyboards.callback_data import StartMenuCallback
from apps.bot.ui_service.game_director.director import GameDirector
from apps.bot.ui_service.view_sender import ViewSender
from apps.common.core.container import AppContainer

router = Router(name="login_lobby_router")


@router.callback_query(StartMenuCallback.filter(F.action == "adventure"))
async def start_login_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    container: AppContainer,
) -> None:
    """
    Обрабатывает кнопку "Начать приключение".
    Делегирует управление LobbyBotOrchestrator.
    """
    if not call.from_user:
        return

    user_id = call.from_user.id
    log.info(f"LoginFlow | event=start_adventure user_id={user_id}")
    await call.answer()

    # 1. Инициализация компонентов UI
    state_data = await state.get_data()

    # Создаем Director
    director = GameDirector(container, state, session)

    # Создаем Orchestrator через контейнер
    orchestrator = container.get_lobby_bot_orchestrator(session)
    orchestrator.set_director(director)

    # 2. Запуск логики входа
    view_dto = await orchestrator.process_entry_point(call.from_user)

    # 3. Отправка ответа
    if view_dto:
        sender = ViewSender(bot, state, state_data, user_id)
        await sender.send(view_dto)
