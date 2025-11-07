# app/services/ui_service/character_status_service.py
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
    Сервис для формирования меню статуса персонажа.

    Этот класс отвечает за создание текста и навигационной клавиатуры для
    основного экрана статуса персонажа (вкладка "Биография").
    """

    def __init__(self, char_id: int, view_mode: str, call_type: str):
        """
        Инициализирует сервис меню статуса.

        Args:
            char_id (int): ID персонажа.
            view_mode (str): Режим просмотра (e.g., "lobby", "ingame").
                Влияет на наличие определенных кнопок, например "Закрыть".
            call_type (str): Тип текущего действия (e.g., "bio", "skills").
                Влияет на то, какая кнопка будет скрыта в навигации.
        """
        self.char_id = char_id
        self.view_mode = view_mode
        self.actor_name = DEFAULT_ACTOR_NAME
        self.call_type = call_type
        self.b_status = STATUS_ACTION

    def staus_bio_message(
            self,
            character: CharacterReadDTO,
            stats: CharacterStatsReadDTO,
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Формирует текст и клавиатуру для вкладки "Биография".

        Args:
            character (CharacterReadDTO): DTO с основной информацией о персонаже.
            stats (CharacterStatsReadDTO): DTO с характеристиками персонажа.

        Returns:
            tuple[str, InlineKeyboardMarkup]: Готовый текст и клавиатура.
        """
        # Имя "рассказчика" зависит от контекста (лобби или игра).
        syb_name = DEFAULT_ACTOR_NAME if self.view_mode == "lobby" else self.actor_name

        text = StatusFormatter.format_character_bio(
            character=character,
            stats=stats,
            actor_name=syb_name
        )
        kb = self._status_kb()
        return text, kb

    def _status_kb(self) -> InlineKeyboardMarkup:
        """
        Создает навигационную клавиатуру для меню статуса.

        Клавиатура содержит кнопки для переключения между вкладками
        ("Биография", "Навыки") и, в зависимости от контекста, кнопку "Закрыть".

        Returns:
            InlineKeyboardMarkup: Готовая навигационная клавиатура.
        """
        kb = InlineKeyboardBuilder()

        active_callback_action = self.call_type
        buttons = []
        for key, value in self.b_status.items():
            action = key

            # Пропускаем создание кнопки для уже активной вкладки.
            if action == active_callback_action:
                continue

            # Особая логика для кнопки "Закрыть".
            if key == "nav:start":
                # Кнопка "Закрыть" не нужна в режиме лобби.
                if self.view_mode == "lobby":
                    continue
                # Это простая кнопка, не использующая фабрику callback'ов.
                buttons.append(InlineKeyboardButton(text=value, callback_data=key))
                continue

            # Для остальных кнопок ("Биография", "Навыки") используем
            # фабрику, чтобы создать стандартизированный callback.
            callback_data_str = StatusMenuCallback(
                action=action,
                char_id=self.char_id,
                view_mode=self.view_mode
            ).pack()  # .pack() сериализует данные в строку.

            buttons.append(InlineKeyboardButton(text=value, callback_data=callback_data_str))

        if buttons:
            kb.row(*buttons)

        return kb.as_markup()
