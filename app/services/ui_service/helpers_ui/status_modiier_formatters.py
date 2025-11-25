from typing import Any

from loguru import logger as log

PERCENT_KEYS = {
    "physical_damage_bonus",
    "physical_penetration",
    "physical_crit_chance",
    "magical_damage_bonus",
    "magical_penetration",
    "magical_crit_chance",
    "spell_land_chance",
    "magical_accuracy",
    "dodge_chance",
    "debuff_avoidance",
    "shield_block_chance",
    "physical_resistance",
    "control_resistance",
    "magical_resistance",
    "shock_resistance",
    "trade_discount",
    "find_loot_chance",
    "crafting_critical_chance",
    "skill_gain_bonus",
    "crafting_success_chance",
}


class ModifierFormatters:
    @staticmethod
    def group_modifier(data: dict[str, str], char_name: str, actor_name: str) -> str | None:
        """
        Форматирует текст для отображения списка групп модификаторов.
        """
        log.debug(f"Форматирование списка групп модификаторов для персонажа '{char_name}'.")

        if not data:
            log.error("Отсутствуют данные о группах навыков для форматирования.")
            return None

        number_width = 3
        separator = " | "
        formatted_lines = ["<code>"]

        # --- Заголовок таблицы ---
        header_num = "№"
        header_title = "Группы-модификаторов"
        formatted_lines.append(f"{header_num:>{number_width}}{separator}{header_title}")
        formatted_lines.append(f"{'─' * 28}")

        # --- Строки таблицы ---
        for i, (group_key, title) in enumerate(data.items(), start=1):
            formatted_lines.append(f"{i:>{number_width}}{separator}{title}")
            log.debug(f"  - Группа #{i} '{group_key}': {title}")

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
    def format_stats_list(data: dict[str, Any], dto_to_use: Any, actor_name: str) -> str | None:
        """
        Форматирует список статов ИЛИ модификаторов в <code> таблицу,
        безопасную для мобильных, в формате (Значение | Параметр).
        """
        if not data or not dto_to_use:
            log.error("Отсутствуют данные (data или dto_to_use) для форматирования.")
            return None

        data_items = data.get("items")
        if not data_items:
            log.error("В словаре 'data' не найден ключ 'items'.")
            return None

        # 1. Задаем БЕЗОПАСНУЮ ширину (Total ~ 8 + 3 + 18 = 29)
        # 8 для "100.00%" (влезет)
        # 18 для "❤️ Базовые Харак..." (обрежется)
        value_width = 8
        title_width = 24
        separator = " | "

        formatted_lines = ["<code>"]
        formatted_lines.append(f"{'Знач.':>{value_width}}{separator}{'Параметр':<{title_width}}")
        formatted_lines.append(f"{'─' * 28}")

        # 2. Итерируем и форматируем
        for key, title in data_items.items():
            # key = "strength" или "hp_max"
            # title = "Сила" или "Макс. Здоровье"

            value = getattr(dto_to_use, key, "N/A")

            # 3. Форматируем ЗНАЧЕНИЕ (справа)
            # FIX: Заменено (float, int) на float | int согласно правилу Ruff UP038
            if key in PERCENT_KEYS and isinstance(value, float | int):
                formatted_value = f"{value * 100:.2f}%"
            elif isinstance(value, float):
                formatted_value = f"{value:.2f}"
            else:
                formatted_value = str(value)

                # Выравниваем значение СПРАВА (как ты и просил)
            formatted_val_str = f"{formatted_value:>{value_width}}"

            # 4. Форматируем НАЗВАНИЕ (слева)
            # Обрезаем длинные заголовки, чтобы не сломать таблицу
            formatted_title = (
                (title[: (title_width - 3)] + "...") if len(title) > title_width else f"{title:<{title_width}}"
            )

            # 5. Собираем строку: ЗНАЧЕНИЕ | НАЗВАНИЕ
            formatted_lines.append(f"{formatted_val_str}{separator}{formatted_title}")

        formatted_lines.append("</code>")
        stats_list_text = "\n".join(formatted_lines)

        # 6. Берем title и description (как ты и сказал, "верни верху надписи")
        title = data.get("title", "...")
        description = data.get("description", "...")

        # --- Собираем финальный текст ---
        text = f"<b>{title}</b>\n\n<i>{actor_name}: {description}</i>\n\n{stats_list_text}"

        return text

    @staticmethod
    def format_modifier_detail(
        data: dict[str, Any],  # Данные из MODIFIER_HIERARCHY
        value: Any,  # Значение (e.g., 5.25 или 150)
        key: str,  # Ключ (e.g., "energy_regen")
        actor_name: str,
    ) -> str | None:
        """
        Форматирует "карточку" (Lvl 2) для конкретного модификатора.
        """
        if not data:
            log.error("Отсутствуют данные (data) для форматирования Lvl 2.")
            return None

        # 1. Берем данные из MODIFIER_HIERARCHY
        title = data.get("title", "...")
        description = data.get("description", "...")

        # 2. Форматируем значение (проверяем, нужно ли ставить %)
        # FIX: Заменено (float, int) на float | int согласно правилу Ruff UP038
        if key in PERCENT_KEYS and isinstance(value, float | int):
            formatted_value = f"{value * 100:.2f}%"
        elif isinstance(value, float):
            formatted_value = f"{value:.2f}"
        else:
            formatted_value = str(value)

        # 3. Собираем текст карточки
        # (Пока что тут только "Итого", в будущем добавишь "База", "От шмота"...)
        text = (
            f"<b>{title}</b>\n\n"
            f"<i>{actor_name}: {description}</i>\n\n"
            f"<b>Расчет:</b>\n"
            f"<code>"
            f"├ (От статов):     (скоро)\n"
            f"├ (От экипировки): (скоро)\n"
            f"├ (От эффектов):   (скоро)\n"
            f"</code>\n"
            f"Итого: <b>{formatted_value}</b>"
        )

        return text
