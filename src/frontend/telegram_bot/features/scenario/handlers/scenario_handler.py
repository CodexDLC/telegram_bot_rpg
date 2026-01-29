from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, User

from src.frontend.telegram_bot.core.container import BotContainer
from src.frontend.telegram_bot.features.scenario.resources.keyboards.scenario_callback import ScenarioCallback
from src.frontend.telegram_bot.features.scenario.system.scenario_bot_orchestrator import ScenarioBotOrchestrator
from src.frontend.telegram_bot.resources.states import BotState
from src.frontend.telegram_bot.services.director.director import GameDirector
from src.frontend.telegram_bot.services.sender.view_sender import ViewSender

router = Router(name="scenario_handler_router")


@router.callback_query(ScenarioCallback.filter(), StateFilter(BotState.scenario))
async def scenario_router_handler(
    call: CallbackQuery,
    callback_data: ScenarioCallback,
    state: FSMContext,
    user: User,
    container: BotContainer,
) -> None:
    """
    Единый хендлер для всех действий сценария.
    Передает управление оркестратору, который сам решает, что делать на основе callback_data.
    """
    await call.answer()

    if not call.bot:
        return

    # 1. Создаем оркестратор
    client = container.scenario
    orchestrator = ScenarioBotOrchestrator(client)

    # 2. Инициализируем директора
    director = GameDirector(container, state)
    orchestrator.set_director(director)

    # 3. Делегируем обработку оркестратору (передаем user_id)
    view_dto = await orchestrator.handle_request(user.id, callback_data)

    # 4. Отправляем результат
    if view_dto:
        state_data = await state.get_data()
        sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)
        await sender.send(view_dto)
