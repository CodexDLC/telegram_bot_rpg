# app/handlers/callback/ui/status_menu/character_modifier.py
import logging
import time

from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery


from app.resources.fsm_states.states import FSM_CONTEX_CHARACTER_STATUS
from app.resources.keyboards.status_callback import StatusModifierCallback
from app.services.ui_service.status_menu.status_modifier_service import CharacterModifierUIService
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err

log = logging.getLogger(__name__)

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

    user_id = call.from_user.id
    char_id = callback_data.char_id
    key = callback_data.key

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

        message_content = modifier_service.get_message_data()

        if not message_content:
            log.warning(f"")
            await Err.message_content_not_found_in_fsm(call=call)
            return

        chat_id , message_id = message_content

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
async def character_modifier_detail_handler(call: CallbackQuery, state: FSMContext, bot: Bot, callback_data: StatusModifierCallback) -> None:
    """
    Обрабатывает выбор конкретного навыка (заглушка).

    Args:
        call (CallbackQuery): Callback от кнопки выбора навыка.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.
        callback_data (StatusModifierCallback): Данные из callback.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Хэндлер 'character_skill_handler' получил обновление без 'from_user'.")
        return
