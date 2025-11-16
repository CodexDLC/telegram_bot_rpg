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
from app.resources.keyboards.status_callback import StatusSkillsCallback, SkillModeCallback
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
    Обрабатывает нажатие на группу навыков и отображает список навыков в ней.

    :param call: Входящий CallbackQuery.
    :param state: Контекст состояния FSM.
    :param bot: Экземпляр бота.
    :param callback_data: Данные из Callback-кнопки.
    """
    if not call.from_user:
        log.warning("Handler 'character_skill_group_handler' received an update without 'from_user'.")
        return

    start_time = time.monotonic()
    user_id = call.from_user.id
    char_id = callback_data.char_id
    key = callback_data.key
    log.info(f"User {user_id} triggered 'character_skill_group_handler' for char_id={char_id}, key='{key}'.")

    await call.message.edit_text(TEXT_AWAIT, parse_mode="html")

    try:
        char_skill_ser = CharacterSkillStatusService(
            char_id=char_id,
            key=key,
            state_data=await state.get_data()
        )
        skills_data = await char_skill_ser.get_list_skills_dto()

        if skills_data is None:
            log.warning(f"No skill data found for char_id={char_id}. Aborting.")
            await Err.generic_error(call=call)
            return

        text, kb = char_skill_ser.status_group_skill_message(character_skills=skills_data)

        message_data = char_skill_ser.get_message_data()
        chat_id, message_id = message_data

        await await_min_delay(start_time, min_delay=0.5)

        if chat_id and message_id:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=kb
            )

        await state.update_data(group_key=key)
        log.debug(f"Successfully displayed skill group '{key}' for char_id={char_id}.")

    except Exception as e:
        log.error(f"An error occurred in 'character_skill_group_handler' for user {user_id}: {e}", exc_info=True)
        await Err.generic_error(call=call)


@router.callback_query(StatusSkillsCallback.filter(F.level == "detail"),
                       StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_skill_detail_handler(call: CallbackQuery, state: FSMContext, bot: Bot, callback_data: StatusSkillsCallback) -> None:
    """
    Обрабатывает нажатие на конкретный навык и отображает его детальную информацию.

    :param call: Входящий CallbackQuery.
    :param state: Контекст состояния FSM.
    :param bot: Экземпляр бота.
    :param callback_data: Данные из Callback-кнопки.
    """
    if not call.from_user:
        log.warning("Handler 'character_skill_detail_handler' received an update without 'from_user'.")
        return

    start_time = time.monotonic()
    user_id = call.from_user.id
    char_id = callback_data.char_id
    key = callback_data.key
    log.info(f"User {user_id} triggered 'character_skill_detail_handler' for char_id={char_id}, key='{key}'.")

    state_data = await state.get_data()
    if not state_data:
        log.warning(f"State data is missing for user {user_id} in 'character_skill_detail_handler'.")
        await Err.callback_data_missing(call=call)
        return

    group_key = state_data.get("group_key")

    if not group_key:
        log.warning(f"'group_key' is missing in state data for user {user_id}.")
        await Err.callback_data_missing(call=call)
        return

    try:
        char_skill_ser = CharacterSkillStatusService(
            char_id=char_id,
            key=key,
            state_data=state_data
        )
        skills_data = await char_skill_ser.get_list_skills_dto()

        if skills_data is None:
            log.warning(f"No skill data found for char_id={char_id}. Aborting detail view.")
            await Err.generic_error(call=call)
            return

        text, kb = char_skill_ser.status_detail_skill_message(
            group_key=group_key,
            skills_dto=skills_data
        )

        message_data = char_skill_ser.get_message_data()
        chat_id, message_id = message_data

        await await_min_delay(start_time, min_delay=0.5)

        if chat_id and message_id:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode="html",
                reply_markup=kb
            )
        log.debug(f"Successfully displayed skill detail '{key}' for char_id={char_id}.")

    except Exception as e:
        log.error(f"An error occurred in 'character_skill_detail_handler' for user {user_id}: {e}", exc_info=True)
        await Err.generic_error(call=call)


@router.callback_query(SkillModeCallback.filter(),
                       StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_skill_mode_handler(
        call: CallbackQuery,
        state: FSMContext,
        bot: Bot,
        callback_data: SkillModeCallback
) -> None:
    """
    Обрабатывает изменение режима прокачки и ПОЛНОСТЬЮ ОБНОВЛЯЕТ
    сообщение, чтобы показать новое состояние.
    """
    if not call.from_user:
        log.warning("Handler 'character_skill_mode_handler' received update without 'from_user'.")
        return

    user_id = call.from_user.id
    log.info(f"User {user_id} changing skill '{callback_data.skill_key}' to '{callback_data.new_mode}'.")

    await call.answer(f"Режим изменен на: {callback_data.new_mode}")

    try:
        # 1. Получаем 'group_key' из FSM (он нужен для 'Назад')
        state_data = await state.get_data()
        group_key = state_data.get("group_key")  # (Убедись, что опечатка 'groupe_key' исправлена)
        if not group_key:
            raise ValueError("group_key не найден в FSM, не могу построить 'Назад'")

        # 2. Создаем сервис (ему нужен FSM state для super())
        char_skill_ser = CharacterSkillStatusService(
            char_id=callback_data.char_id,
            key=callback_data.skill_key,  # key - это ключ навыка (e.g., 'melee_combat')
            state_data=state_data
        )

        # 3. Обновляем БД (как ты и написал)
        await char_skill_ser.set_mode_skill(mode=callback_data.new_mode)

        # 4. ПОЛУЧАЕМ ОБНОВЛЕННЫЕ ДАННЫЕ
        # Нам нужно заново получить DTO, чтобы увидеть новое состояние
        skills_data = await char_skill_ser.get_list_skills_dto()
        if not skills_data:
            raise ValueError("Не удалось получить DTO навыков после обновления")

        # 5. ГЕНЕРИРУЕМ НОВЫЙ ТЕКСТ И КЛАВИАТУРУ
        # (Вызываем тот же метод, что и 'character_skill_detail_handler')
        text, kb = char_skill_ser.status_detail_skill_message(
            group_key=group_key,  # Ключ группы (e.g., 'combat_base')
            skills_dto=skills_data
        )

        # 6. ПЕРЕРИСОВЫВАЕМ СООБЩЕНИЕ
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode="html",
            reply_markup=kb
        )
        log.debug("Сообщение с деталями навыка успешно обновлено.")

    except Exception as e:
        log.error(f"Ошибка в skill_mode_handler: {e}", exc_info=True)
        # Так как мы уже сделали call.answer(), здесь можно просто
        # отправить 'тревожное' сообщение, если что-то пошло не так
        await call.answer("Произошла ошибка при смене режима.", show_alert=True)




