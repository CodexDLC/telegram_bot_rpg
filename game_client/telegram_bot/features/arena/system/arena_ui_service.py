from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from common.schemas.arena import ArenaUIPayloadDTO, ButtonDTO
from game_client.telegram_bot.features.arena.resources.formatters.arena_formatter import ArenaFormatter
from game_client.telegram_bot.features.arena.resources.keyboards.arena_callback import ArenaCallback
from game_client.telegram_bot.services.sender.view_sender import ViewResultDTO


class ArenaUIService:
    def __init__(self):
        self.formatter = ArenaFormatter()

    def render_screen(self, payload: ArenaUIPayloadDTO) -> ViewResultDTO:
        """
        Преобразует DTO от бэкенда в ViewResultDTO (текст + клавиатура).
        """
        # 1. Форматируем текст
        text = self.formatter.format_text(payload)

        # 2. Строим клавиатуру
        keyboard = self._build_keyboard(payload.buttons)

        return ViewResultDTO(text=text, kb=keyboard)

    @staticmethod
    def _build_keyboard(buttons: list[ButtonDTO]) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        for btn in buttons:
            callback = ArenaCallback(action=btn.action, mode=btn.mode, value=btn.value)
            builder.button(text=btn.text, callback_data=callback)

        builder.adjust(1)  # По одной кнопке в ряд
        return builder.as_markup()
