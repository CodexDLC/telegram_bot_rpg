# skill_formatters
import logging
from typing import Any, Dict, Union

log = logging.getLogger(__name__)


class SkillFormatters:

    @staticmethod
    def group_skill(data: Dict[str, Dict[str, str]], char_name: str, actor_name: str) -> Union[str, None]:
        """
        Форматирует текст для первого сообщения навыков.
        Использует идею "числа впереди" для надежного выравнивания.
        Число навыков выравнивается по правому краю,
        затем идет разделитель и название группы.
        """
        if data is None:
            log.error("Нет данных в словаре.")
            return None

        # --- Новая, упрощенная логика ---

        # Задаем ширину колонки для чисел.
        # 3 знака = безопасно для чисел до 999.
        number_width = 3
        separator = " | "

        formatted_lines = []
        formatted_lines.append("<code>")

        # 1. Заголовок
        header_num = "№"
        header_title = "Группа"
        # Выравниваем "№" по правому краю, так же, как будут идти числа
        header_line = f"{header_num:>{number_width}}{separator}{header_title}"
        formatted_lines.append(header_line)

        # 2. Разделительная линия
        # Делаем ее простой, на основе ширины заголовка
        # (Можно и убрать, если не нравится)
        separator_line = f"{'─' * number_width}{separator}{'─' * 15}"
        formatted_lines.append(separator_line)

        # 3. Данные
        for group, value in data.items():
            title = value.get("title_ru", "Без имени")  # Добавим "Без имени" на всякий случай
            skills_count = len(value.get("skills", {}))

            # Опционально: обрезка слишком длинных названий, чтобы они не переносились
            # Можно увеличить лимит или убрать, если перенос строк - это нормально
            max_title_width = 35
            if len(title) > max_title_width:
                title = title[:max_title_width - 1] + "…"

            line = f"{skills_count:>{number_width}}{separator}{title}"
            formatted_lines.append(line)

        formatted_lines.append("</code>")

        table_text = "\n".join(formatted_lines)

        # Текст самого сообщения не меняем
        final_message_text = f"""                  
        
    {actor_name}: ❗ Инициация данных
    
    {actor_name}: Ваши способности сгруппированы в {len(data)} основных категориях.
        
                          
    <code> 
    <b>Имя персонажа:</b> {char_name}
    </code>    
    {table_text}
    """

        return final_message_text

    @staticmethod
    def format_skill_list_in_group(
            data: dict[str, dict[str, str]],
            group_type: str,
            char_name: str,
            actor_name:str,
            view_mode: str,
            character_skill: list[dict[str, Any]]
    ):
        """
        Форматирует сообщение со списком навыков выбранной группы
        """
        if data is None:
            log.error("Нет данных в словаре.")
            return None


        bonus_text = f"{actor_name} Выбери навык ниже, чтобы увидеть прогресс, детали и изменить состояние."

        group_dict = data.get(group_type)
        skill_dict = group_dict.get("skills")

        formatted_lines = []

        # Используем ровную псевдографику │ вместо обычного |
        formatted_lines.append("<code>")
        formatted_lines.append(f"{'Навык':<25} │ Прогрессия")
        formatted_lines.append("─" * 37)

        for skill in character_skill:
            skill_key = skill["skill_key"]
            if skill_key in skill_dict:
                skill_name = skill_dict.get(skill_key)
                progress = skill.get('progress_state')
                line = f"{skill_name:<25} │ {progress}"
                formatted_lines.append(line)

        formatted_lines.append("</code>")

        table_text = "\n".join(formatted_lines)

        final_message_text = f"""
    
    {actor_name}:  В этой группе {len(skill_dict)} навыков.
    {"" if view_mode == "lobby" else bonus_text}    
    
    <code>    
    <b>Персонаж:</b> {char_name}
    <b>Группа:</b> {group_dict.get('title_ru')}
    </code>     
    {table_text}
    """

        return final_message_text


    @staticmethod
    def format_skill_text(


    ):

        pass