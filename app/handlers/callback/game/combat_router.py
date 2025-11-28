# app/handlers/callback/game/combat_router.py
import time
from contextlib import suppress
from typing import Any

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log

from app.resources.fsm_states.states import InGame
from app.resources.keyboards.combat_callback import (
    CombatActionCallback,
    CombatLogCallback,
    CombatZoneCallback,
)
from app.services.core_service.manager.combat_manager import combat_manager
from app.services.game_service.combat.combat_service import CombatService
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.combat.combat_ui_service import CombatUIService
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay

router = Router(name="combat_router")


@router.callback_query(InGame.combat, CombatZoneCallback.filter())
async def combat_zone_toggle_handler(call: CallbackQuery, callback_data: CombatZoneCallback, state: FSMContext) -> None:
    """
    Обрабатывает нажатия на зоны атаки/защиты в бою.

    Переключает выбранные зоны в состоянии FSM и обновляет
    сообщение с панелью управления боем.

    Args:
        call (CallbackQuery): Входящий колбэк.
        callback_data (CombatZoneCallback): Данные колбэка с информацией о зоне.
        state (FSMContext): Контекст FSM.

    Returns:
        None
    """
    if not call.from_user or not isinstance(call.message, Message):
        log.warning("Колбэк без `from_user` или `message` в 'combat_zone_toggle_handler'.")
        return

    state_data = await state.get_data()
    session_context: dict[str, Any] = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    user_id = call.from_user.id

    log.info(
        f"Хэндлер 'combat_zone_toggle_handler' [layer:{callback_data.layer}, zone:{callback_data.zone_id}] "
        f"вызван user_id={user_id}, char_id={char_id}"
    )

    selection: dict[str, list[str]] = state_data.get("combat_selection", {"atk": [], "def": []})
    layer = callback_data.layer
    zone_id = callback_data.zone_id
    current_list = selection.get(layer, [])

    if zone_id in current_list:
        current_list.remove(zone_id)
    else:
        if layer == "def":
            current_list.clear()
        current_list.append(zone_id)

    selection[layer] = current_list
    await state.update_data(combat_selection=selection)
    log.debug(f"Выбор зон обновлен для user_id={user_id}: {selection}")

    session_id = session_context.get("combat_session_id")

    if not session_id or not char_id:
        log.warning(f"User {user_id} в 'combat_zone_toggle_handler' не имеет session_id или char_id в FSM.")
        await Err.generic_error(call)
        return

    ui_service = CombatUIService(user_id, char_id, str(session_id), state_data)
    text, kb = await ui_service.render_dashboard(current_selection=selection)

    with suppress(TelegramAPIError):
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(InGame.combat, CombatActionCallback.filter())
async def combat_action_handler(call: CallbackQuery, callback_data: CombatActionCallback, state: FSMContext) -> None:
    """
    Обрабатывает действия в бою (например, подтверждение хода).

    Args:
        call (CallbackQuery): Входящий колбэк.
        callback_data (CombatActionCallback): Данные колбэка с действием.
        state (FSMContext): Контекст FSM.

    Returns:
        None
    """
    start_time = time.monotonic()
    if not call.from_user or not call.message or not call.bot:
        log.warning("Колбэк без `from_user`, `message` или `bot` в 'combat_action_handler'.")
        return

    action = callback_data.action
    state_data = await state.get_data()
    session_context: dict[str, Any] = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    user_id = call.from_user.id

    log.info(f"Хэндлер 'combat_action_handler' [action:{action}] вызван user_id={user_id}, char_id={char_id}")

    session_id = session_context.get("combat_session_id")

    if not session_id or not char_id:
        log.warning(f"User {user_id} в 'combat_action_handler' не имеет session_id или char_id в FSM.")
        await Err.generic_error(call)
        return

    if action == "submit":
        await call.answer("Ход принят!")

        selection: dict[str, list[str]] = state_data.get("combat_selection", {})
        atk_zones = selection.get("atk", [])
        def_zones_raw = selection.get("def", [])

        real_def_zones = []
        if def_zones_raw:
            real_def_zones = def_zones_raw[0].split("_")

        log.debug(f"Ход user_id={user_id}: atk={atk_zones}, def={real_def_zones}")

        combat_service = CombatService(str(session_id))

        all_participants = await combat_manager.get_session_participants(str(session_id))
        target_id = None
        for pid_str in all_participants:
            pid = int(pid_str)
            if pid != char_id:
                target_id = pid
                break

        if target_id is None:
            log.error(f"Не удалось найти цель для user_id={user_id} в бою {session_id}")
            await Err.generic_error(call)
            return

        log.debug(f"Регистрация хода для user_id={user_id} против target_id={target_id}")
        await combat_service.register_move(
            actor_id=char_id,
            target_id=target_id,
            attack_zones=atk_zones if atk_zones else None,
            block_zones=real_def_zones if real_def_zones else None,
        )

        await state.update_data(combat_selection={"atk": [], "def": []})

        ui_service = CombatUIService(user_id, char_id, str(session_id), state_data)

        msg_menu = session_context.get("message_menu")
        if isinstance(msg_menu, dict):
            log_text, log_kb = await ui_service.render_combat_log(page=0)
            with suppress(TelegramAPIError):
                await call.bot.edit_message_text(
                    chat_id=msg_menu["chat_id"],
                    message_id=msg_menu["message_id"],
                    text=log_text,
                    reply_markup=log_kb,
                    parse_mode="HTML",
                )

        msg_content = session_context.get("message_content")
        if isinstance(msg_content, dict):
            with suppress(TelegramAPIError):
                await call.bot.edit_message_text(
                    chat_id=msg_content["chat_id"],
                    message_id=msg_content["message_id"],
                    text="⏳ <b>Ход отправлен...</b>\n<i>Ожидание результата...</i>",
                    parse_mode="HTML",
                    reply_markup=None,
                )

        await await_min_delay(start_time, min_delay=1.5)

        text, kb = await ui_service.render_dashboard(current_selection={})
        if isinstance(msg_content, dict):
            with suppress(TelegramAPIError):
                await call.bot.edit_message_text(
                    chat_id=msg_content["chat_id"],
                    message_id=msg_content["message_id"],
                    text=text,
                    reply_markup=kb,
                    parse_mode="HTML",
                )

    elif action == "menu":
        log.debug(f"User {user_id} нажал на меню действий в бою (WIP).")
        await call.answer("Меню действий (WIP)")


