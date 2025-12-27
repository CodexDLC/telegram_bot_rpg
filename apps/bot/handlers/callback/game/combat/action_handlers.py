import time
from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InaccessibleMessage
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states import BotState
from apps.bot.resources.keyboards.combat_callback import CombatActionCallback
from apps.bot.ui_service.combat.dto.combat_view_dto import CombatViewDTO
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.bot.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from apps.common.core.container import AppContainer
from apps.common.schemas_dto import SessionDataDTO
from apps.common.schemas_dto.combat_source_dto import CombatMoveDTO

action_router = Router(name="combat_actions")


@action_router.callback_query(BotState.combat, CombatActionCallback.filter(F.action == "submit"))
async def submit_turn_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    container: AppContainer,
    session: AsyncSession,
):
    """
    Хэндлер подтверждения хода (Submit).
    Отправляет ход, запускает анимацию ожидания и обновляет UI по завершении.
    """
    if not call.message or isinstance(call.message, InaccessibleMessage):
        return await call.answer("Сообщение недоступно.")

    await call.answer("Ход отправлен!")
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})

    # Данные для анимации все еще нужны в виде словарей, так как UIAnimationService работает с DTO
    message_content_dict = session_context.get("message_content")
    message_menu_dict = session_context.get("message_menu")

    # Читаем из session_context
    char_id = session_context.get("char_id")
    session_id = session_context.get("combat_session_id")

    target_id = state_data.get("combat_target_id")
    selection = state_data.get("combat_selection", {})

    if not char_id or not session_id or not target_id:
        return await Err.report_and_restart(call, "Данные сессии боя утеряны.")

    # Создаем оркестратор через контейнер
    orchestrator = container.get_combat_bot_orchestrator(session)

    # --- Зоны защиты ---
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
        # 1. Отправляем ход в ядро
        # handle_submit регистрирует ход и возвращает текущее состояние (обычно waiting)
        result_dto = await orchestrator.handle_submit(session_id, char_id, move_dto, state_data)

        # Сбрасываем выбор в FSM
        await state.update_data(combat_selection={}, combat_selected_ability=None)

        # 2. Обновляем лог боя (нижнее сообщение) сразу
        if result_dto.menu and (coords := orchestrator.get_menu_coords(state_data)):
            with suppress(TelegramAPIError):
                await bot.edit_message_text(
                    chat_id=coords.chat_id,
                    message_id=coords.message_id,
                    text=result_dto.menu.text,
                    reply_markup=result_dto.menu.kb,
                    parse_mode="HTML",
                )

        # 3. Запускаем анимацию ожидания на основном экране (верхнее сообщение)
        session_dto = SessionDataDTO(
            user_id=call.from_user.id,
            char_id=char_id,
            message_content=message_content_dict,
            message_menu=message_menu_dict,
        )
        anim_service = UIAnimationService(bot, session_dto)

        async def check_combat(step: int):
            # Просто проверяем статус: если не waiting - значит что-то произошло
            return await orchestrator.check_combat_status(session_id, char_id, state_data)

        # Поллинг с анимацией (30 секунд: 15 шагов по 2 сек)
        # result может быть None или CombatViewDTO
        result = await anim_service.animate_polling(
            base_text="⚔️ <b>Бой в разгаре!</b>\nОжидание хода противника...",
            check_func=check_combat,
            steps=15,
            step_delay=2.0,
        )

        # 4. Обработка результата
        if result:
            # result is CombatViewDTO

            if result.target_id is not None:
                await state.update_data(combat_target_id=result.target_id)

            # Обновляем основное сообщение
            if result.content and (coords := orchestrator.get_content_coords(state_data)):
                with suppress(TelegramAPIError):
                    await bot.edit_message_text(
                        chat_id=coords.chat_id,
                        message_id=coords.message_id,
                        text=result.content.text,
                        reply_markup=result.content.kb,
                        parse_mode="HTML",
                    )

            # Обновляем лог (там может быть инфо об уроне)
            if result.menu and (coords := orchestrator.get_menu_coords(state_data)):
                with suppress(TelegramAPIError):
                    await bot.edit_message_text(
                        chat_id=coords.chat_id,
                        message_id=coords.message_id,
                        text=result.menu.text,
                        reply_markup=result.menu.kb,
                        parse_mode="HTML",
                    )
        else:
            # Таймаут: восстанавливаем интерфейс (кнопку Refresh)
            timeout_result = await orchestrator.get_dashboard_view(session_id, char_id, {}, state_data)
            if timeout_result.content and (coords := orchestrator.get_content_coords(state_data)):
                with suppress(TelegramAPIError):
                    await bot.edit_message_text(
                        chat_id=coords.chat_id,
                        message_id=coords.message_id,
                        text=timeout_result.content.text,
                        reply_markup=timeout_result.content.kb,
                        parse_mode="HTML",
                    )

    except Exception as e:  # noqa: BLE001
        log.exception(f"ActionHandler | status=failed char_id={char_id} error={e}")
        await Err.report_and_restart(call, "Не удалось отправить ход в Ядро.")


