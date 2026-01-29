from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, User

from game_client.telegram_bot.core.container import BotContainer
from game_client.telegram_bot.features.arena.resources.keyboards.arena_callback import ArenaCallback
from game_client.telegram_bot.resources.states import BotState
from game_client.telegram_bot.services.animation.animation_service import UIAnimationService
from game_client.telegram_bot.services.director.director import GameDirector
from game_client.telegram_bot.services.sender.view_sender import ViewSender

router = Router(name="arena_handler_router")


@router.callback_query(ArenaCallback.filter(F.action == "join_queue"), StateFilter(BotState.arena))
async def on_join_queue(
    call: CallbackQuery,
    callback_data: ArenaCallback,
    state: FSMContext,
    user: User,
    container: BotContainer,
) -> None:
    """
    Обработчик начала поиска (Polling).
    """
    await call.answer()

    if not call.bot:
        return

    # 1. Получаем оркестратор
    orchestrator = container.arena

    # 2. Инициализируем Director
    director = GameDirector(container, state)
    orchestrator.set_director(director)

    # 3. Получаем poller-функцию из оркестратора
    poller = orchestrator.get_search_poller(user.id, callback_data)

    # 4. Запускаем анимацию
    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)
    anim_service = UIAnimationService(sender)

    await anim_service.run_polling_loop(
        check_func=poller, timeout=60.0, step_interval=3.0, loading_text="⚔️ <b>Поиск противника...</b>"
    )


@router.callback_query(ArenaCallback.filter(F.action != "join_queue"), StateFilter(BotState.arena))
async def handle_arena_action(
    call: CallbackQuery, callback_data: ArenaCallback, state: FSMContext, user: User, container: BotContainer
):
    """
    Обработчик остальных действий Арены.
    """
    await call.answer()

    if not call.bot:
        return

    # 1. Получаем оркестратор из контейнера (Factory Property)
    orchestrator = container.arena

    # 2. Инициализируем Director и связываем с оркестратором
    director = GameDirector(container, state)
    orchestrator.set_director(director)

    # 3. Обрабатываем запрос
    view_result = await orchestrator.handle_request(user.id, callback_data)

    # 4. Отправляем результат через ViewSender
    if view_result:
        state_data = await state.get_data()
        sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)
        await sender.send(view_result)
