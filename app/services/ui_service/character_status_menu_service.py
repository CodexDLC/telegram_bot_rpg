#app/services/ui_service/character_status_menu_service.py

import logging

from aiogram.types import InlineKeyboardMarkup
from typing import Any, Coroutine

from aiogram.utils.keyboard import InlineKeyboardBuilder


from app.resources.schemas_dto.character_dto import CharacterReadDTO, CharacterStatsReadDTO
# Импорты DTO
from app.services.data_loader_service import load_data_auto
from app.services.helpers_module.DTO_helper import fsm_store
from app.services.ui_service.helpers_ui.status_formatters import StatusFormatter

log = logging.getLogger(__name__)

STATUS_ACTION = {

    "status:bio": "📋 Базовая инфо",
    "status:skill": "📚 Доступные навыки"

}


class CharacterMenuUIService:
    """
    Класс сервис с методами для меню статуса персонажа.
    Скрывает логику от ханделера каллбека.
    """

    def __init__(self, user_id: int, char_id: int, fsm: str):
        self.user_id = user_id
        self.char_id = char_id
        self.fsm_state = fsm
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
                    "character_progress": await fsm_store(value=get_data.get("character_progress"))
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

        for call, name in self.b_status.items():
            # 💡 Исправлено: Добавляем char_id ко ВСЕМ кнопкам для надежности
            # Итоговый формат: status:bio:123
            new_callback_data = f"{call}:{self.char_id}"

            kb.button(text=name, callback_data=new_callback_data)

        if self.fsm_state != "CharacterLobby.selection":
            # 💡 Подумайте о том, чтобы включить ID в "nav:start" для отслеживания
            kb.button(text="❌ Закрыть", callback_data="nav:start")

        return kb.as_markup()



