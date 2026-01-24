# app/services/ui_service/inventory/inventory_list_ui.py
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

from apps.common.schemas_dto import InventoryItemDTO
from game_client.bot.resources.keyboards.inventory_callback import InventoryCallback
from game_client.bot.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from game_client.bot.ui_service.base_service import BaseUIService
from game_client.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO
from game_client.bot.ui_service.inventory.formatters.inventory_formatters import InventoryFormatter


class InventoryListUI(BaseUIService):
    """
    Класс-помощник для рендеринга уровня 1: Списки предметов.
    """

    # Размер страницы (сетка 3x3 = 9 предметов)
    PAGE_SIZE = 9

    def __init__(
        self,
        char_id: int,
        user_id: int,
        state_data: dict[str, Any],
    ):
        super().__init__(char_id=char_id, state_data=state_data)
        self.user_id = user_id
        self.InvF = InventoryFormatter
        # Используем дефолтное имя, так как в BaseUIService его больше нет
        self.actor_name = DEFAULT_ACTOR_NAME
        log.debug(f"InventoryListUI | status=initialized char_id={char_id}")

    def render(
        self,
        items_on_page: list[InventoryItemDTO],
        total_pages: int,
        current_page: int,
        section: str,
        category: str,
        filter_type: str = "category",
    ) -> ViewResultDTO:
        """
        Рендерит экран списка предметов с фильтрами и пагинацией.
        """
        # 4. Форматируем текст
        text = self.InvF.format_item_list(
            items=items_on_page,
            section=section,
            category=category,
            page=current_page,
            total_pages=total_pages,
            actor_name=self.actor_name,
        )

        # 5. Клавиатура
        if filter_type == "slot":
            kb = self._kb_slot_filter_list(
                section=section,
                category=category,
                page=current_page,
                total_pages=total_pages,
                items_on_page=items_on_page,
                filter_type=filter_type,
            )
        else:
            kb = self._kb_category_filter_list(
                section=section,
                category=category,
                page=current_page,
                total_pages=total_pages,
                items_on_page=items_on_page,
                filter_type=filter_type,
            )

        return ViewResultDTO(text=text, kb=kb)

    def _kb_category_filter_list(
        self,
        section: str,
        category: str,
        page: int,
        total_pages: int,
        items_on_page: list[InventoryItemDTO],
        filter_type: str,
    ) -> InlineKeyboardMarkup:
        """Клавиатура для режима "Фильтр по Категории" (для ресурсов/расходников). С кнопками фильтров."""
        kb = InlineKeyboardBuilder()

        # 1. Ряд фильтров (Динамический из SUB_CATEGORIES)
        filters = self.InvF.SUB_CATEGORIES.get(section)

        if filters:
            # Добавляем кнопку "Все" (сброс фильтра)
            all_text = (
                f"✅ {self.InvF.SECTION_NAMES.get(section, 'Все')}"
                if category == "all"
                else self.InvF.SECTION_NAMES.get(section, "Все")
            )

            cb_all = InventoryCallback(
                level=1, user_id=self.user_id, section=section, category="all", page=0, filter_type=filter_type
            ).pack()
            kb.button(text=all_text, callback_data=cb_all)

            # Добавляем кнопки из подкатегорий
            for f_cat, f_name in filters.items():
                btn_text = f"✅ {f_name}" if category == f_cat else f_name
                cb = InventoryCallback(
                    level=1, user_id=self.user_id, section=section, category=f_cat, page=0, filter_type=filter_type
                ).pack()
                kb.button(text=btn_text, callback_data=cb)

            kb.adjust(3)

        # 2. Цифровая панель для выбора предмета
        num_row = []
        for i, item in enumerate(items_on_page, start=(page * self.PAGE_SIZE) + 1):
            button_num = i - (page * self.PAGE_SIZE)
            cb = InventoryCallback(
                level=2,
                user_id=self.user_id,
                section=section,
                category=category,
                page=page,
                item_id=item.inventory_id,
                filter_type=filter_type,
            ).pack()
            num_row.append(InlineKeyboardButton(text=str(button_num), callback_data=cb))

        if num_row:
            kb.row(*num_row)

        # 3. Пагинация
        nav_row = self._get_pagination_row(section, category, page, total_pages, filter_type)
        kb.row(*nav_row)

        # 4. Кнопка "Назад" (возврат на Level 0 - Кукла)
        cb_back = InventoryCallback(level=0, user_id=self.user_id).pack()
        kb.row(InlineKeyboardButton(text="↩️ Назад к Кукле", callback_data=cb_back))

        return kb.as_markup()

    def _kb_slot_filter_list(
        self,
        section: str,
        category: str,
        page: int,
        total_pages: int,
        items_on_page: list[InventoryItemDTO],
        filter_type: str,
    ) -> InlineKeyboardMarkup:
        """Клавиатура для режима "Фильтр по Слоту" (с Куклы). Без кнопок категорий."""
        kb = InlineKeyboardBuilder()

        # 1. Цифровая панель для выбора предмета
        num_row = []
        for i, item in enumerate(items_on_page, start=(page * self.PAGE_SIZE) + 1):
            button_num = i - (page * self.PAGE_SIZE)
            cb = InventoryCallback(
                level=2,
                user_id=self.user_id,
                section=section,
                category=category,
                page=page,
                item_id=item.inventory_id,
                filter_type=filter_type,
            ).pack()
            num_row.append(InlineKeyboardButton(text=str(button_num), callback_data=cb))

        if num_row:
            kb.row(*num_row)

        # 2. Пагинация
        nav_row = self._get_pagination_row(section, category, page, total_pages, filter_type)
        kb.row(*nav_row)

        # 3. Кнопка "Назад" (возврат на Level 0 - Кукла)
        cb_back = InventoryCallback(level=0, user_id=self.user_id).pack()
        kb.row(InlineKeyboardButton(text="↩️ Назад к Кукле", callback_data=cb_back))

        return kb.as_markup()

    def _get_pagination_row(
        self, section: str, category: str, page: int, total_pages: int, filter_type: str
    ) -> list[InlineKeyboardButton]:
        """Вспомогательный метод для создания ряда пагинации."""
        nav_row = []

        # Назад
        if page > 0:
            cb_prev = InventoryCallback(
                level=1,
                user_id=self.user_id,
                section=section,
                category=category,
                page=page - 1,
                filter_type=filter_type,
            ).pack()
            nav_row.append(InlineKeyboardButton(text="◀️", callback_data=cb_prev))
        else:
            nav_row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

        # Счетчик
        nav_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="ignore"))

        # Вперед
        if page < total_pages - 1:
            cb_next = InventoryCallback(
                level=1,
                user_id=self.user_id,
                section=section,
                category=category,
                page=page + 1,
                filter_type=filter_type,
            ).pack()
            nav_row.append(InlineKeyboardButton(text="▶️", callback_data=cb_next))
        else:
            nav_row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

        return nav_row
