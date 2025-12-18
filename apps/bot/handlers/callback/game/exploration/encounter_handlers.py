# apps/bot/handlers/callback/game/exploration/encounter_handlers.py
from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log

from apps.bot.resources.keyboards.callback_data import EncounterCallback
from apps.bot.ui_service.exploration.exploration_ui import ExplorationUIService
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.services.core_service.manager.combat_manager import CombatManager

router = Router(name="encounter_handlers_router")


@router.callback_query(EncounterCallback.filter())
async def handle_encounter_action(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    callback_data: EncounterCallback,
    exploration_ui_service: ExplorationUIService,
    combat_manager: CombatManager,
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
        # TODO: Реализовать создание боевой сессии
        # combat_session_id = await combat_manager.create_session(...)
        # await state.set_state(InGame.combat)
        # ... отрисовка UI боя ...
        await call.answer("⚔️ Вы вступаете в бой! (WIP)", show_alert=True)

    elif action == "bypass":
        await call.answer("Вы успешно обошли угрозу.", show_alert=True)
        # Перерисовываем карту, чтобы убрать превью энкаунтера
        actor_name = session_context.get("symbiote_name", "Симбиот")
        text, kb = await exploration_ui_service.render_map(char_id, actor_name)
        await bot.edit_message_text(
            chat_id=message_content["chat_id"],
            message_id=message_content["message_id"],
            text=text,
            reply_markup=kb,
            parse_mode="HTML",
        )

    elif action == "inspect":
        await call.answer("🔍 Вы осматриваете объект... (WIP)", show_alert=True)

    else:
        await call.answer("Неизвестное действие.", show_alert=True)
