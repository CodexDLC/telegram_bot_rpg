import re

from loguru import logger as log

from app.resources.texts.profanity_list import FORBIDDEN_WORDS

MIN_NAME_LENGTH = 3
MAX_NAME_LENGTH = 16
NAME_PATTERN = re.compile(r"^[a-zA-Zа-яА-Я0-9]+$")


def validate_character_name(name: str) -> tuple[bool, str | None]:
    """
    Проверяет имя персонажа на соответствие игровым правилам.

    Выполняет следующие проверки:
    1. Длина имени (от 3 до 16 символов).
    2. Допустимые символы (только буквы и цифры).
    3. Отсутствие в списке запрещенных слов или их частей.

    Args:
        name: Имя персонажа для проверки.

    Returns:
        Кортеж `(bool, Optional[str])`, где первый элемент - результат
        валидации (True/False), а второй - сообщение об ошибке, если валидация
        не пройдена, иначе None.
    """
    original_name = name
    name = name.strip()
    name_len = len(name)
    log.debug(f"GameValidator | action=validate_name original='{original_name}' processed='{name}'")

    if not name:
        error_msg = "Имя не может быть пустым."
        log.debug(f"GameValidator | status=failed reason='Empty name' name='{name}'")
        return False, error_msg

    if not (MIN_NAME_LENGTH <= name_len <= MAX_NAME_LENGTH):
        error_msg = f"Длина имени должна быть от {MIN_NAME_LENGTH} до {MAX_NAME_LENGTH} символов."
        log.debug(f"GameValidator | status=failed reason='Invalid length' name='{name}' length={name_len}")
        return False, error_msg

    if not NAME_PATTERN.match(name):
        error_msg = "Имя содержит недопустимые символы. Разрешены только буквы и цифры."
        log.debug(f"GameValidator | status=failed reason='Invalid characters' name='{name}'")
        return False, error_msg

    name_lower = name.lower()
    if name_lower in FORBIDDEN_WORDS:
        error_msg = "Это имя зарезервировано или запрещено."
        log.debug(f"GameValidator | status=failed reason='Forbidden word (exact match)' name='{name}'")
        return False, error_msg

    for word in FORBIDDEN_WORDS:
        if word in name_lower:
            error_msg = "Имя содержит недопустимую комбинацию символов."
            log.debug(
                f"GameValidator | status=failed reason='Forbidden word (partial match)' name='{name}' found_word='{word}'"
            )
            return False, error_msg

    log.debug(f"GameValidator | status=success name='{name}'")
    return True, None
