from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.common.schemas_dto.status_dto import FullCharacterDataDTO
from game_client.bot.resources.keyboards.status_callback import StatusModifierCallback, StatusNavCallback
from game_client.bot.resources.status_menu.bio_group_data import TABS_NAV_DATA
from game_client.bot.resources.status_menu.modifer_group_data import MODIFIER_HIERARCHY
from game_client.bot.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from game_client.bot.ui_service.base_service import BaseUIService
from game_client.bot.ui_service.status_menu.formatters.status_modiier_formatters import ModifierFormatters as ModifierF


class CharacterModifierUIService(BaseUIService):
    def __init__(
        self,
        callback_data: StatusNavCallback | StatusModifierCallback,
        state_data: dict[str, Any],
        syb_name: str | None = None,
    ):
        super().__init__(char_id=callback_data.char_id, state_data=state_data)
        # Используем переданное имя или дефолтное
        self.actor_name = syb_name or DEFAULT_ACTOR_NAME
        self.data_skills = MODIFIER_HIERARCHY
        self.key = callback_data.key

        if isinstance(callback_data, StatusModifierCallback):
            self.level = callback_data.level
        else:
            self.level = "root"

        if self.level == "group":
            self.data_group = self.data_skills.get(self.key)
        elif self.level == "detail":
            # Для деталей нам нужно найти группу.
            # Пока заглушка.
            self.data_group = None
        else:
            self.data_group = None

    async def render_modifier_menu(self, data: FullCharacterDataDTO) -> tuple[str, InlineKeyboardMarkup]:
        """
        Рендерит меню модификаторов.
        """

        # Создаем обертку для доступа к статам через getattr
        class AggregatedDataWrapper:
            def __init__(self, total_stats):
                self._data = {}
                # total_stats: {key: {base: X, bonus: Y, total: Z}}
                # Нам нужно {key: total}
                if total_stats:
                    # Разделяем stats и modifiers, если они смешаны, или просто берем total
                    # В FullCharacterDataDTO total_stats это dict[str, dict]
                    for k, v in total_stats.items():
                        if isinstance(v, dict) and "total" in v:
                            self._data[k] = v["total"]
                        else:
                            self._data[k] = v  # Fallback

            def __getattr__(self, item):
                return self._data.get(item, 0)

        wrapper = AggregatedDataWrapper(data.total_stats)

        if self.level == "root" or self.key == "modifiers":  # "stats" в старом коде, "modifiers" в новом
            return self._render_root_menu(wrapper)
        elif self.level == "group":
            return self.status_group_modifier_message(wrapper)
        elif self.level == "detail":
            return "Детали модификатора (WIP)", InlineKeyboardBuilder().as_markup()

        return "Неизвестный контекст", InlineKeyboardBuilder().as_markup()

    def _render_root_menu(self, wrapper: Any) -> tuple[str, InlineKeyboardMarkup]:
        """Рендерит список групп модификаторов."""
        data_stats = self.data_skills.get("stats", {})
        items = data_stats.get("items", {}) if isinstance(data_stats, dict) else {}

        char_name = "Персонаж"  # Нужно передать имя персонажа, но его нет в wrapper.
        # Можно добавить char_name в wrapper или передать отдельно.
        # Пока заглушка.

        text = ModifierF.group_modifier(items, char_name, self.actor_name)

        kb = InlineKeyboardBuilder()
        for key, value in items.items():
            callback_data = StatusModifierCallback(char_id=self.char_id, level="group", key=key).pack()
            kb.button(text=value, callback_data=callback_data)
        kb.adjust(2)

        # Добавляем табы навигации (Колесо)
        nav_buttons = []
        for key, value in TABS_NAV_DATA.items():
            if key == "modifiers":  # Пропускаем текущую вкладку
                continue

            callback_data = StatusNavCallback(
                char_id=self.char_id,
                key=key,
            ).pack()
            nav_buttons.append(InlineKeyboardButton(text=value, callback_data=callback_data))

        if nav_buttons:
            kb.row(*nav_buttons)

        return text or "Ошибка форматирования", kb.as_markup()

    def status_group_modifier_message(
        self,
        dto_to_use: Any,
    ) -> tuple[str, InlineKeyboardMarkup]:
        if not self.data_group:
            return "Группа модификаторов не найдена", InlineKeyboardBuilder().as_markup()

        text = ModifierF.format_stats_list(data=self.data_group, dto_to_use=dto_to_use, actor_name=self.actor_name)
        kb = self._group_modifier_kb()
        return text or "Ошибка форматирования", kb

    def _group_modifier_kb(self) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        if self.data_group:
            data_items = self.data_group.get("items")
            if isinstance(data_items, dict):
                for key, title in data_items.items():
                    callback_data = StatusModifierCallback(char_id=self.char_id, level="detail", key=key).pack()
                    kb.button(text=title, callback_data=callback_data)
        kb.adjust(2)

        back_callback = StatusNavCallback(char_id=self.char_id, key="modifiers").pack()
        kb.row(InlineKeyboardButton(text="[ ◀️ Назад к модификаторам ]", callback_data=back_callback))
        return kb.as_markup()
