# app/services/ui_service/helpers_ui/status_formatters.py
import logging
from typing import Optional, Any

from app.resources.schemas_dto.character_dto import CharacterStatsReadDTO, CharacterReadDTO
from app.resources.texts.buttons_callback import Buttons

log = logging.getLogger(__name__)


class StatusFormatter:
    """
    Класс-контейнер для статических методов форматирования текста в меню статуса.
    """

    @staticmethod
    def format_character_bio(
            text_formated: str,
            actor_name: str
    ) -> str:


        text = f"""
        
        {actor_name}: Выводим статус пользователя
        
        {text_formated}        
        
        """



        log.debug(f"Сформирован текст биографии персонажа (длина: {len(text)}).")
        return text



