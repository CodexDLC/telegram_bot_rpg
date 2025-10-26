# app/services/game_validator.py
from typing import Tuple, Optional
import re

from app.resources.texts.profanity_list import FORBIDDEN_WORDS

# --- Правила игры ---
MIN_NAME_LENGTH = 3
MAX_NAME_LENGTH = 16

NAME_PATTERN = re.compile(r"^[a-zA-Zа-яА-Я0-9]+$")



def validate_character_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Проверяет имя персонажа на соответствие правилам (длина, символы).
    Возвращает (True/False, Сообщение об ошибке)
    """
    name = name.strip()  # Убираем пробелы в начале/конце
    name_len = len(name)

    if not name:
        return False, "Имя не может быть пустым. Введите от 3 до 16 символов."

    if name_len < MIN_NAME_LENGTH:
        return (False,
                f"Имя слишком короткое. Минимальная длина — {MIN_NAME_LENGTH} символа."
                )

    if name_len > MAX_NAME_LENGTH:
        return (False,
                f"Имя слишком длинное. Максимальная длина — {MAX_NAME_LENGTH} символов."
                )

    if not NAME_PATTERN.match(name):
        return (False,
                "Имя содержит недопустимые символы. Разрешены только буквы и цифры."
                )

    name_lower = name.lower()

    if name_lower in FORBIDDEN_WORDS:
        return False, "Это имя зарезервировано или запрещено."

    for word in FORBIDDEN_WORDS:
        if word in name_lower:
            return False, "Имя содержит недопустимую комбинацию символов."

    return True, None