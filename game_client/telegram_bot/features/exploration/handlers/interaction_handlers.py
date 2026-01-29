# game_client/telegram_bot/features/exploration/handlers/interaction_handlers.py

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, User

from common.schemas.enums import CoreDomain
from game_client.telegram_bot.core.container import BotContainer
from game_client.telegram_bot.features.exploration.resources.keyboards.exploration_callbacks import EncounterCallback
from game_client.telegram_bot.services.animation.animation_service import UIAnimationService
from game_client.telegram_bot.services.director.director import GameDirector
from game_client.telegram_bot.services.sender.view_sender import ViewSender

router = Router(name="exploration_interaction")


# --- 1. Exploration Actions (Polling) ---


@router.callback_query(EncounterCallback.filter(F.action == "search"), StateFilter(CoreDomain.EXPLORATION))
async def on_exploration_search(
    call: CallbackQuery,
    callback_data: EncounterCallback,
    state: FSMContext,
    user: User,
    container: BotContainer,
) -> None:
    """
    Обработка активного поиска (search).
    Запускает анимацию и поллинг.
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

    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)

    # Запускаем анимацию с отложенным запросом (анимация → один запрос)
    fetch_func = orchestrator.get_search_fetcher(char_id, callback_data.action, callback_data.target_id)
    anim_service = UIAnimationService(sender)

    await anim_service.run_delayed_fetch(
        fetch_func=fetch_func, delay=3.0, step_interval=1.0, loading_text="🔍 <b>Поиск...</b>"
    )


# --- 2. Encounter Reactions (Instant) ---


@router.callback_query(
    EncounterCallback.filter(),  # Все остальные actions (attack, inspect, etc.)
    StateFilter(CoreDomain.EXPLORATION),
)
async def on_encounter_reaction(
    call: CallbackQuery,
    callback_data: EncounterCallback,
    state: FSMContext,
    user: User,
    container: BotContainer,
) -> None:
    """
    Обработка реакций (attack, inspect, etc).
    Мгновенный запрос.
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

    # Выполняем действие
    view_dto = await orchestrator.handle_interact(char_id, callback_data.action, callback_data.target_id)

    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)
    await sender.send(view_dto)
