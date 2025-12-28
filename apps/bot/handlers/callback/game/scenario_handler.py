from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.bot_container import BotContainer
from apps.bot.resources.fsm_states.states import BotState
from apps.bot.resources.keyboards.callback_data import ScenarioCallback
from apps.bot.ui_service.game_director.director import GameDirector
from apps.bot.ui_service.view_sender import ViewSender
from apps.common.core.container import AppContainer

router = Router(name="scenario_handler_router")


@router.callback_query(ScenarioCallback.filter(F.action == "initialize"))
async def scenario_initialize_handler(
    call: CallbackQuery,
    callback_data: ScenarioCallback,
    state: FSMContext,
    bot: Bot,
    container: AppContainer,
    bot_container: BotContainer,
    session: AsyncSession,
) -> None:
    """
    Запускает сценарий (вход в режим сценария).
    """
    if not call.from_user:
        return

    user_id = call.from_user.id
    log.info(f"Scenario | event=init user_id={user_id} quest='{callback_data.quest_key}'")
    await call.answer()

    # 1. Инициализация UI компонентов
    state_data = await state.get_data()
    # Передаем bot_container в Director
    director = GameDirector(container=bot_container, state=state, session=session)

    orchestrator = bot_container.get_scenario_bot_orchestrator()
    orchestrator.set_director(director)

    # 2. Запуск логики
    view_dto = await orchestrator.process_entry_point(user=call.from_user, quest_key=str(callback_data.quest_key))

    # 3. Отправка ответа
    if view_dto:
        sender = ViewSender(bot, state, state_data, user_id)
        await sender.send(view_dto)


@router.callback_query(BotState.scenario, ScenarioCallback.filter(F.action == "step"))
async def scenario_step_handler(
    call: CallbackQuery,
    callback_data: ScenarioCallback,
    state: FSMContext,
    bot: Bot,
    container: AppContainer,
    bot_container: BotContainer,
    session: AsyncSession,
) -> None:
    """
    Обрабатывает шаг сценария (выбор опции).
    """
    if not call.from_user:
        return

    user_id = call.from_user.id
    log.info(f"Scenario | event=step user_id={user_id} action='{callback_data.action_id}'")
    await call.answer()

    # 1. Инициализация
    state_data = await state.get_data()
    # Передаем bot_container в Director
    director = GameDirector(container=bot_container, state=state, session=session)

    orchestrator = bot_container.get_scenario_bot_orchestrator()
    orchestrator.set_director(director)

    # 2. Логика шага
    view_dto = await orchestrator.handle_action(user=call.from_user, action_id=str(callback_data.action_id))

    # 3. Отправка
    if view_dto:
        sender = ViewSender(bot, state, state_data, user_id)
        await sender.send(view_dto)
