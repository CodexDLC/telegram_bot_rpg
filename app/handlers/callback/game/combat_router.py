import time
from contextlib import suppress
from typing import Any

from aiogram import Bot, Router
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
from app.resources.schemas_dto.fsm_state_dto import SessionDataDTO
from app.services.core_service.manager.account_manager import AccountManager
from app.services.core_service.manager.arena_manager import ArenaManager
from app.services.core_service.manager.combat_manager import CombatManager
from app.services.core_service.manager.world_manager import WorldManager
from app.services.game_service.combat.combat_service import CombatService
from app.services.game_service.game_world_service import GameWorldService
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.arena_ui_service.arena_ui_service import ArenaUIService
from app.services.ui_service.combat.combat_ui_service import CombatUIService
from app.services.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay
from app.services.ui_service.menu_service import MenuService
from app.services.ui_service.navigation_service import NavigationService

router = Router(name="combat_router")


@router.callback_query(InGame.combat, CombatZoneCallback.filter())
async def combat_zone_toggle_handler(
    call: CallbackQuery,
    callback_data: CombatZoneCallback,
    state: FSMContext,
    combat_manager: CombatManager,
    account_manager: AccountManager,
) -> None:
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

    ui_service = CombatUIService(user_id, char_id, str(session_id), state_data, combat_manager, account_manager)
    text, kb = await ui_service.render_dashboard(current_selection=selection)

    try:
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    except TelegramAPIError as e:
        log.warning(f"UIRender | component=combat_dashboard status=failed user_id={user_id} error='{e}'")
    await call.answer()


