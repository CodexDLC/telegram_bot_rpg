import asyncio
from typing import Any

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import InGame
from apps.bot.resources.keyboards.callback_data import ScenarioCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.bot.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from apps.bot.ui_service.hub_entry_service import HubEntryService
from apps.common.core.container import AppContainer
from apps.common.schemas_dto import SessionDataDTO

router = Router(name="scenario_handler_router")


@router.callback_query(ScenarioCallback.filter(F.action == "initialize"))
async def scenario_initialize_handler(
    call: CallbackQuery,
    callback_data: ScenarioCallback,
    state: FSMContext,
    bot: Bot,
    container: AppContainer,
    session: AsyncSession,
) -> None:
    """
    Запускает сценарий.
    """
    if not call.from_user:
        return

    user_id = call.from_user.id
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")

    log.info(f"Scenario | event=init user_id={user_id} char_id={char_id} quest='{callback_data.quest_key}'")
    await call.answer()

    if not char_id:
        await Err.char_id_not_found_in_fsm(call)
        return

    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)
    orchestrator = container.get_scenario_bot_orchestrator(session)

    async def run_logic():
        # Оркестратор сам соберет prev_state и prev_loc
        return await orchestrator.initialize_view(char_id, callback_data, state)

    results = await asyncio.gather(
        anim_service.animate_loading(duration=1.0, text="📜 <b>Загрузка сценария...</b>"),
        run_logic(),
    )
    result_dto = results[1]

    if result_dto.content:
        # Переключаем стейт
        await state.set_state(InGame.scenario)

        # Отрисовываем
        if coords := orchestrator.get_content_coords(state_data):
            try:
                await bot.edit_message_text(
                    chat_id=coords.chat_id,
                    message_id=coords.message_id,
                    text=result_dto.content.text,
                    reply_markup=result_dto.content.kb,
                    parse_mode="HTML",
                )
            except TelegramAPIError as e:
                log.error(f"Scenario | status=render_failed error='{e}'")
                await Err.generic_error(call)
        else:
            await Err.message_content_not_found_in_fsm(call)


@router.callback_query(InGame.scenario, ScenarioCallback.filter(F.action == "step"))
async def scenario_step_handler(
    call: CallbackQuery,
    callback_data: ScenarioCallback,
    state: FSMContext,
    bot: Bot,
    container: AppContainer,
    session: AsyncSession,
) -> None:
    """
    Обрабатывает шаг сценария.
    """
    if not call.from_user:
        return

    user_id = call.from_user.id
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")

    log.info(f"Scenario | event=step user_id={user_id} char_id={char_id} action='{callback_data.action_id}'")
    await call.answer()

    orchestrator = container.get_scenario_bot_orchestrator(session)

    # Выполняем шаг
    result_dto = await orchestrator.step_view(char_id, str(callback_data.action_id))

    # Если сценарий закончился (is_terminal=True), запускаем финализацию
    if result_dto.is_terminal:
        await _finalize_scenario_logic(call, state, bot, container, session, char_id, orchestrator)
        return

    # Иначе просто обновляем сообщение
    if result_dto.content and (coords := orchestrator.get_content_coords(state_data)):
        try:
            await bot.edit_message_text(
                chat_id=coords.chat_id,
                message_id=coords.message_id,
                text=result_dto.content.text,
                reply_markup=result_dto.content.kb,
                parse_mode="HTML",
            )
        except TelegramAPIError as e:
            log.error(f"Scenario | status=render_failed error='{e}'")


async def _finalize_scenario_logic(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    container: AppContainer,
    session: AsyncSession,
    char_id: int,
    orchestrator: Any,  # ScenarioBotOrchestrator
) -> None:
    """
    Логика завершения сценария и возврата в мир.
    """
    log.info(f"Scenario | event=finalize char_id={char_id}")

    # 1. Финализируем на бэкенде и получаем данные для возврата
    finalize_result = await orchestrator.finalize_view(char_id)

    if not finalize_result.get("success", False):
        await call.answer("Ошибка завершения сценария", show_alert=True)
        return

    # 2. Восстанавливаем состояние
    next_state = finalize_result.get("next_state")
    target_loc = finalize_result.get("target_location_id")

    await state.set_state(next_state)

    # 3. Отрисовываем экран возврата
    state_data = await state.get_data()
    coords = orchestrator.get_content_coords(state_data)

    if not coords:
        return

    text, kb = None, None

    # Если возвращаемся в Хаб
    if target_loc and "svc_" in target_loc:
        # Нам нужны менеджеры для HubEntryService
        # В идеале HubEntryService должен создаваться через контейнер, но пока так
        hub_service = HubEntryService(
            char_id=char_id,
            target_loc=target_loc,
            state_data=state_data,
            session=session,
            account_manager=container.account_manager,
            arena_manager=container.arena_manager,
            combat_manager=container.combat_manager,
        )
        text, kb, _ = await hub_service.render_hub_menu()

    # Если возвращаемся в Навигацию
    else:
        expl_orc = container.get_exploration_bot_orchestrator(session)
        view = await expl_orc.get_current_view(char_id, state_data)
        if view and view.content:
            text = view.content.text
            kb = view.content.kb

    # Обновляем сообщение
    if text:
        try:
            await bot.edit_message_text(
                chat_id=coords.chat_id,
                message_id=coords.message_id,
                text=text,
                reply_markup=kb,
                parse_mode="HTML",
            )
        except TelegramAPIError as e:
            log.error(f"Scenario | status=finalize_render_failed error='{e}'")
