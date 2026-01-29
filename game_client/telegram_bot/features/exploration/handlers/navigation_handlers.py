from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, User

from common.schemas.enums import CoreDomain
from game_client.telegram_bot.core.container import BotContainer
from game_client.telegram_bot.features.exploration.resources.keyboards.exploration_callbacks import NavigationCallback
from game_client.telegram_bot.resources.states import BotState
from game_client.telegram_bot.services.animation.animation_service import UIAnimationService
from game_client.telegram_bot.services.director.director import GameDirector
from game_client.telegram_bot.services.sender.view_sender import ViewSender

router = Router(name="navigation_handler_router")


@router.callback_query(
    NavigationCallback.filter(F.action == "move"), StateFilter(BotState.exploration, CoreDomain.EXPLORATION)
)
async def on_move_action(
    call: CallbackQuery,
    callback_data: NavigationCallback,
    state: FSMContext,
    user: User,
    container: BotContainer,
) -> None:
    """
    Обработчик перемещения (Polling).
    """
    await call.answer()

    if not call.bot:
        return

    # 1. Получаем оркестратор
    orchestrator = container.get_navigation_orchestrator()

    # 2. Инициализируем Director
    director = GameDirector(container, state)
    orchestrator.set_director(director)

    char_id = await director.get_char_id()
    if not char_id:
        return

    # 3. Получаем данные из callback_data
    target_id = callback_data.target_id
    duration = callback_data.duration

    if not target_id:
        return

    # 4. Получаем poller
    poller = orchestrator.get_move_poller(char_id, target_id, duration, state)

    # 5. Запускаем анимацию
    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)
    anim_service = UIAnimationService(sender)

    await anim_service.run_timed_polling(
        check_func=poller,
        duration=duration,
        step_interval=1.0,
        loading_text="🚶 <b>Перемещение...</b>",
    )


@router.callback_query(
    NavigationCallback.filter(F.action == "look_around"), StateFilter(BotState.exploration, CoreDomain.EXPLORATION)
)
async def on_look_around_action(
    call: CallbackQuery,
    callback_data: NavigationCallback,
    state: FSMContext,
    user: User,
    container: BotContainer,
) -> None:
    """
    Обработчик обзора.
    """
    await call.answer()

    if not call.bot:
        return

    orchestrator = container.get_navigation_orchestrator()
    director = GameDirector(container, state)
    orchestrator.set_director(director)

    char_id = await director.get_char_id()
    if not char_id:
        return

    view = await orchestrator.handle_look_around(char_id)

    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)
    await sender.send(view)
