from src.shared.enums.item_enums import EquippedSlot
from src.shared.schemas.inventory import BagContextDTO, DetailsContextDTO, DollContextDTO
from src.shared.schemas.item import ItemRarity


class InventoryFormatter:
    """
    Отвечает за генерацию HTML-текста для сообщений инвентаря.
    Использует данные из DTO.
    """

    SLOT_NAMES = {
        EquippedSlot.HEAD_ARMOR: "Голова",
        EquippedSlot.CHEST_ARMOR: "Тело",
        EquippedSlot.ARMS_ARMOR: "Руки",
        EquippedSlot.LEGS_ARMOR: "Ноги",
        EquippedSlot.FEET_ARMOR: "Ступни",
        EquippedSlot.CHEST_GARMENT: "Одежда",
        EquippedSlot.LEGS_GARMENT: "Штаны",
        EquippedSlot.OUTER_GARMENT: "Плащ",
        EquippedSlot.GLOVES_GARMENT: "Перчатки",
        EquippedSlot.MAIN_HAND: "Осн. рука",
        EquippedSlot.OFF_HAND: "Вт. рука",
        EquippedSlot.TWO_HAND: "Двуручн.",
        EquippedSlot.AMULET: "Амулет",
        EquippedSlot.EARRING: "Серьга",
        EquippedSlot.RING_1: "Кольцо 1",
        EquippedSlot.RING_2: "Кольцо 2",
        EquippedSlot.BELT_ACCESSORY: "Пояс",
    }

    @staticmethod
    def _get_rarity_icon(rarity: ItemRarity) -> str:
        icons = {
            ItemRarity.COMMON: "⚪️",
            ItemRarity.UNCOMMON: "🟢",
            ItemRarity.RARE: "🔵",
            ItemRarity.EPIC: "🟣",
            ItemRarity.LEGENDARY: "🟠",
            ItemRarity.MYTHIC: "🔴",
            ItemRarity.EXOTIC: "✨",
            ItemRarity.ABSOLUTE: "⚫️",
        }
        return icons.get(rarity, "⚪️")

    @staticmethod
    def format_doll(context: DollContextDTO) -> str:
        """
        Форматирует текст для экрана 'Кукла'.
        Список слотов с названиями предметов.
        """
        lines = [
            "<b>👤 Экипировка</b>",
            "",
            "<code>",
        ]

        # Порядок отображения в тексте (логический список)
        display_order = [
            EquippedSlot.HEAD_ARMOR,
            EquippedSlot.AMULET,
            EquippedSlot.EARRING,
            EquippedSlot.OUTER_GARMENT,
            EquippedSlot.CHEST_ARMOR,
            EquippedSlot.CHEST_GARMENT,
            EquippedSlot.ARMS_ARMOR,
            EquippedSlot.GLOVES_GARMENT,
            EquippedSlot.MAIN_HAND,
            EquippedSlot.OFF_HAND,
            EquippedSlot.BELT_ACCESSORY,
            EquippedSlot.LEGS_ARMOR,
            EquippedSlot.LEGS_GARMENT,
            EquippedSlot.FEET_ARMOR,
            EquippedSlot.RING_1,
            EquippedSlot.RING_2,
        ]

        for slot in display_order:
            slot_name = InventoryFormatter.SLOT_NAMES.get(slot, str(slot))
            item = context.equipped_items.get(slot)

            if item:
                icon = InventoryFormatter._get_rarity_icon(item.rarity)
                name = item.data.name
                # Формат: [Слот]: 🟢 Меч
                lines.append(f"[{slot_name:<9}]: {icon} {name}")
            else:
                # Формат: [Слот]: —пусто—
                lines.append(f"[{slot_name:<9}]: —пусто—")

        lines.append("</code>")

        # Кошелек
        lines.append("\n<b>💰 Кошелек:</b>")
        wallet_line = []
        for curr in context.wallet.currency:
            icon = "💎" if curr.id == "dust" else "🪙"
            wallet_line.append(f"{icon} {curr.amount}")

        lines.append("  ".join(wallet_line))

        return "\n".join(lines)

    @staticmethod
    def format_bag(context: BagContextDTO) -> str:
        """
        Форматирует список предметов в сумке.
        """
        section_name = context.active_section.value.capitalize()
        category_name = context.active_category.capitalize() if context.active_category else "Все"

        lines = [f"<b>🎒 {section_name} ({category_name})</b>", "", "<code>"]

        if not context.items:
            lines.append("  (Пусто)")
        else:
            for i, item in enumerate(context.items, start=1):
                icon = InventoryFormatter._get_rarity_icon(item.rarity)
                name = item.data.name
                status = "[E]" if item.location == "equipped" else ""
                if len(name) > 20:
                    name = name[:19] + "…"

                lines.append(f"{i}. {icon} {name} {status}")

        lines.append("</code>")
        lines.append(f"\n⚙️ Страница {context.pagination.page + 1}/{context.pagination.total_pages}")

        return "\n".join(lines)

    @staticmethod
    def format_details(context: DetailsContextDTO) -> str:
        """
        Форматирует карточку предмета.
        """
        item = context.item
        icon = InventoryFormatter._get_rarity_icon(item.rarity)

        lines = [
            f"<b>{icon} {item.data.name}</b>",
            f"<i>{item.data.description}</i>",
            "",
            "<b>⚙️ Параметры:</b>",
            "<code>",
            f"├ Тип:      {item.item_type.value}",
            f"├ Подтип:   {item.subtype}",
            f"├ Редкость: {item.rarity.value.capitalize()}",
            f"└ Кол-во:   {item.quantity}",
            "</code>",
        ]

        if item.data.bonuses:
            lines.append("")
            lines.append("<b>✨ Бонусы:</b>")
            lines.append("<code>")
            for k, v in item.data.bonuses.items():
                lines.append(f"├ {k}: +{v}")
            lines.append("</code>")

        if context.comparison_item:
            comp = context.comparison_item
            lines.append("")
            lines.append(f"<b>🆚 Надето: {comp.data.name}</b>")

        return "\n".join(lines)
