# app/services/ui_service/helpers_ui/lobby_formatters.py

from loguru import logger as log

from app.resources.schemas_dto.character_dto import CharacterReadDTO
from app.resources.texts.buttons_callback import Buttons


class LobbyFormatter:
    """
    Класс-контейнер для статических методов форматирования текста в лобби.

    Группирует утилиты для работы с текстом, не требуя создания экземпляра.
    """

    @staticmethod
    def format_character_list(characters: list[CharacterReadDTO] | None) -> str:
        """
        Форматирует список персонажей для отображения в лобби.

        Создает текстовое представление всех персонажей пользователя.

        Args:
            characters (Optional[List[CharacterReadDTO]]): Список DTO персонажей.

        Returns:
            str: Отформатированная строка для сообщения.
        """
        log.debug("Форматирование списка персонажей для лобби.")
        header = "<b>Твои персонажи:</b>\n\n"
        if not characters:
            log.debug("Список персонажей пуст. Возвращается сообщение по умолчанию.")
            return "У тебя пока нет созданных персонажей."

        char_list_parts = []
        for i, char in enumerate(characters):
            # Используем значение по умолчанию, если имя еще не задано.
            name = char.name or "<i>(Имя не задано)</i>"
            gender_key = f"gender:{char.gender}"
            gender = Buttons.GENDER.get(gender_key, "Не указан")

            char_info = f"<b>Персонаж #{i + 1}:</b> {name}\n<i>Пол:</i> {gender}"
            char_list_parts.append(char_info)
            log.debug(f"Отформатирован персонаж: id={char.character_id}, name='{name}'.")

        # Соединяем отформатированные блоки двойным переносом строки.
        formatted_string = header + "\n\n".join(char_list_parts)
        log.debug(f"Финальная отформатированная строка (длина: {len(formatted_string)}).")
        return formatted_string
