# app/handlers/callback/ui/status_menu/character_modifier.py
from loguru import logger as log
import time

from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery


from app.resources.fsm_states.states import FSM_CONTEX_CHARACTER_STATUS
from app.resources.keyboards.status_callback import StatusModifierCallback
from app.resources.texts.ui_messages import TEXT_AWAIT
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay
from app.services.ui_service.status_menu.status_modifier_service import CharacterModifierUIService
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err


router = Router(name="character_Modifier_menu")


@router.callback_query(StatusModifierCallback.filter(F.level == "group"),
                       StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_modifier_group_handler(
        call: CallbackQuery,
        state: FSMContext,
        bot: Bot,
        callback_data: StatusModifierCallback
) -> None:
    """
    Обрабатывает выбор группы навыков, отображая навыки в этой группе.

    Args:
        call (CallbackQuery): Callback от кнопки выбора группы.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.
        callback_data (StatusModifierCallback): Данные из callback.

    Returns:
        None
    """

    if not call.from_user:
        log.warning("Хэндлер 'character_skill_group_handler' получил обновление без 'from_user'.")
        return

    await call.message.edit_text(TEXT_AWAIT, parse_mode="html")

    start_time = time.monotonic()
    user_id = call.from_user.id
    char_id = callback_data.char_id
    key = callback_data.key

    log.info(f"character_skill_group_handler начал работу с данными {user_id}")

    try:
        modifier_service = CharacterModifierUIService(
            char_id=char_id,
            key=key,
            state_data=await state.get_data(),
        )

        log.debug(f"key перед проверкой  = {key}")

        if key == "base_stats":
            stats_dto = await modifier_service.get_data_stats()
            text, kb = modifier_service.status_group_modifier_message(stats_dto)

        else:
            modifiers_dto = await modifier_service.get_data_modifier()
            text, kb = modifier_service.status_group_modifier_message(modifiers_dto)

        message_content = modifier_service.get_message_content_data()

        if not message_content:
            log.warning(f"")
            await Err.message_content_not_found_in_fsm(call=call)
            return

        chat_id , message_id = message_content

        await await_min_delay(start_time, min_delay=0.5)

        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode="html",
            reply_markup=kb
        )

        await state.update_data(group_key=key)

    except Exception as e:
        log.warning(f"{e}")


@router.callback_query(StatusModifierCallback.filter(F.level == "detail"),
                       StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_modifier_detail_handler(
        call: CallbackQuery,
        state: FSMContext,
        bot: Bot,
        callback_data: StatusModifierCallback
) -> None:
    """
    Обрабатывает выбор конкретного модификатора (Lvl 2) и показывает
    его "карточку" с описанием и итоговым значением.
    """
    if not call.from_user:
        log.warning("Хэндлер 'character_modifier_detail_handler' получил обновление без 'from_user'.")
        return

    await call.message.edit_text(TEXT_AWAIT, parse_mode="html")

    start_time = time.monotonic()
    user_id = call.from_user.id
    char_id = callback_data.char_id
    key = callback_data.key  # Ключ Lvl 2 (e.g., "energy_regen")
    log.info(f"User {user_id} (char_id={char_id}) запросил Lvl 2 для модификатора: '{key}'.")

    try:
        # --- 1. Сбор данных ---
        state_data = await state.get_data()

        # Ключ Lvl 1 (e.g., "resources") нам нужен для кнопки "Назад"
        group_key = state_data.get("group_key")

        if not group_key:
            log.warning(f"User {user_id}: 'group_key' не найден в FSM для character_modifier_detail_handler.")
            await Err.callback_data_missing(call=call)
            return

        # --- 2. Инициализация Сервиса ---
        # Сервис сам найдет нужные данные в HIERARCHY по 'key'
        modifier_service = CharacterModifierUIService(
            char_id=char_id,
            key=key,
            state_data=state_data,
        )

        # --- 3. Определение, какой DTO нам нужен ---
        # (Это логика, которую мы обсуждали)
        if group_key == "base_stats":
            log.debug(f"User {user_id}: Запрос данных из get_data_stats() для '{key}'.")
            dto_to_use = await modifier_service.get_data_stats()
        else:
            log.debug(f"User {user_id}: Запрос данных из get_data_modifier() для '{key}'.")
            dto_to_use = await modifier_service.get_data_modifier()

        if not dto_to_use:
            log.warning(f"User {user_id}: DTO (stats или modifiers) не найдены для char_id={char_id}.")
            await Err.generic_error(call=call)
            return

        # --- 4. Получение UI ---
        text, kb = modifier_service.status_detail_modifier_message(
            dto_to_use=dto_to_use,
            group_key=group_key
        )

        # --- 5. Обновление сообщения ---
        message_content = modifier_service.get_message_content_data()
        if not message_content:
            log.warning(f"User {user_id}: 'message_content' не найден в FSM.")
            await Err.message_content_not_found_in_fsm(call=call)
            return

        await await_min_delay(start_time, min_delay=0.5)

        chat_id, message_id = message_content
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode="html",
            reply_markup=kb
        )

    except Exception as e:
        log.exception(f"Критическая ошибка в 'character_modifier_detail_handler' для user {user_id}: {e}")
        await Err.generic_error(call=call)