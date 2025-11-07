# app/handlers/callback/ui/status_menu/character_skill.py
import logging
import time

from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.resources.fsm_states.states import FSM_CONTEX_CHARACTER_STATUS
from app.resources.keyboards.callback_data import StatusMenuCallback, SkillMenuCallback
from app.resources.texts.ui_messages import TEXT_AWAIT
from app.services.helpers_module.get_data_handlers.status_data_helper import get_status_data_package
from app.services.helpers_module.callback_exceptions import error_int_id, error_msg_default
from app.services.ui_service.character_skill_service import CharacterSkillStatusService
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay

log = logging.getLogger(__name__)

router = Router(name="character_skill_menu")


@router.callback_query(
    StatusMenuCallback.filter(F.action == "skills"),
    StateFilter(*FSM_CONTEX_CHARACTER_STATUS)
)
async def character_skill_status_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    callback_data: StatusMenuCallback
) -> None:
    """
    Обрабатывает вход в меню навыков персонажа, отображая группы навыков.

    Args:
        call (CallbackQuery): Callback от кнопки "Навыки".
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.
        callback_data (StatusMenuCallback): Данные из callback.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Хэндлер 'character_skill_status_handler' получил обновление без 'from_user'.")
        return

    user_id = call.from_user.id
    char_id = callback_data.char_id
    log.info(f"Хэндлер 'character_skill_status_handler' [skills] вызван user_id={user_id}, char_id={char_id}")
    await call.message.edit_text(TEXT_AWAIT, parse_mode="html")
    start_time = time.monotonic()

    if not char_id:
        log.warning(f"Не найден char_id в callback_data для user_id={user_id}: {call.data}")
        await error_int_id(call)
        return

    state_data = await state.get_data()
    bd_data_status = state_data.get("bd_data_status")

    if bd_data_status is None or char_id != bd_data_status.get("id"):
        log.info(f"Кэш FSM для user_id={user_id} пуст или неактуален. Загрузка данных для char_id={char_id}.")
        bd_data_status = await get_status_data_package(char_id=char_id, user_id=user_id)
        if not bd_data_status:
            log.warning(f"Не удалось загрузить 'bd_data_status' для char_id={char_id}.")
            await error_msg_default(call)
            return
        await state.update_data(bd_data_status=bd_data_status)
        log.debug(f"Данные 'bd_data_status' для char_id={char_id} сохранены в FSM.")

    char_skill_service = CharacterSkillStatusService(
        char_id=char_id,
        call_type=callback_data.action,
        view_mode=callback_data.view_mode,
        character=bd_data_status.get("character"),
        character_skill=bd_data_status.get("character_progress_skill"),
    )

    text, kb = char_skill_service.data_message_all_group_skill()
    log.debug(f"Сгенерирован список групп навыков для char_id={char_id}.")

    message_content = state_data.get("message_content")
    if message_content:
        await await_min_delay(start_time, min_delay=0.5)
        await bot.edit_message_text(
            chat_id=message_content.get("chat_id"),
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode='HTML',
            reply_markup=kb
        )
        log.debug(f"Сообщение {message_content.get('message_id')} обновлено списком групп навыков.")
    else:
        log.error(f"Не найден 'message_content' в FSM для user_id={user_id} в 'character_skill_status_handler'.")


@router.callback_query(SkillMenuCallback.filter(F.level == "group"),
                       StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_skill_group_handler(
        call: CallbackQuery,
        state: FSMContext,
        bot: Bot,
        callback_data: SkillMenuCallback
) -> None:
    """
    Обрабатывает выбор группы навыков, отображая навыки в этой группе.

    Args:
        call (CallbackQuery): Callback от кнопки выбора группы.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.
        callback_data (SkillMenuCallback): Данные из callback.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Хэндлер 'character_skill_group_handler' получил обновление без 'from_user'.")
        return

    group_type = callback_data.value
    char_id = callback_data.char_id
    user_id = call.from_user.id
    log.info(f"Хэндлер 'character_skill_group_handler' [group:{group_type}] вызван user_id={user_id}, char_id={char_id}")
    await call.message.edit_text(TEXT_AWAIT, parse_mode="html")
    start_time = time.monotonic()

    if not group_type:
        log.warning(f"Не найден 'group_type' в callback_data для user_id={user_id}: {call.data}")
        await error_int_id(call)
        return

    state_data = await state.get_data()
    bd_data_status = state_data.get("bd_data_status")

    if bd_data_status is None or char_id != bd_data_status.get("id"):
        log.info(f"Кэш FSM для user_id={user_id} пуст или неактуален. Загрузка данных для char_id={char_id}.")
        bd_data_status = await get_status_data_package(char_id=char_id, user_id=user_id)
        if not bd_data_status:
            log.warning(f"Не удалось загрузить 'bd_data_status' для char_id={char_id}.")
            await error_msg_default(call)
            return
        await state.update_data(bd_data_status=bd_data_status)
        log.debug(f"Данные 'bd_data_status' для char_id={char_id} сохранены в FSM.")

    char_skill_service = CharacterSkillStatusService(
        char_id=char_id,
        character=bd_data_status.get("character"),
        character_skill=bd_data_status.get("character_progress_skill"),
        call_type=state_data.get("call_type"),
        view_mode=callback_data.view_mode
    )

    text, kb = char_skill_service.data_message_group_skill(group_type=group_type)
    log.debug(f"Сгенерирован список навыков группы '{group_type}' для char_id={char_id}.")

    message_content = state_data.get("message_content")
    if message_content:
        await await_min_delay(start_time, min_delay=0.5)
        await bot.edit_message_text(
            chat_id=message_content.get("chat_id"),
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode='HTML',
            reply_markup=kb
        )
        log.debug(f"Сообщение {message_content.get('message_id')} обновлено списком навыков.")
    else:
        log.error(f"Не найден 'message_content' в FSM для user_id={user_id} в 'character_skill_group_handler'.")


@router.callback_query(SkillMenuCallback.filter(F.level == "detail"),
                       StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_skill_handler(call: CallbackQuery, state: FSMContext, bot: Bot, callback_data: SkillMenuCallback) -> None:
    """
    Обрабатывает выбор конкретного навыка (заглушка).

    Args:
        call (CallbackQuery): Callback от кнопки выбора навыка.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.
        callback_data (SkillMenuCallback): Данные из callback.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Хэндлер 'character_skill_handler' получил обновление без 'from_user'.")
        return

    skill_key = callback_data.value
    user_id = call.from_user.id
    log.info(f"Хэндлер 'character_skill_handler' [detail:{skill_key}] вызван user_id={user_id} (заглушка).")
    await call.answer(f"⚠️ Информация о навыке '{skill_key}' в разработке.", show_alert=True)
    pass
