#app/services/ui_service/character_status_service.py

import logging

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from aiogram.utils.keyboard import InlineKeyboardBuilder


from app.resources.schemas_dto.character_dto import CharacterReadDTO, CharacterStatsReadDTO
from app.resources.texts.ui_text.data_text_status_menu import STATUS_ACTION
# Импорты DTO
from app.services.data_loader_service import load_data_auto
from app.services.helpers_module.DTO_helper import fsm_store
from app.services.ui_service.helpers_ui.status_formatters import StatusFormatter

log = logging.getLogger(__name__)

class CharacterMenuUIService:
    """
    Класс сервис с методами для меню статуса персонажа.
    Скрывает логику от ханделера каллбека.
    """

    def __init__(self, user_id: int, char_id: int, fsm: str, call_type: str):
        self.user_id = user_id
        self.char_id = char_id
        self.fsm_state = fsm
        self.call_type = call_type
        self.b_status = STATUS_ACTION

    async def get_bd_data_staus(self)-> dict[str, int | dict | list[dict]] | None:

        log.info(f"Данные для char_id={self.char_id} отсутствуют или неактуальны в FSM, загружаю из БД.")

        get_data = await load_data_auto(
                ["character", "character_stats", "character_progress"],
                character_id=self.char_id,
                user_id=self.user_id
            )

        if get_data:
            # Формируем и сохраняем пакет данных по персонажу.
            bd_data_by_save = {
                    "id": self.char_id,
                    "character": await fsm_store(value=get_data.get("character")),
                    "character_stats": await fsm_store(value=get_data.get("character_stats")),
                    "character_progress_skill": await fsm_store(value=get_data.get("character_progress"))
                }

            return bd_data_by_save
        else:
            return None


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



