# app/services/ui_service/helpers_ui/inventory_formatters.py
from loguru import logger as log

from app.resources.schemas_dto.item_dto import InventoryItemDTO


class InventoryFormatter:
    """
    Класс-контейнер для статических методов форматирования текста
    системы инвентаря.
    """

    # --- ВАЖНО: Разделение по категориям для UI ---
    SECTION_NAMES = {
        "equip": "⚔️ Экипировка",
        "resource": "🎒 Ресурсы (Сырье)",
        "component": "⚙️ Компоненты",
        "quest": "📜 Квестовые предметы",
    }

    # Маппинг для подкатегорий (level="sub")
    SUB_CATEGORIES = {
        "equip": {
            "weapon": "🔪 Оружие",
            "armor": "🛡️ Броня",
            "accessory": "💍 Аксессуары",
        },
        "resource": {
            "ores": "🪨 Руды",
            "leathers": "🐾 Кожа",
            "fabrics": "🧵 Ткани",
            "organics": "🌿 Органика",
        },
    }

    # 🔥 ИСПРАВЛЕНИЕ: Константа перенесена на уровень класса
    SLOT_NAMES = {
        "head": "🤕 Голова",
        "chest": "👕 Тело",
        "main_hand": "🗡 Прав. р.",
        "off_hand": "🛡 Лев. р.",
        "legs": "👖 Ноги",
        "feet": "👞 Обувь",
    }

    @staticmethod
    def _get_rarity_icon(rarity: str) -> str:
        """Возвращает эмодзи в зависимости от редкости предмета."""
        icons = {"common": "⚪️", "uncommon": "🟢", "rare": "🔵", "epic": "🟣", "legendary": "🟠"}
        return icons.get(rarity, "⚪️")

    @staticmethod
    def format_main_menu(equipped: list[InventoryItemDTO], current_slots: int, max_slots: int, dust_amount: int) -> str:
        """
        Форматирует текст для главного экрана 'Кукла'.

        Args:
            equipped (list[InventoryItemDTO]): Список надетых предметов.
            current_slots (int): Текущее количество занятых слотов.
            max_slots (int): Максимальное количество слотов.
            dust_amount (int): Количество основной валюты.

        Returns:
            str: Отформатированное сообщение для Telegram.
        """
        # 🔥 ИСПРАВЛЕНИЕ: Используем константу класса
        equipped_map = {slot: "—пусто—" for slot in InventoryFormatter.SLOT_NAMES}

        for item in equipped:
            # Для надетого предмета используем первый слот как ключевой для отображения
            if item.data.valid_slots:
                slot_key = item.data.valid_slots[0]
                # Проверка на наличие слота в нашем списке (защита от багов)
                if slot_key in equipped_map:
                    icon = InventoryFormatter._get_rarity_icon(item.rarity.value)
                    equipped_map[slot_key] = f"{icon} {item.data.name}"

        text = (
            f"<b>👤 Экипировка:</b>\n"
            f"<code>"
            f"[{InventoryFormatter.SLOT_NAMES['head']:<10}]: {equipped_map['head']}\n"
            f"[{InventoryFormatter.SLOT_NAMES['chest']:<10}]: {equipped_map['chest']}\n"
            f"[{InventoryFormatter.SLOT_NAMES['main_hand']:<10}]: {equipped_map['main_hand']}\n"
            f"[{InventoryFormatter.SLOT_NAMES['off_hand']:<10}]: {equipped_map['off_hand']}\n"
            f"[{InventoryFormatter.SLOT_NAMES['legs']:<10}]: {equipped_map['legs']}\n"
            f"[{InventoryFormatter.SLOT_NAMES['feet']:<10}]: {equipped_map['feet']}\n"
            f"</code>\n"
            f"🎒 <b>Рюкзак:</b> {current_slots} / {max_slots}\n"
            f"💎 <b>Пыль Резидуу:</b> {dust_amount}"
        )
        return text

    @staticmethod
    def format_item_list(
        items: list[InventoryItemDTO], section: str, category: str, page: int, total_pages: int, actor_name: str
    ) -> str:
        """
        Форматирует список предметов в выбранной категории.

        Args:
            items (list[InventoryItemDTO]): Список предметов на текущей странице.
            section (str): Основная секция (equip, resource).
            category (str): Подкатегория (weapon, ores).
            page (int): Номер текущей страницы (начиная с 0).
            total_pages (int): Общее количество страниц.
            actor_name (str): Имя актора (System).

        Returns:
            str: Отформатированный список предметов с пагинацией.
        """
        section_title = InventoryFormatter.SECTION_NAMES.get(section, "Предметы")
        category_title = InventoryFormatter.SUB_CATEGORIES.get(section, {}).get(category, category)

        log.debug(f"Форматирование списка предметов: Section={section}, Category={category}")

        text_lines = [f"<b>{section_title} ({category_title})</b>", "\n"]

        if not items:
            text_lines.append(f"<i>{actor_name}: В этой категории пока пусто.</i>")
            return "\n".join(text_lines)

        text_lines.append("<code>")
        for i, item in enumerate(items, start=page * 9 + 1):  # 9 - размер сетки 3x3
            item_name = item.data.name
            rarity_icon = InventoryFormatter._get_rarity_icon(item.rarity.value)

            # Статус: [E] - надет, [S] - системный, [T] - для торговли
            status = "[E]" if item.location == "equipped" else ""

            # Нумерация для кнопок
            text_lines.append(f"{i: >2}. {rarity_icon} {item_name} {status}")

        text_lines.append("</code>")
        text_lines.append(f"\n⚙️ <i>Страница {page + 1}/{total_pages}</i>")

        return "\n".join(text_lines)

    @staticmethod
    def format_item_details(item: InventoryItemDTO, actor_name: str) -> str:
        """
        Форматирует детальную карточку предмета.

        Args:
            item (InventoryItemDTO): DTO предмета для детализации.
            actor_name (str): Имя актора (System).

        Returns:
            str: Отформатированная карточка предмета.
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
            f"├ Вес:      {item.data.weight}\n"
            f"└ Кол-во:   {item.quantity}\n"
            f"</code>\n"
            f"<b>✨ Бонусы:</b>\n"
            f"<code>"
        )

        if item.data.bonuses:
            for k, v in item.data.bonuses.items():
                text += f"├ +{v} к {k}\n"
        else:
            text += "└ Нет прямых бонусов.\n"

        text += "</code>"
        return text

    @staticmethod
    def format_sub_menu(section: str, actor_name: str) -> str:
        """
        Форматирует текст для меню подкатегорий.

        Args:
            section (str): Основная секция (equip, resource).
            actor_name (str): Имя актора (System).

        Returns:
            str: Отформатированное сообщение.
        """
        title = InventoryFormatter.SECTION_NAMES.get(section, "Категория")
        return f"<b>{title}</b>\n\n<i>{actor_name}: Выберите тип предметов, которые хотите просмотреть.</i>"
