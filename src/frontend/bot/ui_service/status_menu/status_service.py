# from typing import Any
#
# from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
# from aiogram.utils.keyboard import InlineKeyboardBuilder
# from apps.common.schemas_dto.status_dto import FullCharacterDataDTO
# from loguru import logger as log
#
# from src.frontend.bot import BaseUIService
# from src.frontend.bot.resources.keyboards.status_callback import StatusNavCallback
# from src.frontend.bot.resources.status_menu.bio_group_data import BIO_HIERARCHY, TABS_NAV_DATA
# from src.frontend.bot.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
# from src.frontend.bot.ui_service.status_menu.formatters.status_formatters import StatusFormatter as StatusF
#
#
# class CharacterMenuUIService(BaseUIService):
#     """
#     Сервис для формирования UI-компонентов меню статуса персонажа.
#     """
#
#     def __init__(
#         self,
#         callback_data: StatusNavCallback,
#         state_data: dict[str, Any],
#         syb_name: str | None = None,
#     ):
#         super().__init__(state_data=state_data, char_id=callback_data.char_id)
#
#         # Используем переданное имя или дефолтное
#         self.actor_name = syb_name or DEFAULT_ACTOR_NAME
#         self.status_buttons = TABS_NAV_DATA
#         self.data_bio: dict[str, Any] = BIO_HIERARCHY.get("bio", {})
#         self.call_type = callback_data.key
#
#         log.debug(
#             f"Initialized {self.__class__.__name__} for char_id={self.char_id}, "
#             f"call_type='{self.call_type}', actor='{self.actor_name}'"
#         )
#
#     async def render_bio_menu(
#         self,
#         data: FullCharacterDataDTO,
#     ) -> tuple[str, InlineKeyboardMarkup]:
#         """
#         Формирует текст и клавиатуру для вкладки "Биография".
#         """
#         # TODO: Заменить прямые вызовы репозиториев на вызовы StatusClient.
#         log.debug(f"Формирование сообщения 'Биография' для char_id={self.char_id}.")
#
#         character = data.character
#
#         description = self.data_bio.get("description", "Нет данных.")
#         text_formated = (
#             description.format(
#                 name=character.name,
#                 gender=character.gender,
#                 created_at=character.created_at.strftime("%d-%m-%Y %H:%M"),
#             )
#             if isinstance(description, str)
#             else "Нет данных."
#         )
#
#         text = StatusF.format_character_bio(text_formated=text_formated, actor_name=self.actor_name)
#
#         kb = self._status_kb()
#         return text, kb
#
#     def _status_kb(self) -> InlineKeyboardMarkup:
#         """
#         Создает БАЗОВУЮ навигационную клавиатуру (только нижний ряд).
#         """
#         kb = InlineKeyboardBuilder()
#         buttons_to_add = self._status_buttons()
#         if buttons_to_add:
#             kb.row(*buttons_to_add)
#         return kb.as_markup()
#
#     def _status_buttons(self) -> list[InlineKeyboardButton]:
#         buttons_to_add = []
#         for key, value in self.status_buttons.items():
#             if key == self.call_type:
#                 continue
#
#             callback_data = StatusNavCallback(
#                 char_id=self.char_id,
#                 key=key,
#             ).pack()
#             buttons_to_add.append(InlineKeyboardButton(text=value, callback_data=callback_data))
#
#         return buttons_to_add
