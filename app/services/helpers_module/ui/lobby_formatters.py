# app/services/helpers_module/ui/lobby_formatters.py


from app.resources.models.character_dto import CharacterReadDTO, CharacterStatsReadDTO
from app.resources.texts.buttons_callback import Buttons


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
    def format_character_bio(character: dict[str, str] | CharacterReadDTO) -> str:
        """
        [ТВОЯ ЗАДАЧА 2]
        Форматирует детальное "Био" (для "Якоря" ПОСЛЕ выбора).
        Это представление по умолчанию при инспекции.
        """
        if isinstance(character, CharacterReadDTO):
            name = character.name
            gender = Buttons.GENDER.get(f"gender:{character.gender}", "Не указан")
            data = character.created_at
        else:
            name = character.get("name")
            gender = Buttons.GENDER.get(f"gender:{character.get('gender')}", "Не указан")
            data = character.get("created_at")






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
    def format_character_stats(stats: dict[str, int]) -> str:
        """
        [ТВОЯ ЗАДАЧА 3, НА БУДУЩЕЕ]
        Форматирует "Статы" (для информации, когда игрок нажмет
        на клавиатуре "Статы").
        """

        text = f"""

        ℹ️ Статус персонажа: S.P.E.C.I.A.L
        
                <b>Сила:</b>             <i>{stats.get("strength")}</i>
                   отвечает за:
                <b>Ловкость:</b>         <i>{stats.get("agility")}</i>
                   отвечает за:
                <b>Выносливость:</b>     <i>{stats.get("endurance")}</i>
                   отвечает за:
                <b>Харизма:</b>          <i>{stats.get("charisma")}</i>
                   отвечает за:
                <b>Интеллект:</b>        <i>{stats.get("intelligence")}</i>
                   отвечает за:
                <b>Выносливость:</b>     <i>{stats.get("perception")}</i>
                   отвечает за:
                <b>Ловкость:</b>         <i>{stats.get("luck")}</i>   

        """
        return text