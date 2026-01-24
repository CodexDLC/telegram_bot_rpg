from aiogram.utils.keyboard import InlineKeyboardBuilder

from game_client.bot.resources.texts.buttons_callback import Buttons
from game_client.bot.resources.texts.ui_messages import START_GREETING
from game_client.telegram_bot.common.dto.view_dto import ViewResultDTO
from game_client.telegram_bot.common.services.error.ui.keyboards import StartMenuCallback


class StartUI:
    """
    Service for rendering Command/Menu UI.
    Pure transformation: Data -> ViewResultDTO.
    """

    def render_title_screen(self, user_name: str) -> ViewResultDTO:
        """
        Renders the main Title Screen (Start Menu).
        :param user_name: Safe string name of the user.
        """
        # Безопасное форматирование. Если START_GREETING не содержит плейсхолдера, format игнорирует аргументы.
        # Если содержит {first_name} - подставит user_name.
        text = START_GREETING.format(first_name=user_name)

        kb = self._get_title_keyboard()

        return ViewResultDTO(text=text, kb=kb)

    def _get_title_keyboard(self):
        builder = InlineKeyboardBuilder()

        # Ключи в Buttons.START теперь совпадают с action в StartMenuCallback
        # "adventure": "⚔️ Начать приключение"
        # "settings": "⚙️ Настройки"

        for action, text in Buttons.START.items():
            cb = StartMenuCallback(action=action).pack()
            builder.button(text=text, callback_data=cb)

        builder.adjust(1)
        return builder.as_markup()