@router.callback_query(InGame.combat, CombatLogCallback.filter())
async def combat_log_pagination(call: CallbackQuery, callback_data: CombatLogCallback, state: FSMContext) -> None:
    """
    Обрабатывает пагинацию в логе боя.

    Args:
        call (CallbackQuery): Входящий колбэк.
        callback_data (CombatLogCallback): Данные колбэка с номером страницы.
        state (FSMContext): Контекст FSM.

    Returns:
        None
    """
    if not call.from_user or not isinstance(call.message, Message):
        log.warning("Колбэк без `from_user` или `message` в 'combat_log_pagination'.")
        return

    page = callback_data.page
    state_data = await state.get_data()
    session_context: dict[str, Any] = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    user_id = call.from_user.id

    log.info(f"Хэндлер 'combat_log_pagination' [page:{page}] вызван user_id={user_id}, char_id={char_id}")

    session_id = session_context.get("combat_session_id")

    if not session_id or not char_id:
        log.warning(f"User {user_id} в 'combat_log_pagination' не имеет session_id или char_id в FSM.")
        await Err.generic_error(call)
        return

    ui_service = CombatUIService(user_id, char_id, str(session_id), state_data)
    text, kb = await ui_service.render_combat_log(page=page)

    with suppress(TelegramAPIError):
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await call.answer()
