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
from app.services.helpers_module.helper_id_callback import error_int_id
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
):
    """
    Обрабатывает вход в меню навыков персонажа.

    Эта функция является точкой входа в раздел "Навыки" из меню статуса.
    Она отображает список групп навыков (например, "Боевые", "Ремесленные").

    Args:
        call (CallbackQuery): Входящий callback от кнопки "Навыки".
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.
        callback_data (StatusMenuCallback): Данные из callback-кнопки.

    Returns:
        None
    """
    log.info("character_skill_status_handler начал свою работу")
    await call.message.edit_text(TEXT_AWAIT, parse_mode="html")
    start_time = time.monotonic()

    char_id = callback_data.char_id
    call_type = callback_data.action
    view_mode = callback_data.view_mode

    if char_id is None:
        log.error(f"Ошибка: ID персонажа не найден в callback_data: {call.data}")
        await error_int_id(call)
        return

    state_data = await state.get_data()
    bd_data_status = state_data.get("bd_data_status")
    user_id = state_data.get("user_id")

    # Если полных данных о статусе нет в FSM, загружаем их из БД.
    # Это оптимизация, чтобы не делать лишних запросов при переключении вкладок.
    if bd_data_status is None:
        bd_data_status = await get_status_data_package(char_id=char_id, user_id=user_id)

    char_skill_service = CharacterSkillStatusService(
        char_id=char_id,
        call_type=call_type,
        view_mode=view_mode,
        character=bd_data_status.get("character"),
        character_skill=bd_data_status.get("character_progress_skill"),
    )

    # Получаем текст и клавиатуру со списком групп навыков.
    text, kb = char_skill_service.data_message_all_group_skill()

    message_content = state_data.get("message_content")
    if message_content:
        if start_time:
            await await_min_delay(start_time, min_delay=0.5)

        await bot.edit_message_text(
            chat_id=message_content.get("chat_id"),
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode='HTML',
            reply_markup=kb
        )

    # Сохраняем/обновляем данные в FSM.
    await state.update_data(
        char_id=char_id,
        bd_data_status=bd_data_status
    )
    log.info("character_skill_status_handler Закончил свою работу")


@router.callback_query(SkillMenuCallback.filter(F.level == "group"),
                       StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_skill_group_handler(
        call: CallbackQuery,
        state: FSMContext,
        bot: Bot,
        callback_data: SkillMenuCallback
):
    """
    Обрабатывает выбор группы навыков.

    Эта функция отображает список всех навыков, входящих в выбранную
    пользователем группу (например, все "Боевые" навыки).

    Args:
        call (CallbackQuery): Входящий callback от кнопки выбора группы.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.
        callback_data (SkillMenuCallback): Данные из callback-кнопки.

    Returns:
        None
    """
    await call.message.edit_text(TEXT_AWAIT, parse_mode="html")
    start_time = time.monotonic()
    group_type = callback_data.value
    char_id = callback_data.char_id
    view_mode = callback_data.view_mode

    if group_type is None:
        log.error(f"Ошибка: Тип группы навыков не найден в callback_data: {call.data}")
        await error_int_id(call)
        return

    state_data = await state.get_data()
    user_id = state_data.get("user_id")
    bd_data_status = state_data.get("bd_data_status")

    # Перезагружаем данные, если в FSM их нет или они для другого персонажа.
    if bd_data_status is None or char_id != bd_data_status.get("id"):
        bd_data_status = await get_status_data_package(char_id=char_id, user_id=user_id)

    char_skill_service = CharacterSkillStatusService(
        char_id=char_id,
        character=bd_data_status.get("character"),
        character_skill=bd_data_status.get("character_progress_skill"),
        call_type=state_data.get("call_type"),
        view_mode=view_mode
    )

    # Получаем текст и клавиатуру со списком навыков в выбранной группе.
    text, kb = char_skill_service.data_message_group_skill(group_type=group_type)

    message_content = state_data.get("message_content")
    if message_content:
        if start_time:
            await await_min_delay(start_time, min_delay=0.5)

        await bot.edit_message_text(
            chat_id=message_content.get("chat_id"),
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode='HTML',
            reply_markup=kb
        )

    await state.update_data(
        bd_data_status=bd_data_status,
        user_id=user_id
    )


@router.callback_query(SkillMenuCallback.filter(F.level == "detail"),
                       StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_skill_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Обрабатывает выбор конкретного навыка (заглушка).

    В будущем эта функция будет показывать детальную информацию о выбранном
    навыке, его уровень, описание и, возможно, опции для улучшения.

    Args:
        call (CallbackQuery): Входящий callback от кнопки выбора навыка.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    pass
