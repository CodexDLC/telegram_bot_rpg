import time
from typing import Any

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import ArenaState, InGame
from app.resources.keyboards.combat_callback import (
    CombatActionCallback,
    CombatLogCallback,
    CombatZoneCallback,
)
from app.services.core_service.manager.combat_manager import combat_manager
from app.services.game_service.combat.combat_service import CombatService
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.arena_ui_service.arena_ui_service import ArenaUIService
from app.services.ui_service.combat.combat_ui_service import CombatUIService
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay
from app.services.ui_service.menu_service import MenuService
from app.services.ui_service.navigation_service import NavigationService

router = Router(name="combat_router")


@router.callback_query(InGame.combat, CombatZoneCallback.filter())
async def combat_zone_toggle_handler(call: CallbackQuery, callback_data: CombatZoneCallback, state: FSMContext) -> None:
    """Обрабатывает нажатия на зоны атаки/защиты в бою."""
    if not call.from_user or not isinstance(call.message, Message):
        return

    state_data = await state.get_data()
    session_context: dict[str, Any] = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    user_id = call.from_user.id
    layer, zone_id = callback_data.layer, callback_data.zone_id

    log.info(f"Combat | event=zone_toggle user_id={user_id} char_id={char_id} layer={layer} zone={zone_id}")

    selection: dict[str, list[str]] = state_data.get("combat_selection", {"atk": [], "def": []})
    current_list = selection.get(layer, [])

    if zone_id in current_list:
        current_list.remove(zone_id)
    else:
        if layer == "def":
            current_list.clear()
        current_list.append(zone_id)

    selection[layer] = current_list
    await state.update_data(combat_selection=selection)
    log.debug(f"FSM | data_updated key=combat_selection user_id={user_id} selection='{selection}'")

    session_id = session_context.get("combat_session_id")
    if not session_id or not char_id:
        log.warning(f"Combat | status=failed reason='session_id or char_id missing' user_id={user_id}")
        await Err.generic_error(call)
        return

    ui_service = CombatUIService(user_id, char_id, str(session_id), state_data)
    text, kb = await ui_service.render_dashboard(current_selection=selection)

    try:
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    except TelegramAPIError as e:
        log.warning(f"UIRender | component=combat_dashboard status=failed user_id={user_id} error='{e}'")
    await call.answer()


