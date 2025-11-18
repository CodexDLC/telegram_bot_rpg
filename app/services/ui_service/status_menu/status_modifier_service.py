# app/services/ui_service/status_menu/status_modifier_service.py
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError

from app.resources.game_data.status_menu.modifer_group_data import MODIFIER_HIERARCHY
from app.resources.keyboards.status_callback import StatusModifierCallback, StatusNavCallback
from app.resources.schemas_dto.character_dto import CharacterStatsReadDTO
from app.resources.schemas_dto.modifer_dto import CharacterModifiersDTO
from app.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from app.services.ui_service.base_service import BaseUIService
from app.services.ui_service.helpers_ui.status_modiier_formatters import ModifierFormatters as ModifierF
from database.repositories import get_character_stats_repo, get_modifiers_repo
from database.session import get_async_session


class CharacterModifierUIService(BaseUIService):
    def __init__(
        self,
        char_id: int,
        key: str,
        state_data: dict[str, Any],
        syb_name: str | None = None,
    ):
        """
        Инициализирует сервис для работы с навыками персонажа.

        :param char_id: ID персонажа.
        :param key: Ключ для доступа к данным о группе модификаторов или данные модификатора.
        :param state_data: Данные состояния FSM.
        :param syb_name: Имя симбионта (опционально).
        """
        super().__init__(char_id=char_id, state_data=state_data)
        self.actor_name = syb_name or DEFAULT_ACTOR_NAME
        self.data_skills = MODIFIER_HIERARCHY
        self.data_group: dict[str, Any] | None = self.data_skills.get(key)
        self.key = key

    def status_group_modifier_message(
        self, dto_to_use: CharacterStatsReadDTO | CharacterModifiersDTO
    ) -> tuple[str | None, InlineKeyboardMarkup] | tuple[str, None]:
        """
        Формирует сообщение со списком модификаторов в выбранной группе.

        :return: Кортеж с текстом сообщения и клавиатурой.
        """
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
        self, dto_to_use: CharacterStatsReadDTO | CharacterModifiersDTO, group_key: str | None
    ) -> tuple[str | None, InlineKeyboardMarkup] | tuple[str, None]:
        """
        Формирует сообщение с детальной информацией (карточкой) о модификаторе.

        :param dto_to_use: DTO, из которого нужно извлечь значение.
        :param group_key: Ключ родительской группы (нужен для кнопки "Назад").
        :return: Кортеж с текстом сообщения и клавиатурой.
        """
        if not group_key:
            log.warning(f"Отсутствует group_key {group_key}")
            return "Ошибка: отсутствует ключ группы.", None

        log.debug(f"Формирование Lvl 2 (детали) для ключа '{self.key}' (группа '{group_key}')")

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
        """
        Создает клавиатуру для детального просмотра (Lvl 2) - только "Назад".

        :param group_key: Ключ группы (Lvl 1), к которой нужно вернуться.
        :return: Объект клавиатуры.
        """
        kb = InlineKeyboardBuilder()

        back_callback = StatusModifierCallback(
            char_id=self.char_id,
            level="group",
            key=group_key,
        ).pack()

        kb.row(InlineKeyboardButton(text="[ ◀️ Назад к группе ]", callback_data=back_callback))
        return kb.as_markup()

    async def get_data_modifier(self) -> CharacterModifiersDTO | None:
        try:
            async with get_async_session() as session:
                modifier_repo = get_modifiers_repo(session)
                modifiers = await modifier_repo.get_modifiers(self.char_id)
                if modifiers:
                    log.debug(f"Персонаж с char_id={self.char_id} успешно получен.")
                    return modifiers
                else:
                    return None
        except SQLAlchemyError as e:
            log.error(f"{e}")
            return None

    async def get_data_stats(self) -> CharacterStatsReadDTO | None:
        try:
            async with get_async_session() as session:
                character_stats = get_character_stats_repo(session)
                stats = await character_stats.get_stats(self.char_id)
                if stats:
                    log.debug(f"Персонаж с char_id={self.char_id} успешно получен.")
                    return stats
                else:
                    return None
        except SQLAlchemyError as e:
            log.error(f"{e}")
            return None
