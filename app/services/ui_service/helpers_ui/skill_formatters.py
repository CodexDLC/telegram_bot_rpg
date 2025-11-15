# app/services/ui_service/helpers_ui/skill_formatters.py
import logging
from typing import Any, Dict, List, Optional

from app.resources.schemas_dto.skill import SkillProgressDTO
from app.services.game_service.skill.calculator_service import SkillCalculatorService as SkillCal

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
            char_id: int,
            data_group: dict[str: Any],
            data_skill: list[SkillProgressDTO],
            actor_name: str
    ) -> Optional[str]:
        """
        Форматирует сообщение со списком навыков в выбранной группе.

        Создает псевдо-таблицу, показывающую название навыка и его
        текущий прогресс (статус).

        Args:
            char_id: int: айди персонажа
            data_group: dict[str: Any] : словарь группы где есть "title", "empty_description","items"
            data_skill: list[SkillProgressDTO]: Словарь с DTO skill персонажа.
            actor_name (str): Имя "рассказчика".

        Returns:
            Optional[str]: Готовый текст сообщения или None в случае ошибки.
        """
        data_group_items = data_group.get("items")

        log.debug(f"Форматирование списка навыков в группе '{data_group_items}' для персонажа '{char_id}'.")
        if not data_group_items:
            log.error("Отсутствуют данные о группах навыков для форматирования.")
            return None

        if data_skill:
            # --- Формирование таблицы ---
            formatted_lines = ["<code>"]
            formatted_lines.append(f"{'Навык':<25} │ Прогрессия")
            formatted_lines.append("─" * 37)

            # Итерируемся по всем возможным навыкам в группе, чтобы сохранить порядок.
            for skill_dto in data_skill:
                percentage = SkillCal.get_skill_display_info(skill_dto).percentage
                skill_name = data_group_items.get(skill_dto.skill_key)

                formatted_lines.append(f"{skill_name:<25} │ {percentage}")
                log.debug(f"  - Навык '{skill_name}': Прогресс '{percentage}'")

            formatted_lines.append("</code>")
            table_text = "\n".join(formatted_lines)

        else:
            table_text = data_group.get("empty_description", "У тебя пока нет навыков в этой группе.")

        # --- Финальный текст сообщения ---
        final_message_text = (
            f"{actor_name}: В этой группе {len(data_skill)} навыков.\n"
            f"<code>"
            f"<b>Группа:</b> {data_group.get('title')}"
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
