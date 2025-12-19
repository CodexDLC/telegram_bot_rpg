import asyncio
from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InaccessibleMessage, Message
from loguru import logger as log

from apps.bot.core_client.arena_client import ArenaClient
from apps.bot.resources.fsm_states.states import ArenaState, InGame
from apps.bot.resources.keyboards.callback_data import ArenaQueueCallback
from apps.bot.ui_service.arena_ui_service.arena_bot_orchestrator import (
    ArenaBotOrchestrator,
    ArenaBotOrchestratorError,
)
from apps.bot.ui_service.arena_ui_service.arena_ui_service import ArenaUIService
from apps.bot.ui_service.combat.combat_bot_orchestrator import CombatBotOrchestrator
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY

router = Router(name="arena_1v1_router")


@router.callback_query(ArenaState.menu, ArenaQueueCallback.filter(F.action == "match_menu"))
async def arena_1v1_menu_handler(call: CallbackQuery, callback_data: ArenaQueueCallback, state: FSMContext) -> None:
    """Отображает меню выбора режима арены."""
    if not call.from_user or not call.message or isinstance(call.message, InaccessibleMessage):
        return

    char_id = callback_data.char_id
    mode = callback_data.match_type
    state_data = await state.get_data()
    actor_name = state_data.get(FSM_CONTEXT_KEY, {}).get("symbiote_name", "Симбиот")

    ui = ArenaUIService(char_id=char_id, actor_name=actor_name)
    text, kb = await ui.view_mode_menu(mode)

    await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(ArenaState.menu, ArenaState.waiting, ArenaQueueCallback.filter(F.action == "toggle_queue"))
async def arena_toggle_queue_handler(
    call: CallbackQuery,
    callback_data: ArenaQueueCallback,
    state: FSMContext,
    bot: Bot,
    arena_client: ArenaClient,
) -> None:
    """Обрабатывает вход/выход из очереди и запускает/останавливает поиск матча."""
    if not call.from_user or not call.message or isinstance(call.message, InaccessibleMessage):
        return

    char_id = callback_data.char_id
    user_id = call.from_user.id
    mode = callback_data.match_type
    state_data = await state.get_data()
    actor_name = state_data.get(FSM_CONTEXT_KEY, {}).get("symbiote_name", "Симбиот")

    try:
        bot_orchestrator = ArenaBotOrchestrator(arena_client, char_id, actor_name)
        text, kb = await bot_orchestrator.handle_toggle_queue(mode, char_id)
    except ArenaBotOrchestratorError as e:
        log.error(f"Arena Orchestrator failed: {e}")
        await Err.generic_error(call)
        return

    msg = await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await call.answer()

    current_state = await state.get_state()
    if current_state == ArenaState.menu:
        await state.set_state(ArenaState.waiting)
        log.info(f"FSM | state=ArenaState.waiting user_id={user_id}")
        if isinstance(msg, Message):
            await poll_for_match(bot, state, arena_client, mode, char_id, user_id, msg)
    else:
        await state.set_state(ArenaState.menu)
        log.info(f"FSM | state=ArenaState.menu user_id={user_id}")


async def poll_for_match(
    bot: Bot,
    state: FSMContext,
    arena_client: ArenaClient,
    mode: str,
    char_id: int,
    user_id: int,
    msg: Message,
):
    """Асинхронно опрашивает статус матча и показывает экран 'Бой найден'."""
    for _ in range(15):
        if await state.get_state() != ArenaState.waiting:
            log.info(f"Arena | Polling cancelled for user_id={user_id}")
            return

        response = await arena_client.check_match(mode, char_id)
        if response.status in ("found", "created_shadow"):
            session_id = response.session_id
            log.info(f"Arena | Match found or created. Session: {session_id}")

            await state.update_data(combat_session_id=session_id)

            state_data = await state.get_data()
            actor_name = state_data.get(FSM_CONTEXT_KEY, {}).get("symbiote_name", "Симбиот")
            ui = ArenaUIService(char_id=char_id, actor_name=actor_name)
            text, kb = await ui.view_match_found(session_id=session_id, metadata=response.metadata)

            # --- ВАЖНОЕ ИЗМЕНЕНИЕ: Удаляем старое и шлем новое для уведомления ---
            chat_id = msg.chat.id
            old_message_id = msg.message_id

            # Пытаемся удалить сообщение "Поиск..."
            with suppress(TelegramBadRequest):
                await bot.delete_message(chat_id=chat_id, message_id=old_message_id)

            # Отправляем НОВОЕ сообщение (придет пуш-уведомление)
            new_msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=kb, parse_mode="HTML")

            # Обновляем ID сообщения в контексте, чтобы дашборд боя заменил именно его
            session_context = state_data.get(FSM_CONTEXT_KEY, {})
            session_context["message_content"] = {"chat_id": chat_id, "message_id": new_msg.message_id}
            await state.update_data({FSM_CONTEXT_KEY: session_context})

            return

        await asyncio.sleep(3)

    log.error(f"Arena | Polling finished but no session_id for user_id={user_id}")
    with suppress(TelegramBadRequest):
        await msg.edit_text("Не удалось найти или создать бой. Попробуйте снова.")
    await state.set_state(ArenaState.menu)


@router.callback_query(ArenaState.waiting, ArenaQueueCallback.filter(F.action == "start_battle"))
async def arena_start_battle_handler(
    call: CallbackQuery,
    state: FSMContext,
    orchestrator: CombatBotOrchestrator,
) -> None:
    """Запускает боевую сессию после нажатия кнопки 'В БОЙ'."""
    if not call.from_user or not call.message or isinstance(call.message, InaccessibleMessage):
        return

    # Сразу даем фидбек пользователю, что кнопка нажалась
    await call.answer("⚔️ Бой начинается!", show_alert=False)

    user_id = call.from_user.id
    state_data = await state.get_data()
    session_id = state_data.get("combat_session_id")
    char_id = state_data.get(FSM_CONTEXT_KEY, {}).get("char_id")

    if not session_id or not char_id:
        log.error(f"Arena | Cannot start battle, no session_id or char_id in FSM for user_id={user_id}")
        await Err.generic_error(call)
        return

    log.info(f"Arena | Starting battle for user_id={user_id}, session_id={session_id}")

    # Оркестратор возвращает два кортежа, нам нужен только первый (контент)
    (text, kb), _ = await orchestrator.get_dashboard_view(session_id, char_id, {})

    # Редактируем то самое НОВОЕ сообщение, которое мы отправили в poll_for_match
    await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(InGame.combat)
    log.info(f"FSM | state=InGame.combat user_id={user_id}")
