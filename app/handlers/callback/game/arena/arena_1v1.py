import asyncio
from functools import partial

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import ArenaState, InGame
from app.resources.keyboards.callback_data import ArenaQueueCallback
from app.resources.schemas_dto.fsm_state_dto import SessionDataDTO
from app.services.game_service.arena.arena_service import ArenaService
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.arena_ui_service.arena_builder import ArenaUIBuilder
from app.services.ui_service.combat.combat_ui_service import CombatUIService
from app.services.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from database.session import async_session_factory

router = Router(name="arena_1v1_router")


# =================================================================
# 🔄 ЛОКАЛЬНАЯ ФУНКЦИЯ ОЖИДАНИЯ (Вместо отдельного файла)
# =================================================================
async def _wait_for_battle_task(
    user_id: int,
    char_id: int,
    mode: str,
    bot: Bot,
    chat_id: int,
    message_id: int,
    state: FSMContext,
) -> None:
    """
    Локальная задача для UI:
    1. Крутит анимацию "Поиск..."
    2. Опрашивает ArenaService
    3. Если находит бой -> Рисует интерфейс боя и меняет стейт.
    """
    # Открываем сессию, так как это отдельный поток (Task)
    async with async_session_factory() as session:
        try:
            # Инициализируем Фасад
            arena = ArenaService(session, char_id)

            # Подготовка Аниматора (ему нужен DTO)
            session_dto = SessionDataDTO(
                user_id=user_id,
                char_id=char_id,
                message_content={"chat_id": chat_id, "message_id": message_id},
            )
            anim_service = UIAnimationService(bot, session_dto)

            # 1. Вход в очередь (Бизнес-логика)
            await arena.join_queue(mode)

            # 2. Анимация + Опрос (UI + Бизнес-логика)
            # partial создает функцию check_match(step), где mode уже подставлен
            check_func = partial(arena.check_match, mode)

            session_id = await anim_service.animate_polling(
                base_text="🔎 <b>Поиск достойного соперника...</b>",
                check_func=check_func,
                steps=6,  # 6 шагов по 5 сек = 30 сек
                step_delay=5.0,
            )

            # 3. Тайм-аут -> Просим сервис создать Тень
            if not session_id:
                log.info(f"Тайм-аут (user {user_id}). Бой с Тенью.")
                session_id = await arena.create_shadow_battle(mode)

            # 4. Переход в Бой (UI Logic)
            if session_id:
                # Проверка: Игрок не ушел? (Race Condition)
                if await state.get_state() != ArenaState.waiting:
                    log.warning(f"User {user_id} отменил поиск. Бой {session_id} игнорируется.")
                    return

                # Сохраняем контекст боя в FSM
                state_data = await state.get_data()
                session_context = state_data.get(FSM_CONTEXT_KEY, {})
                session_context["combat_session_id"] = session_id
                await state.update_data({FSM_CONTEXT_KEY: session_context})

                # Рисуем экран боя
                # Берем обновленные данные
                state_data = await state.get_data()
                combat_ui = CombatUIService(user_id, char_id, session_id, state_data)
                text, kb = await combat_ui.render_dashboard(current_selection={})

                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    reply_markup=kb,
                    parse_mode="HTML",
                )

                # Меняем стейт на Игровой
                await state.set_state(InGame.combat)

        except asyncio.CancelledError:
            log.info(f"Задача ожидания боя для user {user_id} была отменена.")
            # Здесь можно добавить логику по очистке, если это необходимо
        except RuntimeError as e:
            log.exception(f"Ошибка в задаче ожидания боя (user {user_id}): {e}")


# =================================================================
# 1. ПОДМЕНЮ 1v1 (Экран выбора)
# =================================================================
@router.callback_query(ArenaState.menu, ArenaQueueCallback.filter(F.action == "match_menu"))
async def arena_1v1_menu_handler(
    call: CallbackQuery,
    callback_data: ArenaQueueCallback,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not call.from_user:
        return

    char_id = callback_data.char_id
    match_type = callback_data.match_type

    state_data = await state.get_data()
    message_content = state_data.get(FSM_CONTEXT_KEY, {}).get("message_content")

    if not message_content:
        await Err.message_content_not_found_in_fsm(call)
        return

    # Рисуем меню режима
    ui_builder = ArenaUIBuilder(char_id, state_data, session)
    text, kb = await ui_builder.render_mode_menu(match_type)

    if text and kb:
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
        await call.answer()
    else:
        await Err.generic_error(call)


# =================================================================
# 2. ПОДАЧА ЗАЯВКИ (Найти бой)
# =================================================================
@router.callback_query(ArenaState.menu, ArenaQueueCallback.filter(F.action == "submit_queue"))
async def arena_submit_queue_handler(
    call: CallbackQuery,
    callback_data: ArenaQueueCallback,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    if not call.from_user:
        return

    char_id = callback_data.char_id
    user_id = call.from_user.id
    match_type = callback_data.match_type

    # 1. Блокируем UI (стейт Waiting)
    await state.set_state(ArenaState.waiting)

    # 2. Рисуем экран "Поиск..."
    state_data = await state.get_data()
    ui_builder = ArenaUIBuilder(char_id, state_data, session)
    text, kb = await ui_builder.render_searching_screen(match_type)

    await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")

    # 3. Запускаем локальную задачу ожидания (Fire and Forget)
    # Она сама будет крутиться и обновит экран, когда найдет бой
    asyncio.create_task(
        _wait_for_battle_task(
            user_id,
            char_id,
            match_type,
            bot,
            call.message.chat.id,
            call.message.message_id,
            state,
        )
    )


# =================================================================
# 3. ОТМЕНА ЗАЯВКИ (Выход)
# =================================================================
@router.callback_query(ArenaState.waiting, ArenaQueueCallback.filter(F.action == "cancel_queue"))
async def arena_cancel_queue_handler(
    call: CallbackQuery,
    callback_data: ArenaQueueCallback,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not call.from_user:
        return

    char_id = callback_data.char_id
    match_type = callback_data.match_type

    log.info(f"User {call.from_user.id} отменяет поиск {match_type}.")

    # 1. Бизнес-логика: Уйти из очереди (через Фасад)
    # Создаем экземпляр сервиса здесь, чтобы вызвать метод
    arena = ArenaService(session, char_id)
    await arena.cancel_queue(match_type)

    # 2. UI: Возврат в меню
    await state.set_state(ArenaState.menu)

    state_data = await state.get_data()
    ui_builder = ArenaUIBuilder(char_id, state_data, session)
    text, kb = await ui_builder.render_mode_menu(match_type)

    if isinstance(call.message, Message):
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await call.answer("Поиск отменен.")
