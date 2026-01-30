from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, User
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from src.frontend.telegram_bot.core.container import BotContainer
from src.frontend.telegram_bot.features.combat.resources.keyboards.combat_callback import (
    CombatControlCallback,
    CombatFlowCallback,
    CombatMenuCallback,
)
from src.frontend.telegram_bot.features.combat.system.combat_bot_orchestrator import CombatBotOrchestrator
from src.frontend.telegram_bot.features.combat.system.combat_state_manager import CombatStateManager
from src.frontend.telegram_bot.services.animation.animation_service import UIAnimationService
from src.frontend.telegram_bot.services.director.director import GameDirector
from src.frontend.telegram_bot.services.sender.view_sender import ViewSender
from src.shared.enums.domain_enums import CoreDomain

router = Router(name="combat_handlers")


@router.callback_query(CombatControlCallback.filter(), StateFilter(CoreDomain.COMBAT))
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

    # Получаем HTTP клиент из нового контейнера
    client = container.combat
    orchestrator = CombatBotOrchestrator(client)

    # Директору сессия нужна для навигации (SystemDispatcher)
    director = GameDirector(container, state)
    orchestrator.set_director(director)

    manager = CombatStateManager(state)

    view_dto = await orchestrator.handle_control_event(user, callback_data, manager)

    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)
    await sender.send(view_dto)


@router.callback_query(CombatMenuCallback.filter(), StateFilter(CoreDomain.COMBAT))
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

    client = container.combat
    orchestrator = CombatBotOrchestrator(client)

    director = GameDirector(container, state)
    orchestrator.set_director(director)

    view_dto = await orchestrator.handle_menu_event(user, callback_data)

    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)
    await sender.send(view_dto)


@router.callback_query(CombatFlowCallback.filter(), StateFilter(CoreDomain.COMBAT))
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

    client = container.combat
    orchestrator = CombatBotOrchestrator(client)

    director = GameDirector(container, state)
    orchestrator.set_director(director)

    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)

    # Получаем поллер из оркестратора
    poller = orchestrator.get_submit_poller(user, callback_data)

    # Запускаем анимацию
    anim_service = UIAnimationService(sender)

    await anim_service.run_polling_loop(
        check_func=poller, timeout=60.0, step_interval=2.0, loading_text="⏳ <b>Ожидание хода</b>"
    )
