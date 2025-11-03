# skill_formatters
import logging
from typing import Any

log = logging.getLogger(__name__)


class SkillFormatters:


    @staticmethod
    def group_skill(data: dict[str, dict[str, str]], char_name: str) -> str | None:
        """
        Форматирует текс для первого сообщения навыков.
        Выводим список группы навыков

        :return: text
        """
        if data is None:
            log.error(f"данных нету внутри словаря")
            return None

        formatted_lines = []

        formatted_lines.append("<code>")
        formatted_lines.append(f"{'Группа':<25} | Количество")
        formatted_lines.append("-" * 31)

        for group, value in data.items():
            line = f"{value.get('title_ru'):<25} | {len(value.get('skills'))}"

            formatted_lines.append(line)

        formatted_lines.append("</code>")

        table_text = "\n".join(formatted_lines)

        final_message_text = f"""
        
        Персонаж: <b>{char_name}</b>

    Твои способности сгруппированы в {len(data)} основных категорий.
    Выбери группу ниже, чтобы увидеть состав и прогресс навыков группы.
    
    {table_text}

        """
        return final_message_text


    @staticmethod
    def format_skill_list_in_group(
            data: dict[str, dict[str, str]],
            group_type: str,
            char_name: str,
            character_skill: list[dict[str, Any]]
    ):
        """
        :return: Текс для сообщения со скилами группы
        """
        if data is None:
            log.error(f"данных нету внутри словаря")
            return None

        group_dict = data.get(group_type)
        skill_dict = group_dict.get("skills")

        formatted_lines = []

        formatted_lines.append("<code>")
        formatted_lines.append(f"{'Навык':<25} | Прогрессия")
        formatted_lines.append("-" * 37)

        for skill in character_skill:
            skill_key = skill["skill_key"]
            if skill_key in skill_dict:
                line = f"{skill_dict.get(skill_key):<25} | {skill.get('progress_state')}"

                formatted_lines.append(line)

        formatted_lines.append("</code>")

        table_text = "\n".join(formatted_lines)

        final_message_text = f"""

                Персонаж: <b>{char_name}</b>
                Группа: {group_dict.get('title_ru')}

    В это группе  {len(skill_dict)} навыков. 
    Выбери навык ниже, чтобы увидеть прогресс, детали и изменить состояние.

    {table_text}
    """

        return final_message_text


    @staticmethod
    def format_skill_text(


    ):

        pass