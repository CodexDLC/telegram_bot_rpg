# apps/bot/handlers/callback/login/lobby_character_selection.py
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.keyboards.callback_data import LobbySelectionCallback
from apps.bot.ui_service.game_director.director import GameDirector
from apps.bot.ui_service.view_sender import ViewSender
from apps.common.core.container import AppContainer

router = Router(name="lobby_selection_router")


@router.callback_query(
    LobbySelectionCallback.filter(F.action.in_({"select", "delete", "delete_yes", "delete_no", "login"}))
)
async def select_or_delete_character_handler(
    call: CallbackQuery,
    callback_data: LobbySelectionCallback,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    container: AppContainer,
) -> None:
    """Обрабатывает выбор, удаление или вход персонажа в лобби."""
    if not call.from_user:
        return

    char_id = callback_data.char_id
    user_id = call.from_user.id
    action = callback_data.action
    log.info(f"Lobby | action={action} user_id={user_id} char_id={char_id}")

    await call.answer()
    state_data = await state.get_data()

    # 1. Инициализация
    director = GameDirector(container, state, session)
    orchestrator = container.get_lobby_bot_orchestrator(session)
    orchestrator.set_director(director)

    view_dto = None

    # 2. Обработка действий
    if action == "select":
        if not char_id:
            return
        # Выбор персонажа -> Показ статуса и галочки
        view_dto = await orchestrator.handle_select_character(call.from_user, char_id)

    elif action == "login":
        if not char_id:
            return
        # Вход в игру -> Редирект
        view_dto = await orchestrator.handle_enter_game(call.from_user, char_id)

    elif action == "delete":
        if not char_id:
            return
        # Запрос удаления -> Показ подтверждения
        view_dto = await orchestrator.handle_delete_request(call.from_user, char_id)

    elif action == "delete_yes":
        if not char_id:
            return
        # Подтверждение -> Удаление и возврат в лобби
        view_dto = await orchestrator.handle_delete_confirm(call.from_user, char_id)

    elif action == "delete_no":
        # Отмена -> Возврат в лобби (сброс выбора)
        view_dto = await orchestrator.process_entry_point(call.from_user)

    # 3. Отправка ответа
    if view_dto:
        sender = ViewSender(bot, state, state_data, user_id)
        await sender.send(view_dto)
