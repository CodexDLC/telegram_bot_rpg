# app/services/ui_service/character_status_service.py
import logging
from typing import Tuple

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
    Сервис для формирования UI-компонентов меню статуса персонажа.

    Отвечает за создание текста и навигационной клавиатуры для
    основного экрана статуса ("Биография").
    """

    def __init__(self, char_id: int, view_mode: str, call_type: str):
        """
        Инициализирует сервис.

        Args:
            char_id (int): ID персонажа.
            view_mode (str): Режим просмотра ("lobby", "ingame"). Влияет на
                             наличие определенных кнопок (например, "Закрыть").
            call_type (str): Тип текущего действия ("bio", "skills"). Влияет
                             на то, какая кнопка будет скрыта в навигации.
        """
        self.char_id = char_id
        self.view_mode = view_mode
        self.call_type = call_type
        self.actor_name = DEFAULT_ACTOR_NAME
        self.b_status = STATUS_ACTION
        log.debug(f"Инициализирован {self.__class__.__name__} для char_id={char_id}, view_mode='{view_mode}', call_type='{call_type}'.")

    def staus_bio_message(
            self,
            character: CharacterReadDTO,
            stats: CharacterStatsReadDTO,
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Формирует текст и клавиатуру для вкладки "Биография".

        Args:
            character (CharacterReadDTO): DTO с информацией о персонаже.
            stats (CharacterStatsReadDTO): DTO с характеристиками персонажа.

        Returns:
            Tuple[str, InlineKeyboardMarkup]: Готовый текст и клавиатура.
        """
        log.debug(f"Формирование сообщения 'Биография' для char_id={self.char_id}.")
        # Имя "рассказчика" зависит от контекста.
        syb_name = DEFAULT_ACTOR_NAME if self.view_mode == "lobby" else self.actor_name

        text = StatusFormatter.format_character_bio(
            character=character,
            stats=stats,
            actor_name=syb_name
        )
        kb = self._status_kb()
        log.debug(f"Сообщение 'Биография' для char_id={self.char_id} успешно сформировано.")
        return text, kb

    def _status_kb(self) -> InlineKeyboardMarkup:
        """
        Создает навигационную клавиатуру для меню статуса.

        Содержит кнопки для переключения между вкладками ("Биография", "Навыки")
        и, в зависимости от контекста, кнопку "Закрыть".

        Returns:
            InlineKeyboardMarkup: Готовая навигационная клавиатура.
        """
        kb = InlineKeyboardBuilder()
        log.debug("Создание навигационной клавиатуры для меню статуса.")

        active_callback_action = self.call_type
        buttons_to_add = []

        for key, value in self.b_status.items():
            # Пропускаем создание кнопки для уже активной вкладки.
            if key == active_callback_action:
                continue

            # Кнопка "Закрыть" не нужна в режиме лобби.
            if key == "nav:start" and self.view_mode == "lobby":
                continue

            # Собираем callback через фабрику.
            callback_data = StatusMenuCallback(
                action=key,
                char_id=self.char_id,
                view_mode=self.view_mode
            ).pack()
            buttons_to_add.append(InlineKeyboardButton(text=value, callback_data=callback_data))

        if buttons_to_add:
            kb.row(*buttons_to_add)
            log.debug(f"Добавлено {len(buttons_to_add)} навигационных кнопок.")

        return kb.as_markup()
