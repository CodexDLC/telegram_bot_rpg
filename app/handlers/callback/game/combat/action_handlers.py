"""
Обработчики основных действий в бою: подтверждение хода, выход, обновление.
"""

import time
from contextlib import suppress
from typing import Any

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import ArenaState, InGame
from app.resources.keyboards.combat_callback import CombatActionCallback
from app.resources.schemas_dto.fsm_state_dto import SessionDataDTO
from app.services.core_service.manager.account_manager import AccountManager
from app.services.core_service.manager.arena_manager import ArenaManager
from app.services.core_service.manager.combat_manager import CombatManager
from app.services.core_service.manager.world_manager import WorldManager
from app.services.game_service.combat.combat_service import CombatService
from app.services.game_service.world.game_world_service import GameWorldService
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.arena_ui_service.arena_ui_service import ArenaUIService
from app.services.ui_service.combat.combat_ui_service import CombatUIService
from app.services.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay
from app.services.ui_service.menu_service import MenuService
from app.services.ui_service.navigation_service import NavigationService

action_router = Router(name="combat_actions")


@action_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action == "leave"))
async def leave_combat_handler(
    call: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    combat_manager: CombatManager,
    account_manager: AccountManager,
    world_manager: WorldManager,
    arena_manager: ArenaManager,
    game_world_service: GameWorldService,
):
    if not call.from_user or not call.message or not call.bot:
        return

    state_data = await state.get_data()
    session_context: dict[str, Any] = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    user_id = call.from_user.id
    session_id = session_context.get("combat_session_id")

    if not char_id or not session_id:
        return

    meta = await combat_manager.get_session_meta(str(session_id))
    mode = meta.get("mode", "world") if meta else "world"
    log.info(f"Combat | action=leave user_id={user_id} char_id={char_id} mode='{mode}'")

    content_text, content_kb = None, None
    if mode == "arena":
        await state.set_state(ArenaState.menu)
        arena_ui = ArenaUIService(char_id, state_data, session, account_manager, arena_manager, combat_manager)
        content_text, content_kb = await arena_ui.view_main_menu()
    else:
        await state.set_state(InGame.navigation)
        nav_service = NavigationService(
            char_id=char_id,
            state_data=state_data,
            account_manager=account_manager,
            world_manager=world_manager,
            game_world_service=game_world_service,
            combat_manager=combat_manager,
        )
        content_text, content_kb = await nav_service.reload_current_ui()

    if msg_menu := session_context.get("message_menu"):
        ms = MenuService(game_stage="in_game", state_data=state_data, session=session, account_manager=account_manager)
        menu_text, menu_kb = await ms.get_data_menu()
        with suppress(TelegramAPIError):
            await call.bot.edit_message_text(
                chat_id=msg_menu["chat_id"],
                message_id=msg_menu["message_id"],
                text=menu_text,
                reply_markup=menu_kb,
                parse_mode="HTML",
            )

    if (msg_content := session_context.get("message_content")) and content_text:
        with suppress(TelegramAPIError):
            await call.bot.edit_message_text(
                chat_id=msg_content["chat_id"],
                message_id=msg_content["message_id"],
                text=content_text,
                reply_markup=content_kb,
                parse_mode="HTML",
            )
    await call.answer()