@router.callback_query(InGame.combat, CombatActionCallback.filter())
async def combat_action_handler(
    call: CallbackQuery, callback_data: CombatActionCallback, state: FSMContext, session: AsyncSession
) -> None:
    """Обрабатывает действия в бою (подтверждение хода, выход, меню)."""
    start_time = time.monotonic()
    if not call.from_user or not call.message or not call.bot:
        return

    action = callback_data.action
    state_data = await state.get_data()
    session_context: dict[str, Any] = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    user_id = call.from_user.id
    session_id = session_context.get("combat_session_id")

    log.info(f"Combat | event=action user_id={user_id} char_id={char_id} action='{action}'")

    if not session_id or not char_id:
        log.warning(f"Combat | status=failed reason='session_id or char_id missing' user_id={user_id}")
        await Err.generic_error(call)
        return

    if action == "leave":
        meta = await combat_manager.get_session_meta(str(session_id))
        mode = meta.get("mode", "world") if meta else "world"
        log.info(f"Combat | action=leave user_id={user_id} char_id={char_id} mode='{mode}'")

        content_text, content_kb = None, None
        if mode == "arena":
            await state.set_state(ArenaState.menu)
            arena_ui = ArenaUIService(char_id, state_data, session)
            content_text, content_kb = await arena_ui.view_main_menu()
        else:
            await state.set_state(InGame.navigation)
            nav_service = NavigationService(char_id, state_data)
            content_text, content_kb = await nav_service.reload_current_ui()

        msg_menu = session_context.get("message_menu")
        if msg_menu:
            ms = MenuService(game_stage="in_game", state_data=state_data, session=session)
            menu_text, menu_kb = await ms.get_data_menu()
            try:
                await call.bot.edit_message_text(
                    chat_id=msg_menu["chat_id"],
                    message_id=msg_menu["message_id"],
                    text=menu_text,
                    reply_markup=menu_kb,
                    parse_mode="HTML",
                )
            except TelegramAPIError as e:
                log.warning(f"UIRender | component=menu status=failed_on_leave user_id={user_id} error='{e}'")

        msg_content = session_context.get("message_content")
        if msg_content and content_text:
            try:
                await call.bot.edit_message_text(
                    chat_id=msg_content["chat_id"],
                    message_id=msg_content["message_id"],
                    text=content_text,
                    reply_markup=content_kb,
                    parse_mode="HTML",
                )
            except TelegramAPIError as e:
                log.warning(f"UIRender | component=content status=failed_on_leave user_id={user_id} error='{e}'")
        await call.answer()
        return

    elif action == "submit":
        await call.answer("Ход принят!")
        selection: dict[str, list[str]] = state_data.get("combat_selection", {})
        atk_zones = selection.get("atk", [])
        def_zones_raw = selection.get("def", [])
        real_def_zones = def_zones_raw[0].split("_") if def_zones_raw else []

        log.debug(f"Combat | action=submit user_id={user_id} atk='{atk_zones}' def='{real_def_zones}'")

        combat_service = CombatService(str(session_id))
        all_participants = await combat_manager.get_session_participants(str(session_id))
        target_id = next((int(pid) for pid in all_participants if int(pid) != char_id), None)

        if target_id is None:
            log.error(f"Combat | status=failed reason='target not found' user_id={user_id} session_id='{session_id}'")
            await Err.generic_error(call)
            return

        await combat_service.register_move(
            actor_id=char_id, target_id=target_id, attack_zones=atk_zones or None, block_zones=real_def_zones or None
        )
        await state.update_data(combat_selection={"atk": [], "def": []})

        ui_service = CombatUIService(user_id, char_id, str(session_id), state_data)
        if msg_menu := session_context.get("message_menu"):
            log_text, log_kb = await ui_service.render_combat_log(page=0)
            try:
                await call.bot.edit_message_text(
                    chat_id=msg_menu["chat_id"],
                    message_id=msg_menu["message_id"],
                    text=log_text,
                    reply_markup=log_kb,
                    parse_mode="HTML",
                )
            except TelegramAPIError as e:
                log.warning(f"UIRender | component=combat_log status=failed user_id={user_id} error='{e}'")

        if msg_content := session_context.get("message_content"):
            try:
                await call.bot.edit_message_text(
                    chat_id=msg_content["chat_id"],
                    message_id=msg_content["message_id"],
                    text="⏳ <b>Ход отправлен...</b>\n<i>Ожидание результата...</i>",
                    parse_mode="HTML",
                    reply_markup=None,
                )
            except TelegramAPIError as e:
                log.warning(f"UIRender | component=combat_wait status=failed user_id={user_id} error='{e}'")

        await await_min_delay(start_time, min_delay=1.5)

        text, kb = await ui_service.render_dashboard(current_selection={})
        if msg_content:
            try:
                await call.bot.edit_message_text(
                    chat_id=msg_content["chat_id"],
                    message_id=msg_content["message_id"],
                    text=text,
                    reply_markup=kb,
                    parse_mode="HTML",
                )
            except TelegramAPIError as e:
                log.warning(
                    f"UIRender | component=combat_dashboard_refresh status=failed user_id={user_id} error='{e}'"
                )

    elif action == "menu":
        # TODO: Реализовать меню действий в бою.
        log.debug(f"Combat | action=menu status=stub user_id={user_id}")
        await call.answer("Меню действий (WIP)")

    elif action == "switch_target":
        # TODO: Реализовать смену цели в бою.
        log.debug(f"Combat | action=switch_target status=stub user_id={user_id}")
        await call.answer("Смена цели (WIP)", show_alert=True)

    elif action == "refresh":
        log.debug(f"Combat | action=refresh user_id={user_id}")
        ui_service = CombatUIService(user_id, char_id, str(session_id), state_data)
        text, kb = await ui_service.render_dashboard(current_selection={})
        if msg_content := session_context.get("message_content"):
            try:
                await call.bot.edit_message_text(
                    chat_id=msg_content["chat_id"],
                    message_id=msg_content["message_id"],
                    text=text,
                    reply_markup=kb,
                    parse_mode="HTML",
                )
            except TelegramAPIError as e:
                log.warning(
                    f"UIRender | component=combat_dashboard_refresh status=failed user_id={user_id} error='{e}'"
                )
        await call.answer("Обновлено")


@router.callback_query(InGame.combat, CombatLogCallback.filter())
async def combat_log_pagination(call: CallbackQuery, callback_data: CombatLogCallback, state: FSMContext) -> None:
    """Обрабатывает пагинацию в логе боя."""
    if not call.from_user or not isinstance(call.message, Message):
        return

    page = callback_data.page
    state_data = await state.get_data()
    session_context: dict[str, Any] = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    user_id = call.from_user.id
    session_id = session_context.get("combat_session_id")

    log.info(f"CombatLog | event=pagination user_id={user_id} char_id={char_id} page={page}")

    if not session_id or not char_id:
        log.warning(f"CombatLog | status=failed reason='session_id or char_id missing' user_id={user_id}")
        await Err.generic_error(call)
        return

    ui_service = CombatUIService(user_id, char_id, str(session_id), state_data)
    text, kb = await ui_service.render_combat_log(page=page)

    try:
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    except TelegramAPIError as e:
        log.warning(f"UIRender | component=combat_log status=failed user_id={user_id} error='{e}'")
    await call.answer()
