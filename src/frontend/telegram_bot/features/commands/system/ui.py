from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.frontend.bot.resources.texts.buttons_callback import Buttons
from src.frontend.bot.resources.texts.ui_messages import START_GREETING
from src.frontend.telegram_bot.base.view_dto import ViewResultDTO
from src.frontend.telegram_bot.features.account.resources.keyboards.account_callbacks import LobbyEntryCallback
from src.frontend.telegram_bot.features.commands.resources.keyboards.commands_callbacks import SettingsCallback


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
        text = START_GREETING.format(first_name=user_name)
        kb = self._get_title_keyboard()
        return ViewResultDTO(text=text, kb=kb)

    def _get_title_keyboard(self):
        builder = InlineKeyboardBuilder()

        # Adventure -> Account (Lobby)
        builder.button(text=Buttons.START["adventure"], callback_data=LobbyEntryCallback(action="enter").pack())

        # Settings -> Commands feature
        builder.button(text=Buttons.START["settings"], callback_data=SettingsCallback(action="open").pack())

        builder.adjust(1)
        return builder.as_markup()
