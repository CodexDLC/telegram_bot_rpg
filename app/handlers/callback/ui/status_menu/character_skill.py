# app/handlers/callback/ui/status_menu/character_skill.py
import logging
import time

from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.resources.fsm_states.states import FSM_CONTEX_CHARACTER_STATUS
from app.resources.texts.ui_messages import TEXT_AWAIT
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay
from app.services.ui_service.status_menu.status_skill_service import CharacterSkillStatusService
from app.resources.keyboards.status_callback import StatusSkillsCallback
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err

log = logging.getLogger(__name__)

router = Router(name="character_skill_menu")


@router.callback_query(StatusSkillsCallback.filter(F.level == "group"),
                       StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_skill_group_handler(
        call: CallbackQuery,
        state: FSMContext,
        bot: Bot,
        callback_data: StatusSkillsCallback
) -> None:
    """
    Обрабатывает выбор группы навыков, отображая навыки в этой группе.

    Args:

        call (CallbackQuery): Callback от кнопки выбора группы.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.
        callback_data (StatusSkillsCallback): Данные из callback.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Хэндлер 'character_skill_group_handler' получил обновление без 'from_user'.")
        return

    start_time = time.monotonic()
    char_id = callback_data.char_id
    key = callback_data.key
    user_id = call.from_user.id
    log.info(f"User {user_id}: Запуск `character_skill_group_handler` для char_id={char_id}, key='{key}'.")

    await call.message.edit_text(TEXT_AWAIT, parse_mode="html")

    try:
        char_skill_ser = CharacterSkillStatusService(
            char_id=char_id,
            key=key,
            state_data=await state.get_data()
        )
        skills_data = await char_skill_ser.get_list_skills_dto()

        if skills_data is None:
            log.warning(f"")
            await Err.generic_error(call=call)


        text, kb = char_skill_ser.status_group_skill_message(character_skills=skills_data)

        message_data = char_skill_ser.get_message_data()

        char_id, message_id = message_data

        await await_min_delay(start_time, min_delay=0.5)

        if char_id and message_id:
            await bot.edit_message_text(
                chat_id=char_id,
                message_id=message_id,
                text=text,
                reply_markup=kb
            )



    except Exception as e:
        log.warning(f"{e}")










@router.callback_query(StatusSkillsCallback.filter(F.level == "detail"),
                       StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_skill_detail_handler(call: CallbackQuery, state: FSMContext, bot: Bot, callback_data: StatusSkillsCallback) -> None:
    """
    Обрабатывает выбор конкретного навыка (заглушка).

    Args:
        call (CallbackQuery): Callback от кнопки выбора навыка.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.
        callback_data (StatusSkillsCallback): Данные из callback.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Хэндлер 'character_skill_handler' получил обновление без 'from_user'.")
        return