@action_router.callback_query(BotState.combat, CombatActionCallback.filter(F.action == "refresh"))
async def refresh_combat_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    container: AppContainer,
    session: AsyncSession,
):
    """
    Хэндлер ручного обновления экрана боя. Обновляет ОБА сообщения.
    """
    if not call.message or isinstance(call.message, InaccessibleMessage):
        return await call.answer("Сообщение недоступно.")

    await call.answer("Обновляю...")
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})

    # Читаем из session_context
    char_id = session_context.get("char_id")
    session_id = session_context.get("combat_session_id")

    selection = state_data.get("combat_selection", {})

    if not char_id or not session_id:
        return await Err.report_and_restart(call, "Данные сессии боя утеряны.")

    # Создаем оркестратор через контейнер
    orchestrator = container.get_combat_bot_orchestrator(session)

    try:
        # 1. Оркестратор возвращает DTO
        result_dto = await orchestrator.get_dashboard_view(session_id, char_id, selection, state_data)

        # Обновляем target_id в FSM, если он изменился
        if result_dto.target_id is not None:
            await state.update_data(combat_target_id=result_dto.target_id)

        # 2. Обновляем контентное сообщение
        if result_dto.content and (coords := orchestrator.get_content_coords(state_data)):
            with suppress(TelegramAPIError):
                await bot.edit_message_text(
                    chat_id=coords.chat_id,
                    message_id=coords.message_id,
                    text=result_dto.content.text,
                    reply_markup=result_dto.content.kb,
                    parse_mode="HTML",
                )

        # 3. Обновляем сообщение с логом боя
        if result_dto.menu and (coords := orchestrator.get_menu_coords(state_data)):
            with suppress(TelegramAPIError):
                await bot.edit_message_text(
                    chat_id=coords.chat_id,
                    message_id=coords.message_id,
                    text=result_dto.menu.text,
                    reply_markup=result_dto.menu.kb,
                    parse_mode="HTML",
                )

    except Exception as e:  # noqa: BLE001
        log.error(f"ActionHandler | refresh failed: {e}")
        await Err.report_and_restart(call, "Сбой при получении данных боя.")


@action_router.callback_query(BotState.combat, CombatActionCallback.filter(F.action == "leave"))
async def leave_combat_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    container: AppContainer,
    session: AsyncSession,
):
    """
    Завершает участие в бою и переводит игрока в предыдущее состояние (Навигация или Арена).
    """
    if not call.message or isinstance(call.message, InaccessibleMessage):
        return await call.answer("Сообщение недоступно.")

    await call.answer("Возвращение...")
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")

    if not char_id:
        return await Err.report_and_restart(call, "Ошибка контекста при выходе из боя.")

    # 1. Получаем оркестратор и просим его "вывести" нас из боя
    orchestrator = container.get_combat_bot_orchestrator(session)

    try:
        result: CombatViewDTO = await orchestrator.leave_combat(char_id, state_data, session)

        # 2. Обновляем FSM (стейт и чистим боевые ключи)
        if result.new_state:
            await state.set_state(result.new_state)

        # Очищаем данные боя
        session_context["combat_session_id"] = None
        session_context["previous_state"] = None
        await state.update_data({FSM_CONTEXT_KEY: session_context})
        await state.update_data(combat_target_id=None, combat_selection={})

        # 3. Рендерим верхнее сообщение (Контент)
        if result.content and (coords := orchestrator.get_content_coords(state_data)):
            with suppress(TelegramAPIError):
                await bot.edit_message_text(
                    chat_id=coords.chat_id,
                    message_id=coords.message_id,
                    text=result.content.text,
                    reply_markup=result.content.kb,
                    parse_mode="HTML",
                )

        # 4. Рендерим нижнее сообщение (Меню)
        if result.menu and (coords := orchestrator.get_menu_coords(state_data)):
            with suppress(TelegramAPIError):
                await bot.edit_message_text(
                    chat_id=coords.chat_id,
                    message_id=coords.message_id,
                    text=result.menu.text,
                    reply_markup=result.menu.kb,
                    parse_mode="HTML",
                )
    except Exception as e:  # noqa: BLE001
        log.error(f"LeaveCombat | Failed to render target UI: {e}")
        # Fallback на случай ошибки
        if coords := orchestrator.get_content_coords(state_data):
            with suppress(TelegramAPIError):
                await bot.edit_message_text(
                    chat_id=coords.chat_id,
                    message_id=coords.message_id,
                    text="🗺 <b>Вы вернулись.</b>\nИспользуйте меню.",
                    reply_markup=None,
                    parse_mode="HTML",
                )
