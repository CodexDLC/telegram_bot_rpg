# app/services/ui_service/helpers_ui/inventory_formatters.py
from loguru import logger as log

from apps.common.schemas_dto import EquippedSlot, InventoryItemDTO


class InventoryFormatter:
    """
    Класс-контейнер для статических методов форматирования текста
    системы инвентаря.
    """

    # --- ВАЖНО: Разделение по категориям для UI ---
    SECTION_NAMES = {
        "equip": "⚔️ Экипировка",
        "resource": "🎒 Ресурсы",
        "consumable": "🧪 Расходники",
        "component": "⚙️ Компоненты",
        "scenario_orchestrator": "📜 Квестовые",
    }

    # Маппинг для подкатегорий (level="sub")
    SUB_CATEGORIES = {
        "equip": {
            "weapon": "🔪 Оружие",
            "armor": "🛡️ Броня",
            "garment": "🧥 Одежда",
            "accessory": "💍 Аксессуары",
        },
        "resource": {
            "ores": "🪨 Руды",
            "leathers": "🐾 Кожа",
            "fabrics": "🧵 Ткани",
            "organics": "🌿 Органика",
        },
    }

    SLOT_NAMES = {
        # Броня (Armor)
        "head_armor": "🤕 Броня (Голова)",
        "chest_armor": "👕 Броня (Тело)",
        "arms_armor": "💪 Броня (Руки)",
        "legs_armor": "👖 Броня (Ноги)",
        "feet_armor": "👞 Броня (Ступни)",
        # Одежда (Garment)
        "chest_garment": "👚 Одежда (Тело)",
        "legs_garment": "🩳 Одежда (Ноги)",
        "outer_garment": "🧥 Верхняя одежда",
        "gloves_garment": "🧤 Перчатки",
        # Оружие/Щит
        "main_hand": "🗡 Осн. рука",
        "off_hand": "🛡 Вт. рука",
        "two_hand": "⚔️ Двуручн.",
        # Аксессуары
        "amulet": "💎 Амулет",
        "earring": "👂 Серьга",
        "ring_1": "💍 Кольцо 1",
        "ring_2": "💍 Кольцо 2",
        "belt_accessory": "🔗 Пояс",
    }

    @staticmethod
    def _get_rarity_icon(rarity: str) -> str:
        """Возвращает эмодзи в зависимости от редкости предмета."""
        icons = {"common": "⚪️", "uncommon": "🟢", "rare": "🔵", "epic": "🟣", "legendary": "🟠"}
        return icons.get(rarity, "⚪️")

    @staticmethod
    def format_main_menu(equipped: list[InventoryItemDTO], current_slots: int, max_slots: int, dust_amount: int) -> str:
        """
        Форматирует текст для главного экрана 'Кукла', включая все слои.
        """
        all_display_slots = [
            "head_armor",
            "head_garment",
            "outer_garment",
            "chest_armor",
            "chest_garment",
            "arms_armor",
            "gloves_garment",
            "main_hand",
            "off_hand",
            "two_hand",
            "belt_accessory",
            "legs_armor",
            "legs_garment",
            "feet_armor",
            "amulet",
            "ring_1",
            "ring_2",
            "earring",
        ]

        equipped_map = {}
        for item in equipped:
            if item.equipped_slot:
                try:
                    equipped_map[item.equipped_slot] = item
                except ValueError:
                    log.warning(
                        f"Formatter | skip_item reason='Invalid equipped_slot value' slot='{item.equipped_slot}'"
                    )

        text_lines = ["<b>👤 Экипировка:</b>", "<code>"]

        for slot_key_str in InventoryFormatter.SLOT_NAMES:
            if slot_key_str not in all_display_slots:
                continue

            slot_name = InventoryFormatter.SLOT_NAMES.get(slot_key_str, "???")

            try:
                slot_key_enum = EquippedSlot(slot_key_str)
            except ValueError:
                continue

            item_in_slot = equipped_map.get(slot_key_enum)

            item_display = "—пусто—"
            if item_in_slot:
                icon = InventoryFormatter._get_rarity_icon(item_in_slot.rarity.value)
                item_display = f"{icon} {item_in_slot.data.name}"

            text_lines.append(f"[{slot_name:<15}]: {item_display}")

        text_lines.append("</code>")
        text_lines.append(f"\n🎒 <b>Рюкзак:</b> {current_slots} / {max_slots}")
        text_lines.append(f"💎 <b>Пыль Резидуу:</b> {dust_amount}")

        return "\n".join(text_lines)

    @staticmethod
    def format_item_list(
        items: list[InventoryItemDTO], section: str, category: str, page: int, total_pages: int, actor_name: str
    ) -> str:
        """
        Форматирует список предметов в выбранной категории.
        """
        section_title = InventoryFormatter.SECTION_NAMES.get(section, "Предметы")
        category_title = InventoryFormatter.SUB_CATEGORIES.get(section, {}).get(category, category)

        log.debug(f"Форматирование списка предметов: Section={section}, Category={category}")

        text_lines = [f"<b>{section_title} ({category_title})</b>", "\n"]

        if not items:
            text_lines.append(f"<i>{actor_name}: В этой категории пока пусто.</i>")
            return "\n".join(text_lines)

        text_lines.append("<code>")
        for i, item in enumerate(items, start=page * 9 + 1):
            rarity_icon = InventoryFormatter._get_rarity_icon(item.rarity.value)
            item_name = item.data.name
            status = "[E]" if item.location == "equipped" else ""
            text_lines.append(f"{i: >2}. {rarity_icon} {item_name} {status}")

        text_lines.append("</code>")
        text_lines.append(f"\n⚙️ <i>Страница {page + 1}/{total_pages}</i>")

        return "\n".join(text_lines)

    @staticmethod
    def format_item_details(item: InventoryItemDTO, actor_name: str) -> str:
        """
        Форматирует детальную карточку предмета, корректно обрабатывая
        разные типы данных (экипировка vs. ресурсы).
        """
        rarity_icon = InventoryFormatter._get_rarity_icon(item.rarity.value)

        text = (
            f"<b>{rarity_icon} {item.data.name}</b>\n"
            f"<i>{actor_name}: {item.data.description}</i>\n\n"
            f"<b>⚙️ Параметры:</b>\n"
            f"<code>"
            f"├ Тип:      {item.item_type.value}\n"
            f"├ Подтип:   {item.subtype}\n"
            f"├ Редкость: {item.rarity.value.capitalize()}\n"
            f"└ Кол-во:   {item.quantity}\n"
            f"</code>\n"
        )

        if item.data.bonuses:
            text += "<b>✨ Бонусы:</b>\n<code>"
            for k, v in item.data.bonuses.items():
                text += f"├ +{v} к {k}\n"
            text += "</code>"

        return text

    @staticmethod
    def format_sub_menu(section: str, actor_name: str) -> str:
        """
        Форматирует текст для меню подкатегорий.
        """
        title = InventoryFormatter.SECTION_NAMES.get(section, "Категория")
        return f"<b>{title}</b>\n\n<i>{actor_name}: Выберите тип предметов, которые хотите просмотреть.</i>"
