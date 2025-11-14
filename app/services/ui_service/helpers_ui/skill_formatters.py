# app/services/ui_service/helpers_ui/skill_formatters.py
import logging
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


class SkillFormatters:
    """
    Класс-контейнер для статических методов форматирования текста в меню навыков.
    """

    @staticmethod
    def group_skill(data: Dict[str, str], char_name: str, actor_name: str) -> Optional[str]:
        """
        Форматирует текст для отображения списка групп навыков.

        Создает псевдо-таблицу с выравниванием, показывающую количество
        навыков в каждой группе.

        Args:
            data (Dict[str, Dict[str, Any]]): Словарь с данными о группах
                навыков (из `skill_library.py`).
            char_name (str): Имя персонажа.
            actor_name (str): Имя "рассказчика".

        Returns:
            Optional[str]: Готовый текст сообщения или None в случае ошибки.
        """
        log.debug(f"Форматирование списка групп навыков для персонажа '{char_name}'.")
        if not data:
            log.error("Отсутствуют данные о группах навыков для форматирования.")
            return None

        number_width = 3
        separator = " | "
        formatted_lines = ["<code>"]

        # --- Заголовок таблицы ---
        header_num = "№"
        header_title = "Группа"
        formatted_lines.append(f"{header_num:>{number_width}}{separator}{header_title}")
        formatted_lines.append(f"{'─' * number_width}{separator}{'─' * 15}")

        # --- Строки таблицы ---
        for group_key, group_value in data.items():
            title = group_value
            skills_count = len(data)
            formatted_lines.append(f"{skills_count:>{number_width}}{separator}{title}")
            log.debug(f"  - Группа '{group_key}': {title}, Навыков: {skills_count}")

        formatted_lines.append("</code>")
        table_text = "\n".join(formatted_lines)

        # --- Финальный текст сообщения ---
        final_message_text = (
            f"{actor_name}: ❗ Инициация данных\n\n"
            f"{actor_name}: Ваши способности сгруппированы в {len(data)} основных категориях.\n\n"
            f"<code><b>Имя персонажа:</b> {char_name}</code>\n"
            f"{table_text}"
        )
        log.debug(f"Сформирован текст для групп навыков (длина: {len(final_message_text)}).")
        return final_message_text

    @staticmethod
    def format_skill_list_in_group(
            data: Dict[str, Dict[str, Any]],
            group_type: str,
            char_name: str,
            actor_name: str,
            view_mode: str,
            character_skill: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Форматирует сообщение со списком навыков в выбранной группе.

        Создает псевдо-таблицу, показывающую название навыка и его
        текущий прогресс (статус).

        Args:
            data (Dict[str, Dict[str, Any]]): Словарь с данными о группах навыков.
            group_type (str): Ключ выбранной группы.
            char_name (str): Имя персонажа.
            actor_name (str): Имя "рассказчика".
            view_mode (str): Режим просмотра ("lobby" или "ingame").
            character_skill (List[Dict[str, Any]]): Список навыков персонажа из БД.

        Returns:
            Optional[str]: Готовый текст сообщения или None в случае ошибки.
        """
        log.debug(f"Форматирование списка навыков в группе '{group_type}' для персонажа '{char_name}'.")
        if not data:
            log.error("Отсутствуют данные о группах навыков для форматирования.")
            return None

        group_dict = data.get(group_type)
        if not group_dict:
            log.error(f"Группа '{group_type}' не найдена в данных SKILL_UI_GROUPS_MAP.")
            return "Ошибка: не найдена указанная группа навыков."

        skill_dict = group_dict.get("skills", {})
        bonus_text = (
            f"{actor_name}: Выбери навык ниже, чтобы увидеть прогресс, "
            "детали и изменить состояние."
        )

        # --- Формирование таблицы ---
        formatted_lines = ["<code>"]
        formatted_lines.append(f"{'Навык':<25} │ Прогрессия")
        formatted_lines.append("─" * 37)

        # Создаем словарь для быстрого доступа к прогрессу по ключу навыка.
        skill_progress_map = {skill["skill_key"]: skill.get('progress_state', 'N/A')
                              for skill in character_skill}
        log.debug(f"Карта прогресса навыков для персонажа: {skill_progress_map}")

        # Итерируемся по всем возможным навыкам в группе, чтобы сохранить порядок.
        for skill_key, skill_name in skill_dict.items():
            progress = skill_progress_map.get(skill_key, 'Нет')
            formatted_lines.append(f"{skill_name:<25} │ {progress}")
            log.debug(f"  - Навык '{skill_name}': Прогресс '{progress}'")

        formatted_lines.append("</code>")
        table_text = "\n".join(formatted_lines)

        # --- Финальный текст сообщения ---
        final_message_text = (
            f"{actor_name}: В этой группе {len(skill_dict)} навыков.\n"
            f'{"" if view_mode == "lobby" else bonus_text}\n\n'
            f"<code>"
            f"<b>Персонаж:</b> {char_name}\n"
            f"<b>Группа:</b> {group_dict.get('title_ru')}"
            f"</code>\n"
            f"{table_text}"
        )
        log.debug(f"Сформирован текст для списка навыков в группе (длина: {len(final_message_text)}).")
        return final_message_text

    @staticmethod
    def format_skill_text():
        """
        Форматирует детальное описание навыка (заглушка).
        """
        log.debug("Вызван метод-заглушка 'format_skill_text'.")
        pass
