#app/services/ui_service/character_status_service.py

import logging

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.keyboards.callback_data import StatusMenuCallback
from app.resources.schemas_dto.character_dto import CharacterReadDTO, CharacterStatsReadDTO
from app.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
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
        self.actor_name = DEFAULT_ACTOR_NAME
        self.call_type = call_type
        self.b_status = STATUS_ACTION


    def staus_bio_message(
            self,
            character: CharacterReadDTO,
            stats: CharacterStatsReadDTO,

        ):

        syb_name = DEFAULT_ACTOR_NAME if self.call_type == "lobby" else self.actor_name

        text = StatusFormatter.format_character_bio(
                character=character,
                stats=stats,
                actor_name=syb_name
            )

        kb = self._status_kb()

        return text, kb

    def _status_kb(self) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()

        active_callback_action = self.call_type
        buttons = []
        for key, value in self.b_status.items():

            # 'key' здесь это 'status:bio' или 'status:skills'
            # Получаем 'bio' или 'skills'
            action = key

            if action == active_callback_action:
                continue

            # VVV Логика для кнопки "Закрыть" VVV
            if key == "nav:start":
                # Если мы в лобби, кнопка "Закрыть" не нужна
                if self.view_mode == "lobby":  # <--- (Твой фикс для view_mode)
                    continue
                # Это обычная кнопка, она не часть Фабрики
                b1 = InlineKeyboardButton(text=value, callback_data=key)
                buttons.append(b1)
                continue

            # VVV МАГИЯ VVV
            # Собираем callback через нашу Фабрику
            callback_data_str = StatusMenuCallback(
                action=action,
                char_id=self.char_id,
                view_mode=self.view_mode
            ).pack()  # .pack() создает строку, например "sm:bio:123:lobby"

            b1 = InlineKeyboardButton(text=value, callback_data=callback_data_str)
            buttons.append(b1)

        if buttons:
            kb.row(*buttons)

        return kb.as_markup()



