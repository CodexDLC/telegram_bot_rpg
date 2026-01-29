from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from common.schemas.game_menu import GameMenuDTO, HUDDataDTO, MenuButtonDTO
from game_client.telegram_bot.base.view_dto import ViewResultDTO


class MenuUIService:
    """
    Сервис для рендеринга UI меню (Текст + Клавиатура).
    """

    def render(self, dto: GameMenuDTO) -> ViewResultDTO:
        """
        Основной метод рендеринга.
        """
        text = self._format_hud(dto.hud, dto.legend)
        kb = self._create_keyboard(dto.buttons)
        return ViewResultDTO(text=text, kb=kb)

    def _format_hud(self, hud: HUDDataDTO, legend: dict[str, str]) -> str:
        """
        Форматирует текст сообщения (HTML).
        """
        # 1. Header (Name + Mode)
        # Mode приходит уже локализованным с бэкенда (например, "Exploration")
        text = f"<b>👤 {hud.char_name}</b> | <i>{hud.current_mode}</i>\n"

        # 2. Vitals (HP/Energy)
        text += f"❤️ <b>HP:</b> {hud.hp}/{hud.max_hp}\n"
        text += f"⚡ <b>Energy:</b> {hud.energy}/{hud.max_energy}\n"

        # 3. Location
        text += f"📍 <b>Loc:</b> {hud.location_id}\n"

        # 4. Legend (Описание кнопок)
        if legend:
            text += "\n" + " | ".join([f"{k} {v}" for k, v in legend.items()])

        return text

    def _create_keyboard(self, buttons: list[MenuButtonDTO]) -> InlineKeyboardMarkup:
        """
        Генерирует клавиатуру.
        """
        builder = InlineKeyboardBuilder()

        for btn in buttons:
            if btn.is_active:
                builder.button(text=btn.text, callback_data=f"menu:{btn.id}")

        builder.adjust(3)

        return builder.as_markup()
