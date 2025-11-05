#app/services/helpers_module/helper_id_callback.py
import logging
from typing import Optional

from aiogram.types import CallbackQuery

from app.resources.game_data.skill_library import SKILL_UI_GROUPS_MAP

log = logging.getLogger(__name__)

def get_int_id_type(call: CallbackQuery)-> Optional[int]:

    call_data = call.data
    call_data_parts = call_data.split(":")
    char_id_str = call_data_parts[-1]
    if not char_id_str.isdigit():
        return None

    char_id = int(char_id_str)


    return char_id



def get_group_key(call: CallbackQuery) -> Optional[str]:
    """
    Извлекает ключ группы навыков из колбэка и проверяет его наличие
    в SKILL_UI_GROUPS_MAP.
    """
    call_data = call.data
    call_data_parts = call_data.split(":")
    # Предполагаем, что group_key — это последний элемент
    group_key = call_data_parts[-1]

    if group_key in SKILL_UI_GROUPS_MAP:
        return group_key

    return None

def get_type_callback(call: CallbackQuery)-> Optional[str]:
    call_data = call.data
    if call_data:
        call_data_parts = call_data.split(":")

        type_call_data = call_data_parts[-2]
    else:
        type_call_data = "bio"

    return type_call_data






async def error_int_id(call: CallbackQuery):


    await call.answer()

    # 💡 Метка для будущего Reply Keyboard
    await call.message.answer(
        f"Произошел сбой. Данные не прошли валидацию. Попробуйте перезайти через /start",
        # TODO: В будущем здесь будет reply_markup=get_error_reply_kb()
    )


async def error_msg_default(call: CallbackQuery):
    await call.message.answer("Что то пошло не так и данные вашего персонажа не обнаружены")
    # TODO: В будущем здесь будет reply_markup=get_error_reply_kb()
