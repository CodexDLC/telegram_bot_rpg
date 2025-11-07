# app/services/ui_service/helpers_ui/lobby_formatters.py
import logging
from typing import List, Optional

from app.resources.schemas_dto.character_dto import CharacterReadDTO
from app.resources.texts.buttons_callback import Buttons

log = logging.getLogger(__name__)


class LobbyFormatter:
    """
    Класс-контейнер для статических методов форматирования текста в лобби.

    Использование статических методов в классе-форматтере позволяет
    логически сгруппировать утилиты для работы с текстом, не создавая
    экземпляр класса.
    """

    @staticmethod
    def format_character_list(characters: Optional[List[CharacterReadDTO]]) -> str:
        """
        Форматирует список персонажей для отображения в лобби.

        Создает текстовое представление всех персонажей пользователя.
        Если у персонажа еще нет имени, отображает "Пусто".

        Args:
            characters (Optional[List[CharacterReadDTO]]): Список DTO
                персонажей. Может быть None или пустым.

        Returns:
            str: Отформатированная строка для отправки в сообщении.
        """
        header = "Твои персонажи:\n\n"
        if not characters:
            return "У тебя пока нет созданных персонажей."

        char_list_parts = []
        for char in characters:
            # Используем "or" для предоставления значения по умолчанию,
            # если имя персонажа еще не задано.
            name = char.name or "- Пусто -"
            gender_key = f"gender:{char.gender}"
            gender = Buttons.GENDER.get(gender_key, "Не указан")

            char_list_parts.append(
                f"<b>Персонаж:</b> {name}\n"
                f"<i>Пол:</i> {gender}"
            )

        # Соединяем отформатированные блоки двойным переносом строки.
        return header + "\n\n".join(char_list_parts)
