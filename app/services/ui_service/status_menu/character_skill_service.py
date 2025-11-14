# app/services/ui_service/character_skill_service.py
import logging
from typing import Any, Optional, Dict, Tuple

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.game_data.status_menu.bio_group_data import TABS_NAV_DATA
from app.resources.game_data.status_menu.skill_group_data import SKILL_HIERARCHY
from app.resources.keyboards.status_callback import StatusNavCallback, StatusSkillsCallback
from app.resources.schemas_dto.character_dto import CharacterReadDTO
from app.resources.texts.ui_messages import DEFAULT_ACTOR_NAME

from app.services.ui_service.helpers_ui.skill_formatters import SkillFormatters as SkillF

log = logging.getLogger(__name__)


class CharacterSkillStatusService:
    """
    Сервис для управления UI-логикой меню навыков персонажа.

    Формирует текст и клавиатуры для различных уровней вложенности:
    от общего списка групп до детальной информации о конкретном навыке.
    """

    def __init__(self,
                 char_id: int,
                 callback_data: StatusNavCallback,
                 state_data: Dict[str, Any],
                 syb_name: Optional[str] = None,
                 ):
        """

        """
        self.char_id = char_id
        self.actor_name = syb_name or DEFAULT_ACTOR_NAME
        self.status_buttons = TABS_NAV_DATA
        self.data_lib = SKILL_HIERARCHY
        self.call_type = callback_data.key
        self.state_data = state_data
        log.debug(f"Инициализирован {self.__class__.__name__} для char_id={char_id}.")



    def data_message_group_skill(self, group_type: Optional[str]) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Возвращает текст и клавиатуру для навыков в конкретной группе.

        Args:
            group_type (Optional[str]): Ключ группы навыков (e.g., "combat").

        Returns:
            Tuple[str, InlineKeyboardMarkup]: Текст и клавиатура.
        """
        pass

    def _group_skill_kb(self) -> InlineKeyboardMarkup:
        """Создает клавиатуру для списка навыков в группе."""
        kb = InlineKeyboardBuilder()

        data = self.data_lib.get(self.call_type).get("items")

        for key, value in data.items():
            callback_data = StatusSkillsCallback(
                char_id=self.char_id,
                level="detail",
                key=key
            ).pack()
            kb.button(text=value, callback_data=callback_data)
        kb.adjust(2)

        buttons = self._status_buttons()

        if buttons:
            kb.row(*buttons)
            log.debug(f"Добавлено {len(buttons)} навигационных кнопок.")

        return kb.as_markup()


