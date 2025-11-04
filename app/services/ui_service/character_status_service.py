#app/services/ui_service/character_status_service.py

import logging

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from aiogram.utils.keyboard import InlineKeyboardBuilder


from app.resources.schemas_dto.character_dto import CharacterReadDTO, CharacterStatsReadDTO
from app.resources.texts.ui_text.data_text_status_menu import STATUS_ACTION

from app.services.ui_service.helpers_ui.status_formatters import StatusFormatter

log = logging.getLogger(__name__)

class CharacterMenuUIService:
    """
    Класс сервис с методами для меню статуса персонажа.
    Скрывает логику от ханделера каллбека.
    """

    def __init__(self, char_id: int, view_mode: str, call_type: str):
        self.char_id = char_id
        self.view_mode = view_mode
        self.actor_name = "system"
        self.call_type = call_type
        self.b_status = STATUS_ACTION


    def staus_bio_message(
            self,
            character: CharacterReadDTO,
            stats: CharacterStatsReadDTO,

        ):

        text = StatusFormatter.format_character_bio(
            character=character,
            stats=stats
        )


        kb = self._status_kb()

        return text, kb

    def _status_kb(self) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()

        active_callback = f"status:{self.call_type}"
        buttons = []
        for key, value in self.b_status.items():

            if key == active_callback:
                continue

            if key == "nav:start":
                # Если мы в лобби, кнопка "Закрыть" не нужна
                if self.fsm_state == "CharacterLobby.selection":
                    continue
            callback_data = f"{key}:{self.char_id}" if key.startswith("status:") else key

            b1 = InlineKeyboardButton(text=value, callback_data=callback_data)
            buttons.append(b1)

        if buttons:
            kb.row(*buttons)

        return kb.as_markup()



