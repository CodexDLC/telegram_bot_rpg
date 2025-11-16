# app/services/ui_service/status_menu/status_modifier_service.py
import logging
from typing import Tuple, Optional, Dict, Any, Type

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


from app.resources.game_data.status_menu.modifer_group_data import MODIFIER_HIERARCHY
from app.resources.keyboards.status_callback import StatusNavCallback, StatusModifierCallback
from app.resources.schemas_dto.character_dto import CharacterStatsReadDTO
from app.resources.schemas_dto.modifer_dto import CharacterModifiersDTO
from app.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from app.services.ui_service.base_service import BaseUIService
from app.services.ui_service.helpers_ui.status_modiier_formatters import ModifierFormatters as ModifierF
from database.repositories import get_modifiers_repo, get_character_stats_repo
from database.session import get_async_session

log = logging.getLogger(__name__)



class CharacterModifierUIService(BaseUIService):

    def __init__(self,
                 char_id: int,
                 key: str,
                 state_data: Dict[str, Any],
                 syb_name: Optional[str] = None,
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
        self.data_group = self.data_skills.get(key)
        self.key = key



    def status_group_modifier_message(
            self,
            dto_to_use: CharacterStatsReadDTO | CharacterModifiersDTO
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Формирует сообщение со списком модификаторов в выбранной группе.

        :return: Кортеж с текстом сообщения и клавиатурой.
        """
        log.debug(f"Формирование сообщения для группы модификаторов '{self.key}' для персонажа ID={self.char_id}.")

        text = ModifierF.format_stats_list(
            data=self.data_group,
            dto_to_use=dto_to_use,
            actor_name=self.actor_name
        )

        kb = self._group_modifier_kb()



        return text, kb

    def _group_modifier_kb(self)-> InlineKeyboardMarkup:

        kb = InlineKeyboardBuilder()
        data_items = self.data_group.get("items")

        for key, title in data_items.items():
            callback_data = StatusModifierCallback(
                    char_id=self.char_id,
                    level="detail",
                    key=key
                ).pack()
            kb.button(text=title, callback_data=callback_data)
        kb.adjust(2)

        # Кнопка "Назад" для возврата к списку групп модификаторов
        back_callback = StatusNavCallback(
            char_id=self.char_id,
            key="stats"
        ).pack()

        kb.row(
            InlineKeyboardButton(text="[ ◀️ Назад к модификаторам ]", callback_data=back_callback)
        )
        return kb.as_markup()

    async def get_data_modifier(self)-> CharacterModifiersDTO | None:

        try:
            async with get_async_session() as session:
                modifier_repo = get_modifiers_repo(session)
                modifiers = await modifier_repo.get_modifiers(self.char_id)
                if modifiers:
                    log.debug(f"Персонаж с char_id={self.char_id} успешно получен.")
                    return modifiers
                else:
                    return None
        except Exception as e:
            log.error(f"{e}")


    async def get_data_stats(self)-> CharacterStatsReadDTO | None:

        try:
            async with get_async_session() as session:
                character_stats = get_character_stats_repo(session)
                stats = await character_stats.get_stats(self.char_id)
                if stats:
                    log.debug(f"Персонаж с char_id={self.char_id} успешно получен.")
                    return stats
                else:
                    return None
        except Exception as e:
            log.error(f"{e}")