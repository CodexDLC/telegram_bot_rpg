#app/services/helpers_module/helper_id_callback.py
from typing import Optional

from aiogram.types import CallbackQuery


def get_int_id(call: CallbackQuery)-> Optional[int]:

    call_data = call.data
    call_data_parts = call_data.split(":")
    char_id_str = call_data_parts[-1]
    if not char_id_str.isdigit():
        return None

    char_id = int(char_id_str)

    return char_id