@router.callback_query(InGame.combat, CombatActionCallback.filter())
async def combat_action_handler(
    call: CallbackQuery,
    callback_data: CombatActionCallback,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    combat_manager: CombatManager,
    account_manager: AccountManager,
    world_manager: WorldManager,
    arena_manager: ArenaManager,
    game_world_service: GameWorldService,
) -> None:
    """Обрабатывает действия в бою (подтверждение хода, выход, меню)."""
    # start_time = time.monotonic() # Удалено, так как не используется
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
            arena_ui = ArenaUIService(char_id, state_data, session, account_manager, arena_manager, combat_manager)
            content_text, content_kb = await arena_ui.view_main_menu()
        else:
            await state.set_state(InGame.navigation)
            nav_service = NavigationService(
                char_id, state_data, account_manager, world_manager, game_world_service=game_world_service
            )
            content_text, content_kb = await nav_service.reload_current_ui()

        msg_menu = session_context.get("message_menu")
        if msg_menu:
            ms = MenuService(
                game_stage="in_game", state_data=state_data, session=session, account_manager=account_manager
            )
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
        # 1. Сначала отвечаем на колбэк, чтобы убрать часики
        await call.answer("Ход зафиксирован.")

        selection: dict[str, list[str]] = state_data.get("combat_selection", {})
        atk_zones = selection.get("atk", [])
        def_zones_raw = selection.get("def", [])
        real_def_zones = def_zones_raw[0].split("_") if def_zones_raw else []

        combat_service = CombatService(str(session_id), combat_manager, account_manager)
        all_participants = await combat_manager.get_session_participants(str(session_id))

        # Определяем ID цели (для PvP важно найти правильного врага)
        target_id = next((int(pid) for pid in all_participants if int(pid) != char_id), None)

        if target_id is None:
            log.error(f"Combat | status=failed reason='target not found' user_id={user_id}")
            await Err.generic_error(call)
            return

        # 2. Регистрируем ход
        await combat_service.register_move(
            actor_id=char_id, target_id=target_id, attack_zones=atk_zones or None, block_zones=real_def_zones or None
        )
        # Сбрасываем выбор в FSM
        await state.update_data(combat_selection={"atk": [], "def": []})

        # 3. ПРОВЕРКА: Случился ли обмен?
        # Если pending_move все еще существует для нашей пары, значит мы ждем врага.
        # Mypy fix: убеждаемся, что target_id не None перед использованием
        if target_id is None:
            log.error(f"Combat | status=failed reason='target_id became None unexpectedly' user_id={user_id}")
            await Err.generic_error(call)
            return
        is_pending_move = await combat_manager.get_pending_move(str(session_id), char_id, target_id)

        ui_service = CombatUIService(user_id, char_id, str(session_id), state_data, combat_manager, account_manager)

        if is_pending_move:
            # --- СЦЕНАРИЙ ОЖИДАНИЯ (PvP) ---
            log.info(f"Combat | status=waiting_opponent char_id={char_id} target_id={target_id}")

            # 3.1 Показываем экран "Ждем..."
            wait_text, wait_kb = await ui_service.render_waiting_screen()

            with suppress(TelegramAPIError):  # Заменено на contextlib.suppress
                if msg_content := session_context.get("message_content"):
                    await call.bot.edit_message_text(
                        chat_id=msg_content["chat_id"],
                        message_id=msg_content["message_id"],
                        text=wait_text,
                        reply_markup=wait_kb,
                        parse_mode="HTML",
                    )

            # 3.2 Запускаем анимацию Polling (она будет сама проверять статус)
            session_dto = SessionDataDTO(**session_context)
            anim_service = UIAnimationService(bot, session_dto)

            # Функция проверки для аниматора:
            # Возвращает "Done", если pending_move исчез (обмен случился)
            async def check_turn_done(step: int) -> str | None:
                # Mypy fix: убеждаемся, что target_id не None
                assert target_id is not None
                still_pending = await combat_manager.get_pending_move(str(session_id), char_id, target_id)
                if not still_pending:
                    return "TurnComplete"
                return None

            # Крутим цикл 10 раз по 2 секунды (20 секунд ожидания)
            # Текст анимации будет обновляться сам
            result = await anim_service.animate_polling(
                base_text=wait_text, check_func=check_turn_done, steps=10, step_delay=2.0
            )

            # Если цикл закончился и мы все еще ждем - оставляем экран ожидания
            if not result:
                return

        # --- СЦЕНАРИЙ ЗАВЕРШЕНИЯ ХОДА ---
        # Сюда мы попадаем, если is_pending был False сразу,
        # ИЛИ если animate_polling вернул "TurnComplete".

        # Небольшая задержка, чтобы базы данных успели синхронизироваться после расчетов
        await await_min_delay(time.monotonic(), min_delay=0.5)

        # Рендерим актуальный дашборд
        text, kb = await ui_service.render_dashboard(current_selection={})

        # Обновляем Лог (сверху)
        with suppress(TelegramAPIError):  # Заменено на contextlib.suppress
            if msg_menu := session_context.get("message_menu"):
                log_text, log_kb = await ui_service.render_combat_log(page=0)
                await call.bot.edit_message_text(
                    chat_id=msg_menu["chat_id"],
                    message_id=msg_menu["message_id"],
                    text=log_text,
                    reply_markup=log_kb,
                    parse_mode="HTML",
                )

        # Обновляем Дашборд (снизу)
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
                # Вот тут ловим "not modified", если вдруг расчет не изменил HP
                log.warning(f"Combat | dashboard_update_warning error='{e}'")

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

        # 1. ПИНАЕМ СЕРВЕР (Таймеры, AFK)
        combat_service = CombatService(str(session_id), combat_manager, account_manager)
        await combat_service.process_turn_updates()

        ui_service = CombatUIService(user_id, char_id, str(session_id), state_data, combat_manager, account_manager)

        # 2. ОБНОВЛЯЕМ ЛОГ (Верхнее сообщение) - Это безопасно, лог всегда актуален
        with suppress(TelegramAPIError):  # Заменено на contextlib.suppress
            if msg_menu := session_context.get("message_menu"):
                log_text, log_kb = await ui_service.render_combat_log(page=0)
                await bot.edit_message_text(
                    chat_id=msg_menu["chat_id"],
                    message_id=msg_menu["message_id"],
                    text=log_text,
                    reply_markup=log_kb,
                    parse_mode="HTML",
                )

        # 3. ОБНОВЛЯЕМ ДАШБОРД (Нижнее сообщение) - 🔥 ТУТ ГЛАВНАЯ ПРАВКА 🔥
        # Сначала проверяем, не ждем ли мы кого-то
        all_participants = await combat_manager.get_session_participants(str(session_id))
        target_id = next((int(pid) for pid in all_participants if int(pid) != char_id), None)

        is_pending = False
        if target_id:
            is_pending = bool(await combat_manager.get_pending_move(str(session_id), char_id, target_id))

        if is_pending:
            # ЕСЛИ МЫ ЖДЕМ: Рисуем экран ожидания снова!
            # Можно даже запустить короткий поллинг, чтобы "оживить" таймер
            text, kb = await ui_service.render_waiting_screen()

            # (Опционально) Запускаем мини-поллинг на 1-2 тика, чтобы проверить статус визуально
            # Но для простоты пока просто покажем статичный экран ожидания с кнопкой "Обновить"
        else:
            # ЕСЛИ НЕ ЖДЕМ (Ход свободен): Рисуем кнопки боя
            text, kb = await ui_service.render_dashboard(current_selection={})

        if msg_content := session_context.get("message_content"):
            try:
                await bot.edit_message_text(
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

        await call.answer("Статус обновлен")


@router.callback_query(InGame.combat, CombatLogCallback.filter())
async def combat_log_pagination(
    call: CallbackQuery,
    callback_data: CombatLogCallback,
    state: FSMContext,
    combat_manager: CombatManager,
    account_manager: AccountManager,
) -> None:
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

    ui_service = CombatUIService(user_id, char_id, str(session_id), state_data, combat_manager, account_manager)
    text, kb = await ui_service.render_combat_log(page=page)

    try:
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    except TelegramAPIError as e:
        log.warning(f"UIRender | component=combat_log status=failed user_id={user_id} error='{e}'")
    await call.answer()
