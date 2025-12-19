import time
from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InaccessibleMessage
from loguru import logger as log

from apps.bot.resources.fsm_states import InGame
from apps.bot.resources.keyboards.combat_callback import CombatActionCallback
from apps.bot.ui_service.combat.combat_bot_orchestrator import CombatBotOrchestrator
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.schemas_dto.combat_source_dto import CombatMoveDTO

action_router = Router(name="combat_actions")


@action_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action == "submit"))
async def submit_turn_handler(call: CallbackQuery, state: FSMContext, orchestrator: CombatBotOrchestrator, bot: Bot):
    """
    Хэндлер подтверждения хода (Submit).
    Собирает данные из FSM, отправляет их в оркестратор и обновляет ОБА сообщения.
    """
    if not call.message or isinstance(call.message, InaccessibleMessage):
        return await call.answer("Сообщение недоступно.")

    await call.answer("Ход принят, обрабатываю...")
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_content = session_context.get("message_content")
    message_menu = session_context.get("message_menu")

    char_id = state_data.get("char_id")
    session_id = state_data.get("combat_session_id")
    target_id = state_data.get("combat_target_id")
    selection = state_data.get("combat_selection", {})

    if not char_id or not session_id or not target_id:
        return await Err.report_and_restart(call, "Данные сессии боя утеряны.")

    # --- Зоны защиты ---
    # Ядро ожидает список отдельных зон, а от кнопок приходит одна строка "zone1_zone2"
    def_zones_raw = selection.get("def", [])
    real_def_zones = def_zones_raw[0].split("_") if def_zones_raw else []

    move_dto = CombatMoveDTO(
        target_id=int(target_id),
        attack_zones=selection.get("atk", []),
        block_zones=real_def_zones,
        ability_key=state_data.get("combat_selected_ability"),
        execute_at=int(time.time()) + 60,
    )

    try:
        # 1. Оркестратор возвращает данные для двух сообщений
        (content_text, content_kb), (menu_text, menu_kb) = await orchestrator.handle_submit(
            session_id, char_id, move_dto
        )

        # 2. Обновляем контентное сообщение
        with suppress(TelegramAPIError):
            if message_content:
                await bot.edit_message_text(
                    chat_id=message_content["chat_id"],
                    message_id=message_content["message_id"],
                    text=content_text,
                    reply_markup=content_kb,
                    parse_mode="HTML",
                )

        # 3. Обновляем сообщение с логом боя
        with suppress(TelegramAPIError):
            if message_menu:
                await bot.edit_message_text(
                    chat_id=message_menu["chat_id"],
                    message_id=message_menu["message_id"],
                    text=menu_text,
                    reply_markup=menu_kb,
                    parse_mode="HTML",
                )

        await state.update_data(combat_selection={}, combat_selected_ability=None)

    except Exception as e:  # noqa: BLE001
        log.exception(f"ActionHandler | status=failed char_id={char_id} error={e}")
        await Err.report_and_restart(call, "Не удалось отправить ход в Ядро.")


@action_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action == "refresh"))
async def refresh_combat_handler(call: CallbackQuery, state: FSMContext, orchestrator: CombatBotOrchestrator, bot: Bot):
    """
    Хэндлер ручного обновления экрана боя. Обновляет ОБА сообщения.
    """
    if not call.message or isinstance(call.message, InaccessibleMessage):
        return await call.answer("Сообщение недоступно.")

    await call.answer("Обновляю...")
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_content = session_context.get("message_content")
    message_menu = session_context.get("message_menu")

    char_id = state_data.get("char_id")
    session_id = state_data.get("combat_session_id")
    selection = state_data.get("combat_selection", {})

    if not char_id or not session_id:
        return await Err.report_and_restart(call, "Данные сессии боя утеряны.")

    try:
        # 1. Оркестратор возвращает данные для двух сообщений
        (content_text, content_kb), (menu_text, menu_kb) = await orchestrator.get_dashboard_view(
            session_id, char_id, selection
        )

        # 2. Обновляем контентное сообщение
        with suppress(TelegramAPIError):
            if message_content:
                await bot.edit_message_text(
                    chat_id=message_content["chat_id"],
                    message_id=message_content["message_id"],
                    text=content_text,
                    reply_markup=content_kb,
                    parse_mode="HTML",
                )

        # 3. Обновляем сообщение с логом боя
        with suppress(TelegramAPIError):
            if message_menu:
                await bot.edit_message_text(
                    chat_id=message_menu["chat_id"],
                    message_id=message_menu["message_id"],
                    text=menu_text,
                    reply_markup=menu_kb,
                    parse_mode="HTML",
                )

    except Exception as e:  # noqa: BLE001
        log.error(f"ActionHandler | refresh failed: {e}")
        await Err.report_and_restart(call, "Сбой при получении данных боя.")


@action_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action == "leave"))
async def leave_combat_handler(call: CallbackQuery, state: FSMContext):
    """
    Завершает участие в бою и переводит игрока в навигацию.
    """
    if not call.message or isinstance(call.message, InaccessibleMessage):
        return await call.answer("Сообщение недоступно.")

    # Здесь можно добавить проверку через оркестратор, действительно ли бой окончен
    await state.set_state(InGame.navigation)
    await state.update_data(combat_session_id=None, combat_target_id=None)

    await call.message.edit_text("Вы покинули поле боя. Возвращение в мир...")
    await call.answer()
