# apps/bot/handlers/callback/game/exploration/encounter_handlers.py
from typing import Any

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from apps.common.core.container import AppContainer
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from game_client.bot.resources.fsm_states.states import BotState
from game_client.bot.resources.keyboards.callback_data import EncounterCallback
from game_client.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from game_client.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY

router = Router(name="encounter_handlers_router")


@router.callback_query(EncounterCallback.filter())
async def handle_encounter_action(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    container: AppContainer,
    callback_data: EncounterCallback,
):
    if not call.from_user:
        return

    user_id = call.from_user.id
    action = callback_data.action
    target_id = callback_data.target_id
    log.info(f"Encounter | action={action} target_id={target_id} user_id={user_id}")

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")

    if not char_id:
        await Err.generic_error(call)
        return

    # Создаем оркестратор навигации
    expl_orchestrator = container.get_exploration_bot_orchestrator(session)

    # Обрабатываем действие через оркестратор
    result_dto = await expl_orchestrator.resolve_encounter(action, target_id, char_id, state_data)

    # Показываем уведомление, если есть
    if result_dto.alert_text:
        await call.answer(result_dto.alert_text, show_alert=False)
    else:
        await call.answer()

    # Если нужно переключить состояние (например, в бой)
    if result_dto.new_state == "InGame.combats":
        if not result_dto.combat_session_id:
            await Err.generic_error(call)
            return

        await state.set_state(BotState.combat)

        # Атомарное обновление FSM
        session_context["combat_session_id"] = result_dto.combat_session_id

        # Явно указываем тип словаря, чтобы избежать ошибки статического анализа
        update_data: dict[str, Any] = {FSM_CONTEXT_KEY: session_context}

        if result_dto.combat_target_id is not None:
            update_data["combat_target_id"] = result_dto.combat_target_id

        await state.update_data(update_data)

        # Для отрисовки боя используем CombatBotOrchestrator
        # combat_orchestrator = container.get_combat_bot_orchestrator(session)

        # Получаем первый кадр боя
        # combat_view = await combat_orchestrator.get_dashboard_view(
        #     result_dto.combat_session_id, char_id, {}, state_data
        # )

        # Обновляем контент (Дашборд)
        # if combat_view.content and (coords := expl_orchestrator.get_content_coords(state_data)):
        #     await bot.edit_message_text(
        #         chat_id=coords.chat_id,
        #         message_id=coords.message_id,
        #         text=combat_view.content.text,
        #         reply_markup=combat_view.content.kb,
        #         parse_mode="HTML",
        #     )

        # Заглушка
        if coords := expl_orchestrator.get_content_coords(state_data):
            await bot.edit_message_text(
                chat_id=coords.chat_id,
                message_id=coords.message_id,
                text="⚔️ <b>Бой начинается!</b>\n(Переход в новую систему боя...)",
                reply_markup=None,
                parse_mode="HTML",
            )

    else:
        # Обычное обновление (например, обход или осмотр)
        if result_dto.content and (coords := expl_orchestrator.get_content_coords(state_data)):
            await bot.edit_message_text(
                chat_id=coords.chat_id,
                message_id=coords.message_id,
                text=result_dto.content.text,
                reply_markup=result_dto.content.kb,
                parse_mode="HTML",
            )
