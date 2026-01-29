# # app/services/ui_service/helpers_ui/skill_formatters.py
# from typing import Any
#
# from loguru import logger as log
#
# from apps.shared.schemas_dto import SkillDisplayDTO, SkillProgressDTO
# from apps.game_core.modules.skill.calculator_service import SkillCalculatorService as SkillCal
#
#
# class SkillFormatters:
#     """
#     Класс-контейнер для статических методов форматирования текста,
#     связанного с навыками персонажа.
#     """
#
#     @staticmethod
#     def group_skill(data: dict[str, str], char_name: str, actor_name: str) -> str | None:
#         """
#         Форматирует текст для отображения списка групп навыков.
#
#         Создает псевдо-таблицу с выравниванием, показывающую доступные
#         группы навыков.
#
#         :param data: Словарь с данными о группах навыков (ключ: название).
#         :param char_name: Имя персонажа.
#         :param actor_name: Имя "рассказчика" (например, имя бота).
#         :return: Готовый текст сообщения или None в случае ошибки.
#         """
#         log.debug(f"Форматирование списка групп навыков для персонажа '{char_name}'.")
#
#         if not data:
#             log.error("Отсутствуют данные о группах навыков для форматирования.")
#             return None
#
#         number_width = 3
#         separator = " | "
#         formatted_lines = ["<code>"]
#
#         # --- Заголовок таблицы ---
#         header_num = "№"
#         header_title = "Группы-навыков"
#         formatted_lines.append(f"{header_num:>{number_width}}{separator}{header_title}")
#         formatted_lines.append(f"{'─' * 28}")
#
#         # --- Строки таблицы ---
#         for i, (group_key, title) in enumerate(data.items(), start=1):
#             formatted_lines.append(f"{i:>{number_width}}{separator}{title}")
#             log.debug(f"  - Группа #{i} '{group_key}': {title}")
#
#         formatted_lines.append("</code>")
#         table_text = "\n".join(formatted_lines)
#
#         # --- Финальный текст сообщения ---
#         final_message_text = (
#             f"{actor_name}: ❗ Инициация данных\n\n"
#             f"{actor_name}: Ваши способности сгруппированы в {len(data)} основных категориях.\n\n"
#             f"<code><b>Имя персонажа:</b> {char_name}</code>\n"
#             f"{table_text}"
#         )
#         log.debug(f"Сформирован текст для групп навыков (длина: {len(final_message_text)}).")
#         return final_message_text
#
#     @staticmethod
#     def format_skill_list_in_group(
#         char_id: int, data_group: dict[str, Any], data_skill: list[SkillProgressDTO], actor_name: str
#     ) -> str | None:
#         """
#         Форматирует сообщение со списком навыков в выбранной группе.
#
#         Создает псевдо-таблицу, показывающую название навыка и его
#         текущий прогресс.
#
#         :param char_id: ID персонажа.
#         :param data_group: Словарь с данными о группе (title, empty_description, items).
#         :param data_skill: Список DTO с прогрессом навыков персонажа.
#         :param actor_name: Имя "рассказчика".
#         :return: Готовый текст сообщения или None в случае ошибки.
#         """
#         group_title = data_group.get("title", "Без названия")
#         log.debug(f"Форматирование списка навыков в группе '{group_title}' для персонажа ID={char_id}.")
#
#         data_group_items = data_group.get("items")
#         if not data_group_items:
#             log.error(f"Отсутствуют 'items' в данных группы '{group_title}'.")
#             return None
#
#         if data_skill:
#             # --- Формирование таблицы ---
#
#             # 1. Задаем ширину (как в Модификаторах)
#             value_width = 8  # 8 хватит для "100.00%"
#             title_width = 24
#             separator = " | "
#
#             formatted_lines = ["<code>"]
#             # 2. Меняем заголовок (Значение | Название)
#             formatted_lines.append(f"{'Прогресс':>{value_width}}{separator}{'Навык':<{title_width}}")
#             formatted_lines.append("─" * 35)  # Чуть длиннее из-за separator
#
#             for skill_dto in data_skill:
#                 # 3. Получаем процент и форматируем его
#                 percentage = SkillCal.get_skill_display_info(skill_dto).percentage
#                 formatted_value = f"{percentage:.2f}%"
#
#                 # 4. Выравниваем значение СПРАВА (как в Модификаторах)
#                 formatted_val_str = f"{formatted_value:>{value_width}}"
#
#                 # 5. Получаем и форматируем Название СЛЕВА (как в Модификаторах)
#                 skill_name = data_group_items.get(skill_dto.skill_key, "Неизвестный навык")
#                 if len(skill_name) > title_width:
#                     formatted_title = skill_name[: (title_width - 3)] + "..."
#                 else:
#                     formatted_title = f"{skill_name:<{title_width}}"  # Выравниваем слева
#
#                 # 6. Собираем строку: ЗНАЧЕНИЕ | НАЗВАНИЕ
#                 formatted_lines.append(f"{formatted_val_str}{separator}{formatted_title}")
#
#                 log.debug(f"  - Навык '{skill_name}': Прогресс '{formatted_value}'")
#
#             formatted_lines.append("</code>")
#             table_text = "\n".join(formatted_lines)
#         else:
#             table_text = data_group.get("empty_description", "У вас пока нет доступных навыков в этой группе.")
#
#         # --- Финальный текст сообщения ---
#         final_message_text = (
#             f"{actor_name}: ❗ Инициация данных\n\n"
#             f"{actor_name}: Вывожу данные о ваших навыках в группе.\n"
#             f"\n"
#             f"<code>"
#             f"<b>Группа:</b> {group_title}"
#             f"</code>\n"
#             f"{table_text}"
#         )
#         log.debug(f"Сформирован текст для списка навыков в группе '{group_title}' (длина: {len(final_message_text)}).")
#         return final_message_text
#
#     @staticmethod
#     def format_detail_skill_message(
#         data: dict[str, Any], skill_dto: SkillProgressDTO, skill_display: SkillDisplayDTO, actor_name: str
#     ) -> str | None:
#         """
#         Форматирует детальное описание конкретного навыка.
#
#         :param data: Словарь с метаданными навыка (title, description, items).
#         :param skill_dto: DTO с прогрессом навыка.
#         :param skill_display: DTO с отображаемыми данными навыка.
#         :param actor_name: Имя "рассказчика".
#         :return: Готовый текст сообщения или None в случае ошибки.
#         """
#         log.debug(
#             f"Форматирование детального описания навыка '{data.get('title')}' для персонажа ID={skill_dto.character_id}."
#         )
#
#         if not all([skill_dto, skill_display, data]):
#             log.error("Отсутствуют полные данные о навыке для форматирования.")
#             return None
#
#         # --- Основная информация ---
#         title = data.get("title", "Навык без имени")
#         description = data.get("description", "Нет описания.")
#         percentage = skill_display.percentage
#         total_xp = skill_dto.total_xp
#         progress_state = skill_dto.progress_state.value
#
#         # --- Формирование списка бонусов/уровней ---
#         item_data = data.get("items", {})
#         bonus_lines = ["<code>"]
#         if item_data:
#             bonus_lines.append("<b>Бонусы уровня:</b>")
#             for threshold, bonus_desc in sorted(item_data.items()):
#                 # Преобразуем ключ-порог в int для сравнения
#                 try:
#                     threshold_val = int(threshold)
#                     mark = "✅" if percentage >= threshold_val else "☑️"
#                     bonus_lines.append(f"  {mark} {threshold_val}%: {bonus_desc}")
#                 except (ValueError, TypeError):
#                     log.warning(f"Неверный ключ '{threshold}' в 'items' для навыка '{title}'. Ожидалось число.")
#                     continue
#         bonus_lines.append("</code>")
#         bonuses_text = "\n".join(bonus_lines)
#
#         # --- Финальный текст сообщения ---
#         final_text = (
#             f"<b>{title}</b>\n\n"
#             f"<i>{actor_name}: {description}</i>\n\n"
#             f"<b>Прогресс:</b>\n"
#             f"<code>"
#             f"├ Прокачка: {percentage}%\n"
#             f"├ Всего опыта: {total_xp}\n"
#             f"└ Режим работы: {progress_state}\n"
#             f"</code>\n"
#             f"{bonuses_text}"
#         )
#         log.debug(f"Сформирован детальный текст для навыка '{title}' (длина: {len(final_text)}).")
#         return final_text
