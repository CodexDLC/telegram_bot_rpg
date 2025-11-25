from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.game_data.status_menu.modifer_group_data import MODIFIER_HIERARCHY
from app.resources.keyboards.status_callback import StatusModifierCallback, StatusNavCallback
from app.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from app.services.game_service.stats_aggregation_service import StatsAggregationService
from app.services.ui_service.base_service import BaseUIService
from app.services.ui_service.helpers_ui.status_modiier_formatters import ModifierFormatters as ModifierF


class CharacterModifierUIService(BaseUIService):
    def __init__(
        self,
        char_id: int,
        key: str,
        state_data: dict[str, Any],
        syb_name: str | None = None,
    ):
        super().__init__(char_id=char_id, state_data=state_data)
        self.actor_name = syb_name or DEFAULT_ACTOR_NAME
        self.data_skills = MODIFIER_HIERARCHY
        self.data_group: dict[str, Any] | None = self.data_skills.get(key)
        self.key = key

    def status_group_modifier_message(
        self,
        dto_to_use: Any,  # Теперь это может быть Wrapper
    ) -> tuple[str | None, InlineKeyboardMarkup] | tuple[str, None]:
        log.debug(f"Формирование сообщения для группы модификаторов '{self.key}' для персонажа ID={self.char_id}.")

        if not self.data_group:
            return "Группа модификаторов не найдена", None

        text = ModifierF.format_stats_list(data=self.data_group, dto_to_use=dto_to_use, actor_name=self.actor_name)
        kb = self._group_modifier_kb()
        return text, kb

    def _group_modifier_kb(self) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        if self.data_group:
            data_items = self.data_group.get("items")
            if isinstance(data_items, dict):
                for key, title in data_items.items():
                    callback_data = StatusModifierCallback(char_id=self.char_id, level="detail", key=key).pack()
                    kb.button(text=title, callback_data=callback_data)
        kb.adjust(2)

        back_callback = StatusNavCallback(char_id=self.char_id, key="stats").pack()
        kb.row(InlineKeyboardButton(text="[ ◀️ Назад к модификаторам ]", callback_data=back_callback))
        return kb.as_markup()

    def status_detail_modifier_message(
        self,
        dto_to_use: Any,
        group_key: str | None,
    ) -> tuple[str | None, InlineKeyboardMarkup] | tuple[str, None]:
        if not group_key:
            log.warning(f"Отсутствует group_key {group_key}")
            return "Ошибка: отсутствует ключ группы.", None

        value = getattr(dto_to_use, self.key, "N/A")

        if not self.data_group:
            return "Данные о группе не найдены", None

        text = ModifierF.format_modifier_detail(
            data=self.data_group,
            value=value,
            key=self.key,
            actor_name=self.actor_name,
        )
        kb = self._detail_modifier_kb(group_key=group_key)
        return text, kb

    def _detail_modifier_kb(self, group_key: str) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        back_callback = StatusModifierCallback(
            char_id=self.char_id,
            level="group",
            key=group_key,
        ).pack()
        kb.row(InlineKeyboardButton(text="[ ◀️ Назад к группе ]", callback_data=back_callback))
        return kb.as_markup()

    async def get_aggregated_data(self, session: AsyncSession) -> Any | None:
        """
        Получает полные данные (Статы + Модификаторы) через Агрегатор.
        Возвращает объект-обертку, совместимый с getattr().
        """
        try:
            agg_service = StatsAggregationService(session)
            total_data = await agg_service.get_character_total_stats(self.char_id)

            class AggregatedDataWrapper:
                def __init__(self, stats_dict, mods_dict):
                    self._data = {}
                    # Распаковка {key: {total: X}} -> {key: X}
                    for k, v in stats_dict.items():
                        self._data[k] = v["total"]
                    for k, v in mods_dict.items():
                        self._data[k] = v["total"]

                def __getattr__(self, item):
                    return self._data.get(item, 0)

            if not total_data:
                return None

            return AggregatedDataWrapper(total_data.get("stats", {}), total_data.get("modifiers", {}))

        except (TypeError, KeyError) as e:
            log.error(f"Ошибка агрегации данных в UI: {e}")
            return None
