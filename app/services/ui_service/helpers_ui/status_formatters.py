# app/services/ui_service/helpers_ui/status_formatters.py

from loguru import logger as log


class StatusFormatter:
    """
    Класс-контейнер для статических методов форматирования текста в меню статуса.
    """

    @staticmethod
    def format_character_bio(text_formated: str, actor_name: str) -> str:
        text = f"""
        
        {actor_name}: Выводим статус пользователя
        
        {text_formated}        
        
        """

        log.debug(f"Сформирован текст биографии персонажа (длина: {len(text)}).")
        return text
