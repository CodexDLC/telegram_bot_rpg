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
    def format_character_list(characters: list[CharacterReadDTO] | list[dict[str, str]]) -> str:
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


    @staticmethod
    def format_character_bio(character: CharacterReadDTO) -> str:
        """
        [ТВОЯ ЗАДАЧА 2]
        Форматирует детальное "Био" (для "Якоря" ПОСЛЕ выбора).
        Это представление по умолчанию при инспекции.
        """

        name = character.name
        gender = Buttons.GENDER.get(f"gender:{character.gender}", "Не указан")
        data = character.created_at

        text = f"""
        
        ℹ️ Статус персонажа:
        
                <b>Имя:</b>             <i>{name}</i>
                <b>Пол:</b>             <i>{gender}</i>
                <b>Дата:</b>            <i>{data}</i>
 
        
        <b></b>Просмотреть более потребные данные персонажа можно переключая вкладки на клавиатуре.
        такие как S.P.E.C.I.A.L - stats, Навыки, Экипировка, Достижения, и другие. дополним потом 
        
        """

        return text

    @staticmethod
    def format_character_stats(stats: dict[str, int] | CharacterStatsReadDTO) -> str:
        """
        Форматирует "Статы" S.P.E.C.I.A.L.
        """

        log.debug(f"stats: {stats}")
        # Если это DTO, получаем значения через getattr, иначе через .get()
        # Но для простоты, если stats это dict (как в логах), .get() безопасен.
        # Если stats *гарантированно* DTO, getattr(stats, 'strength', 0) был бы лучше.
        # Оставим .get() для универсальности, как ты и делал.
        if isinstance(stats, dict):
            s = stats.get("strength", 0)
            p = stats.get("perception", 0)
            e = stats.get("endurance", 0)
            c = stats.get("charisma", 0)
            i = stats.get("intelligence", 0)
            a = stats.get("agility", 0)
            l = stats.get("luck", 0)
        else:
            s = getattr(stats, 'strength', 0)
            p = getattr(stats, 'perception', 0)
            e = getattr(stats, 'endurance', 0)
            c = getattr(stats, 'charisma', 0)
            i = getattr(stats, 'intelligence', 0)
            a = getattr(stats, 'agility', 0)
            l = getattr(stats, 'luck', 0)


        # Используем <code> для моноширинного выравнивания
        # Длина "E (Выносливость) " = 17 символов, остальные подогнаны
        text = f"""
    ℹ️ Статус персонажа: S.P.E.C.I.A.L
    <code>
    S (Сила)         : {s}
    P (Восприятие)   : {p}
    E (Выносливость) : {e}
    C (Харизма)      : {c}
    I (Интеллект)    : {i}
    A (Ловкость)     : {a}
    L (Удача)        : {l}
    </code>
    <i>(Тут будет описание, за что отвечает каждый стат)</i>
    """
        return text