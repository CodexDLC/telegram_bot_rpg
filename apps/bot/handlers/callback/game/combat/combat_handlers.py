from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, User
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.bot_container import BotContainer
from apps.bot.resources.keyboards.combat_callback import (
    CombatControlCallback,
    CombatFlowCallback,
    CombatMenuCallback,
)
from apps.bot.ui_service.combat.combat_bot_orchestrator import CombatBotOrchestrator
from apps.bot.ui_service.combat.helpers.combat_state_manager import CombatStateManager
from apps.bot.ui_service.game_director.director import GameDirector
from apps.bot.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from apps.bot.ui_service.view_sender import ViewSender
from apps.common.schemas_dto.game_state_enum import GameState

router = Router(name="combat_handlers")


@router.callback_query(CombatControlCallback.filter(), StateFilter(GameState.COMBAT))
async def on_combat_control(
    call: CallbackQuery,
    callback_data: CombatControlCallback,
    state: FSMContext,
    user: User,
    container: BotContainer,
    session: AsyncSession,
) -> None:
    log.info(f"CombatHandler | user={user.id} action={callback_data.action} layer={callback_data.layer}")
    await call.answer()

    if not call.bot:
        return

    # Получаем клиент без сессии (она не нужна для Redis-операций)
    client = container.get_combat_rbc_client()
    orchestrator = CombatBotOrchestrator(client)

    # Директору сессия нужна для навигации (CoreRouter)
    director = GameDirector(container, state, session)
    orchestrator.set_director(director)

    manager = CombatStateManager(state)

    view_dto = await orchestrator.handle_control_event(user, callback_data, manager)

    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)
    await sender.send(view_dto)


@router.callback_query(CombatMenuCallback.filter(), StateFilter(GameState.COMBAT))
async def on_combat_menu(
    call: CallbackQuery,
    callback_data: CombatMenuCallback,
    state: FSMContext,
    user: User,
    container: BotContainer,
    session: AsyncSession,
) -> None:
    log.info(f"CombatHandler | user={user.id} menu_action={callback_data.action}")
    await call.answer()

    if not call.bot:
        return

    client = container.get_combat_rbc_client()
    orchestrator = CombatBotOrchestrator(client)

    director = GameDirector(container, state, session)
    orchestrator.set_director(director)

    view_dto = await orchestrator.handle_menu_event(user, callback_data)

    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)
    await sender.send(view_dto)


@router.callback_query(CombatFlowCallback.filter(), StateFilter(GameState.COMBAT))
async def on_combat_flow(
    call: CallbackQuery,
    callback_data: CombatFlowCallback,
    state: FSMContext,
    user: User,
    container: BotContainer,
    session: AsyncSession,
) -> None:
    """
    Обработка глобальных действий (Submit, Leave).
    Использует "умную" функцию проверки для анимации (сначала Submit, потом Check).
    """
    log.info(f"CombatHandler | user={user.id} flow_action={callback_data.action}")
    await call.answer()

    if not call.bot:
        return

    client = container.get_combat_rbc_client()
    orchestrator = CombatBotOrchestrator(client)

    director = GameDirector(container, state, session)
    orchestrator.set_director(director)

    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)

    # Получаем поллер из оркестратора
    poller = orchestrator.get_submit_poller(user, callback_data)

    # Запускаем анимацию
    anim_service = UIAnimationService(sender)

    await anim_service.start_combat_polling(check_func=poller, timeout=60, step_delay=2.0)
