# app/handlers/callback/ui/character_status_menu.py
import logging
from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery


from app.services.helpers_module.DTO_helper import fsm_convector
from app.services.helpers_module.helper_id_callback import get_int_id
from app.services.ui_service.character_status_menu_service import CharacterMenuUIService

router = Router(name="character_status_menu")

log = logging.getLogger(__name__)

FSM_CONTEX_CHARACTER_STATUS = [

]

@router.callback_query(F.data.startswith("status:bio"),
                       *FSM_CONTEX_CHARACTER_STATUS)
async def status_menu_start_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Ловим callback от кнопки который должен вывести статус персонажа
    идет замена нижнего сообщения контент. Отслеживает все разрешенные статусы в списке
    FSM_CONTEX_CHARACTER_STATUS
    """
    state_data = await state.get_data()
    char_id = get_int_id(call=call)

    if char_id is None:
        log.error(f"Ошибка: ID персонажа не найден в callback_data: {call.data}")
        await call.answer()

        # 💡 Метка для будущего Reply Keyboard
        await call.message.answer(
            f"Произошел сбой. Данные не прошли валидацию. Попробуйте перезайти через /start",
            # TODO: В будущем здесь будет reply_markup=get_error_reply_kb()
        )
        return

    char_menu_service = CharacterMenuUIService(
            user_id=call.from_user.id,
            char_id=char_id,
            fsm=await state.get_state()
        )

    # Получаем данные о персонаже по его айди.
    bd_data_status = await char_menu_service.get_bd_data_staus()

    if bd_data_status is None:
        await call.message.answer("Что то пошло не так и данные вашего персонажа не обнаружены")
        # TODO: В будущем здесь будет reply_markup=get_error_reply_kb()
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
                "chat_id": msg.chat.id}
        else:
            chat_id = message_content.get("chat_id")
            message_id = message_content.get("message_id")
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode='HTML',
                reply_markup=kb)

        await state.update_data(message_content=message_content, bd_data_staus=bd_data_status)

    except TelegramBadRequest as e:
        # Игнорируем ошибку, если пытаемся отправить тот же самый текст.
        if "message is not modified" in str(e):
            log.debug("Сообщение не изменилось, игнорируем.")
        else:
            log.warning(f"Неожиданная ошибка Telegram API: {e}")
    except Exception as e:
        log.exception(f"Критическая ошибка при обновлении БИО/Статов: {e}")