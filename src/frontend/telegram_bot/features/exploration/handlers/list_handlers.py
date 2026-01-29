# frontend/telegram_bot/features/exploration/handlers/list_handlers.py

from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, User

from src.frontend.telegram_bot.core.container import BotContainer
from src.frontend.telegram_bot.features.exploration.resources.keyboards.exploration_callbacks import (
    ExplorationListCallback,
)
from src.frontend.telegram_bot.services.director.director import GameDirector
from src.frontend.telegram_bot.services.sender.view_sender import ViewSender
from src.shared.enums.domain_enums import CoreDomain

router = Router(name="exploration_list")


@router.callback_query(ExplorationListCallback.filter(), StateFilter(CoreDomain.EXPLORATION))
async def on_list_action(
    call: CallbackQuery,
    callback_data: ExplorationListCallback,
    state: FSMContext,
    user: User,
    container: BotContainer,
) -> None:
    """
    Обработка списков (пагинация, выбор элемента).
    """
    await call.answer()

    if not call.bot:
        return

    director = GameDirector(container, state)
    orchestrator = container.get_interaction_orchestrator()
    orchestrator.set_director(director)

    char_id = await director.get_char_id()
    if not char_id:
        return

    # Используем handle_list_action из InteractionOrchestrator
    view_dto = await orchestrator.handle_list_action(
        char_id=char_id, action=callback_data.action, item_id=callback_data.item_id, page=callback_data.page or 1
    )

    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)
    await sender.send(view_dto)