@action_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action == "submit"))
async def submit_turn_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    combat_manager: CombatManager,
    account_manager: AccountManager,
):
    if not call.from_user or not call.message:
        return

    await call.answer("Ход зафиксирован.")
    state_data = await state.get_data()
    session_context: dict[str, Any] = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    user_id = call.from_user.id
    session_id = str(session_context.get("combat_session_id"))

    if not char_id or not session_id:
        return

    selection: dict[str, list[str]] = state_data.get("combat_selection", {})
    atk_zones = selection.get("atk", [])
    def_zones_raw = selection.get("def", [])
    real_def_zones = def_zones_raw[0].split("_") if def_zones_raw else []

    combat_service = CombatService(session_id, combat_manager, account_manager)
    all_participants = await combat_manager.get_session_participants(session_id)
    target_id = next((int(pid) for pid in all_participants if int(pid) != char_id), None)

    if target_id is None:
        await Err.generic_error(call)
        return

    await combat_service.register_move(
        actor_id=char_id, target_id=target_id, attack_zones=atk_zones or None, block_zones=real_def_zones or None
    )
    await state.update_data(combat_selection={"atk": [], "def": []})

    is_pending_move = await combat_manager.get_pending_move(session_id, char_id, target_id)
    ui_service = CombatUIService(user_id, char_id, session_id, state_data, combat_manager, account_manager)

    if is_pending_move:
        log.info(f"Combat | status=waiting_opponent char_id={char_id} target_id={target_id}")
        wait_text, wait_kb = await ui_service.render_waiting_screen()
        with suppress(TelegramAPIError):
            if msg_content := session_context.get("message_content"):
                await bot.edit_message_text(
                    chat_id=msg_content["chat_id"],
                    message_id=msg_content["message_id"],
                    text=wait_text,
                    reply_markup=wait_kb,
                    parse_mode="HTML",
                )
        session_dto = SessionDataDTO(**session_context)
        anim_service = UIAnimationService(bot, session_dto)

        async def check_turn_done(step: int) -> str | None:
            assert target_id is not None
            still_pending = await combat_manager.get_pending_move(session_id, char_id, target_id)
            if not still_pending:
                return "TurnComplete"
            return None

        result = await anim_service.animate_polling(
            base_text=wait_text, check_func=check_turn_done, steps=10, step_delay=2.0
        )
        if not result:
            return

    await await_min_delay(time.monotonic(), min_delay=0.5)
    text, kb = await ui_service.render_dashboard(current_selection={})
    with suppress(TelegramAPIError):
        if msg_menu := session_context.get("message_menu"):
            log_text, log_kb = await ui_service.render_combat_log(page=0)
            await bot.edit_message_text(
                chat_id=msg_menu["chat_id"],
                message_id=msg_menu["message_id"],
                text=log_text,
                reply_markup=log_kb,
                parse_mode="HTML",
            )
    if msg_content := session_context.get("message_content"):
        with suppress(TelegramAPIError):
            await bot.edit_message_text(
                chat_id=msg_content["chat_id"],
                message_id=msg_content["message_id"],
                text=text,
                reply_markup=kb,
                parse_mode="HTML",
            )


@action_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action == "refresh"))
async def refresh_combat_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    combat_manager: CombatManager,
    account_manager: AccountManager,
):
    if not call.from_user or not call.message:
        return

    state_data = await state.get_data()
    session_context: dict[str, Any] = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    user_id = call.from_user.id
    session_id = str(session_context.get("combat_session_id"))

    if not char_id or not session_id:
        return

    log.debug(f"Combat | action=refresh user_id={user_id}")
    combat_service = CombatService(session_id, combat_manager, account_manager)
    await combat_service.process_turn_updates()
    ui_service = CombatUIService(user_id, char_id, session_id, state_data, combat_manager, account_manager)

    with suppress(TelegramAPIError):
        if msg_menu := session_context.get("message_menu"):
            log_text, log_kb = await ui_service.render_combat_log(page=0)
            await bot.edit_message_text(
                chat_id=msg_menu["chat_id"],
                message_id=msg_menu["message_id"],
                text=log_text,
                reply_markup=log_kb,
                parse_mode="HTML",
            )

    all_participants = await combat_manager.get_session_participants(session_id)
    target_id = next((int(pid) for pid in all_participants if int(pid) != char_id), None)
    is_pending = bool(await combat_manager.get_pending_move(session_id, char_id, target_id)) if target_id else False

    if is_pending:
        text, kb = await ui_service.render_waiting_screen()
    else:
        text, kb = await ui_service.render_dashboard(current_selection={})

    if msg_content := session_context.get("message_content"):
        with suppress(TelegramAPIError):
            await bot.edit_message_text(
                chat_id=msg_content["chat_id"],
                message_id=msg_content["message_id"],
                text=text,
                reply_markup=kb,
                parse_mode="HTML",
            )
    await call.answer("Статус обновлен")
