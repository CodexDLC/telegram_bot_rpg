# app/services/helpers_module/ui/lobby_formatters.py
import logging

from app.resources.schemas_dto.character_dto import CharacterReadDTO, CharacterStatsReadDTO
from app.resources.texts.buttons_callback import Buttons

log = logging.getLogger(__name__)

class LobbyFormatter:
    """
    Группирует статические методы для форматирования UI
    в состоянии CharacterLobby.
    """

    @staticmethod
    def format_character_list(characters: list[CharacterReadDTO]) -> str:
        """
        Форматирует ОБЩИЙ список персонажей (для "Якоря" до выбора).
        Принимает: Список DTO персонажей.

        """

        char_list_text = []

        for char in characters:
            name   = char.name or "- Пусто -"
            gender = Buttons.GENDER.get(f"gender:{char.gender}", "Не указан")
            char_list_text.append(
                f"<b>Персонаж:</b> {name}\n"
                f"<i>Пол:</i> {gender}"
            )

        text = """
            Твои персонажи:
            
            """
        text += "\n\n".join(char_list_text)

        return text

