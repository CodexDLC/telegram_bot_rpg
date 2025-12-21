from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InaccessibleMessage
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import ArenaState, InGame
from apps.bot.resources.keyboards.callback_data import ArenaQueueCallback
from apps.bot.ui_service.arena_ui_service.arena_bot_orchestrator import (
    ArenaBotOrchestratorError,
)
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.bot.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from apps.common.core.container import AppContainer
from apps.common.schemas_dto import SessionDataDTO

router = Router(name="arena_1v1_router")


@router.callback_query(ArenaState.menu, ArenaQueueCallback.filter(F.action == "match_menu"))
async def arena_1v1_menu_handler(
    call: CallbackQuery,
    callback_data: ArenaQueueCallback,
    state: FSMContext,
    container: AppContainer,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """Отображает меню выбора режима арены."""
    await call.answer()
    if not call.from_user or not call.message or isinstance(call.message, InaccessibleMessage):
        return

    # char_id = callback_data.char_id # Удалено: не используется
    mode = str(callback_data.match_type)
    state_data = await state.get_data()

    orchestrator = container.get_arena_bot_orchestrator(session)
    result_dto = await orchestrator.get_mode_menu(mode, state_data)

    if result_dto.content:
        with suppress(TelegramBadRequest):
            await call.message.edit_text(
                text=result_dto.content.text, reply_markup=result_dto.content.kb, parse_mode="HTML"
            )


@router.callback_query(
    StateFilter(ArenaState.menu, ArenaState.waiting), ArenaQueueCallback.filter(F.action == "toggle_queue")
)
async def arena_toggle_queue_handler(
    call: CallbackQuery,
    callback_data: ArenaQueueCallback,
    state: FSMContext,
    bot: Bot,
    container: AppContainer,
    session: AsyncSession,
) -> None:
    """Обрабатывает вход/выход из очереди и запускает/останавливает поиск матча."""
    await call.answer()

    if not call.from_user or not call.message or isinstance(call.message, InaccessibleMessage):
        return

    char_id = callback_data.char_id
    user_id = call.from_user.id
    mode = str(callback_data.match_type)
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_content = session_context.get("message_content")
    message_menu = session_context.get("message_menu")

    orchestrator = container.get_arena_bot_orchestrator(session)

    try:
        result_dto = await orchestrator.handle_toggle_queue(mode, char_id, state_data)

        if result_dto.content:
            msg = await call.message.edit_text(
                text=result_dto.content.text, reply_markup=result_dto.content.kb, parse_mode="HTML"
            )
        else:
            msg = call.message  # Fallback

    except ArenaBotOrchestratorError as e:
        log.error(f"Arena Orchestrator failed: {e}")
        await Err.generic_error(call)
        return

    current_state = await state.get_state()
    if current_state == ArenaState.menu:
        await state.set_state(ArenaState.waiting)
        log.info(f"FSM | state=ArenaState.waiting user_id={user_id}")

        # --- ЗАПУСК АНИМАЦИИ ПОИСКА ---
        session_dto = SessionDataDTO(
            user_id=user_id, char_id=char_id, message_content=message_content, message_menu=message_menu
        )
        anim_service = UIAnimationService(bot, session_dto)

        async def check_match(step: int):
            # Проверяем, не отменил ли пользователь поиск
            if await state.get_state() != ArenaState.waiting:
                return "cancelled"

            # Используем оркестратор для проверки матча
            res = await orchestrator.handle_check_match(mode, char_id, state_data)
            if res and res.session_id:
                return res.session_id
            return None

        # Запускаем анимацию поиска
        base_text = result_dto.content.text if result_dto.content else "Поиск..."

        result = await anim_service.animate_polling(
            base_text=base_text,
            check_func=check_match,
            steps=15,
            step_delay=3.0,
        )

        if result and result != "cancelled":
            # Матч найден!
            session_id = result
            log.info(f"Arena | Match found or created. Session: {session_id}")

            # Сохраняем session_id
            session_context["combat_session_id"] = session_id
            session_context["previous_state"] = "ArenaState:menu"

            await state.update_data({FSM_CONTEXT_KEY: session_context})

            # Отрисовываем "Бой найден" через оркестратор
            found_dto = await orchestrator.handle_check_match(mode, char_id, state_data)

            if found_dto and found_dto.content:
                with suppress(TelegramBadRequest):
                    if isinstance(msg, bool):
                        await call.message.edit_text(
                            text=found_dto.content.text, reply_markup=found_dto.content.kb, parse_mode="HTML"
                        )
                    else:
                        await msg.edit_text(
                            text=found_dto.content.text, reply_markup=found_dto.content.kb, parse_mode="HTML"
                        )

        elif result is None:
            # Таймаут
            log.info(f"Arena | Polling timeout for user_id={user_id}")
            with suppress(TelegramBadRequest):
                if isinstance(msg, bool):
                    await call.message.edit_text("⏳ Не удалось найти противника. Попробуйте снова.")
                else:
                    await msg.edit_text("⏳ Не удалось найти противника. Попробуйте снова.")
            await state.set_state(ArenaState.menu)

    else:
        # Отмена поиска (нажата кнопка "Покинуть очередь")
        await state.set_state(ArenaState.menu)
        log.info(f"FSM | state=ArenaState.menu user_id={user_id}")


@router.callback_query(ArenaState.waiting, ArenaQueueCallback.filter(F.action == "start_battle"))
async def arena_start_battle_handler(
    call: CallbackQuery,
    state: FSMContext,
    container: AppContainer,
    session: AsyncSession,
) -> None:
    """Запускает боевую сессию после нажатия кнопки 'В БОЙ'."""
    await call.answer("⚔️ Бой начинается!", show_alert=False)

    if not call.from_user or not call.message or isinstance(call.message, InaccessibleMessage):
        return

    user_id = call.from_user.id
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})

    # Читаем из session_context
    session_id = session_context.get("combat_session_id")
    char_id = session_context.get("char_id")

    if not session_id or not char_id:
        log.error(f"Arena | Cannot start battle, no session_id or char_id in FSM for user_id={user_id}")
        await Err.generic_error(call)
        return

    log.info(f"Arena | Starting battle for user_id={user_id}, session_id={session_id}")

    # Создаем оркестратор боя через контейнер
    orchestrator = container.get_combat_bot_orchestrator(session)

    try:
        # Оркестратор возвращает DTO
        result_dto = await orchestrator.get_dashboard_view(session_id, char_id, {}, state_data)

        # Обновляем target_id в FSM, если он изменился
        if result_dto.target_id is not None:
            await state.update_data(combat_target_id=result_dto.target_id)

        # Обновляем сообщение (здесь это call.message, так как мы нажали кнопку в нем)
        if result_dto.content:
            await call.message.edit_text(
                text=result_dto.content.text, reply_markup=result_dto.content.kb, parse_mode="HTML"
            )

        await state.set_state(InGame.combat)
        log.info(f"FSM | state=InGame.combat user_id={user_id}")

    except ValueError as e:
        log.warning(f"Arena | Session invalid or expired: {e}")
        await call.message.edit_text("⚠️ Сессия боя устарела или недействительна. Пожалуйста, начните поиск заново.")
        await state.set_state(ArenaState.menu)
