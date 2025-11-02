#app/services/helpers_module/ui/lobby_formatters.py
import logging

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.schemas_dto.character_dto import CharacterStatsReadDTO, CharacterReadDTO
from app.resources.texts.buttons_callback import Buttons

log = logging.getLogger(__name__)


class StatusFormatter:
    """
    Группирует методы форматирования текста для меню Статус персонажа.

    """

    @staticmethod
    def format_character_bio(character: CharacterReadDTO, stats: CharacterStatsReadDTO) -> str:
        """
        Форматирует детальное "Био" (для "Якоря" ПОСЛЕ выбора).
        Это представление по умолчанию при инспекции или при нажатии кнопки статус персонажа.

        """
        log.debug(
            f"""
            character равно = {character}
            stats = {stats}            
            """
        )
        s = getattr(stats, 'strength', 0)
        p = getattr(stats, 'perception', 0)
        e = getattr(stats, 'endurance', 0)
        c = getattr(stats, 'charisma', 0)
        i = getattr(stats, 'intelligence', 0)
        a = getattr(stats, 'agility', 0)
        l = getattr(stats, 'luck', 0)

        name = character.name
        gender = Buttons.GENDER.get(f"gender:{character.gender}", "Не указан")
        data = character.created_at

        text = f"""

        ℹ️ Статус персонажа:  -= <i>{name}</i> =-    
        
    <code>
    <b>Пол:</b><i>{gender}</i>     
    <b>Параметры персонажа:</b>
    
    (Сила)         : {s}
    (Восприятие)   : {p}
    (Выносливость) : {e}
    (Харизма)      : {c}
    (Интеллект)    : {i}
    (Ловкость)     : {a}
    (Удача)        : {l}
    
    <b>Дата создания:</b> <i>{data}</i>
    </code>

        """

        return text

