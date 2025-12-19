# apps/bot/handlers/callback/game/exploration/encounter_handlers.py
from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.core_client.combat_rbc_client import CombatRBCClient
from apps.bot.resources.fsm_states.states import InGame
from apps.bot.resources.keyboards.callback_data import EncounterCallback
from apps.bot.ui_service.combat.combat_bot_orchestrator import CombatBotOrchestrator
from apps.bot.ui_service.combat.combat_ui_service import CombatUIService
from apps.bot.ui_service.exploration.exploration_ui import ExplorationUIService
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.combat_manager import CombatManager

router = Router(name="encounter_handlers_router")


@router.callback_query(EncounterCallback.filter())
async def handle_encounter_action(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    callback_data: EncounterCallback,
    exploration_ui_service: ExplorationUIService,
    combat_manager: CombatManager,
    account_manager: AccountManager,
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
    message_content = session_context.get("message_content")

    if not char_id or not message_content:
        await Err.generic_error(call)
        return

    if action == "attack":
        client = CombatRBCClient(session, account_manager, combat_manager)
        ui_service = CombatUIService(state_data, char_id)
        orchestrator = CombatBotOrchestrator(client, ui_service)

        try:
            enemy_id = int(target_id)
        except (ValueError, TypeError):
            await call.answer("Ошибка ID цели", show_alert=True)
            return

        session_id, new_target_id, text, kb = await orchestrator.start_new_battle(players=[char_id], enemies=[enemy_id])

        await state.set_state(InGame.combat)
        session_context["combat_session_id"] = session_id
        await state.update_data({FSM_CONTEXT_KEY: session_context})

        # Сохраняем target_id в FSM
        if new_target_id is not None:
            await state.update_data(combat_target_id=new_target_id)

        await bot.edit_message_text(
            chat_id=message_content["chat_id"],
            message_id=message_content["message_id"],
            text=text,
            reply_markup=kb,
            parse_mode="HTML",
        )

    elif action == "bypass":
        await call.answer("Вы успешно обошли угрозу.", show_alert=True)
        actor_name = session_context.get("symbiote_name", "Симбиот")
        nav_text, nav_kb = await exploration_ui_service.render_map(char_id, actor_name)
        if nav_kb:
            await bot.edit_message_text(
                chat_id=message_content["chat_id"],
                message_id=message_content["message_id"],
                text=nav_text,
                reply_markup=nav_kb,
                parse_mode="HTML",
            )

    elif action == "inspect":
        await call.answer("🔍 Вы осматриваете объект... (WIP)", show_alert=True)

    else:
        await call.answer("Неизвестное действие.", show_alert=True)
