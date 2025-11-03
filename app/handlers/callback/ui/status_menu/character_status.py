# app/handlers/callback/ui/character_status.py
import logging
from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.resources.fsm_states.states import FSM_CONTEX_CHARACTER_STATUS
from app.services.helpers_module.DTO_helper import fsm_convector
from app.services.helpers_module.helper_id_callback import error_int_id, error_msg_default, get_int_id_type, \
    get_type_callback
from app.services.ui_service.character_status_service import CharacterMenuUIService

router = Router(name="character_status_menu")

log = logging.getLogger(__name__)



@router.callback_query(F.data.startswith("status:bio"),
                       *FSM_CONTEX_CHARACTER_STATUS)
async def status_menu_start_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Ловим callback от кнопки который должен вывести статус персонажа
    идет замена нижнего сообщения контент. Отслеживает все разрешенные статусы в списке
    FSM_CONTEX_CHARACTER_STATUS
    """
    state_data = await state.get_data()
    char_id = get_int_id_type(call=call)
    call_type = get_type_callback(call=call)

    if char_id is None:
        # вызываем функцию хелпер ошибки айди
        log.error(f"Ошибка: ID персонажа не найден в callback_data: {call.data}")
        await error_int_id(call)
        return

    char_menu_service = CharacterMenuUIService(
            user_id=call.from_user.id,
            char_id=char_id,
            fsm=await state.get_state(),
            call_type=call_type
        )

    # Получаем данные о персонаже по его айди.
    bd_data_status = await char_menu_service.get_bd_data_staus()

    if bd_data_status is None:
        # вызываем функцию ошибки
        await error_msg_default(call)
        return

    message_content = state_data.get("message_content") or None
    character = await fsm_convector(bd_data_status.get("character"),"character")
    character_state = await fsm_convector(bd_data_status.get("character_stats"),"character_stats")

    # Сбор сообщения и клавиатуры
    text, kb = char_menu_service.staus_bio_message(
        character=character,
        stats=character_state,
    )

    try:
        if message_content is None:

            msg = await call.message.answer(text=text, parse_mode='HTML', reply_markup=kb)

            message_content = {
                "message_id": msg.message_id,
                "chat_id": msg.chat.id
            }
        else:
            chat_id = message_content.get("chat_id")
            message_id = message_content.get("message_id")
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode='HTML',
                reply_markup=kb)

        await state.update_data(
            message_content=message_content,
            bd_data_staus=bd_data_status,
            state_fsm=await state.get_state()
        )

        log.info(f"status_menu_start_handler закончил свою работу ")
    except TelegramBadRequest as e:
        # Игнорируем ошибку, если пытаемся отправить тот же самый текст.
        if "message is not modified" in str(e):
            log.debug("Сообщение не изменилось, игнорируем.")
        else:
            log.warning(f"Неожиданная ошибка Telegram API: {e}")
    except Exception as e:
        log.exception(f"Критическая ошибка при обновлении БИО/Статов: {e}")