# app/services/helpers_module/game_validator.py
from loguru import logger as log
import re
from typing import Tuple, Optional

from app.resources.texts.profanity_list import FORBIDDEN_WORDS


# --- Правила валидации имени персонажа ---
MIN_NAME_LENGTH = 3
MAX_NAME_LENGTH = 16
# Паттерн разрешает только буквы (латиница и кириллица) и цифры.
# Пробелы, дефисы и другие знаки запрещены.
NAME_PATTERN = re.compile(r"^[a-zA-Zа-яА-Я0-9]+$")


def validate_character_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Проверяет имя персонажа на соответствие игровым правилам.

    Выполняет следующие проверки:
    1. Длина имени (от 3 до 16 символов).
    2. Допустимые символы (только буквы и цифры).
    3. Наличие в списке запрещенных слов или их частей.

    Args:
        name (str): Имя персонажа для проверки.

    Returns:
        Tuple[bool, Optional[str]]: Кортеж, где первый элемент - результат
                                    валидации (True/False), а второй -
                                    сообщение об ошибке, если валидация
                                    не пройдена.
    """
    original_name = name
    name = name.strip()
    name_len = len(name)
    log.debug(f"Начало валидации имени: '{original_name}' (обработанное: '{name}').")

    if not name:
        error_msg = "Имя не может быть пустым."
        log.debug(f"Валидация провалена: {error_msg}")
        return False, error_msg

    if not (MIN_NAME_LENGTH <= name_len <= MAX_NAME_LENGTH):
        error_msg = f"Длина имени должна быть от {MIN_NAME_LENGTH} до {MAX_NAME_LENGTH} символов."
        log.debug(f"Валидация провалена: {error_msg} (текущая длина: {name_len}).")
        return False, error_msg

    if not NAME_PATTERN.match(name):
        error_msg = "Имя содержит недопустимые символы. Разрешены только буквы и цифры."
        log.debug(f"Валидация провалена: {error_msg} (не соответствует паттерну).")
        return False, error_msg

    name_lower = name.lower()
    # Проверка на полное совпадение с запрещенным словом.
    if name_lower in FORBIDDEN_WORDS:
        error_msg = "Это имя зарезервировано или запрещено."
        log.debug(f"Валидация провалена: {error_msg} (полное совпадение с '{name_lower}').")
        return False, error_msg

    # Проверка на частичное вхождение запрещенного слова.
    for word in FORBIDDEN_WORDS:
        if word in name_lower:
            error_msg = "Имя содержит недопустимую комбинацию символов."
            log.debug(f"Валидация провалена: {error_msg} (найдено вхождение '{word}').")
            return False, error_msg

    log.debug(f"Имя '{name}' успешно прошло валидацию.")
    return True, None
