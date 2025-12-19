from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.bot.resources.keyboards.callback_data import NavigationCallback


class StubUIService:
    """
    Универсальный UI-сервис-заглушка для временно недоступных хабов.
    """

    def __init__(self, title: str, char_id: int):
        self.title = title
        self.char_id = char_id

    async def render_stub(self) -> tuple[str, InlineKeyboardMarkup]:
        """
        Рендерит сообщение о недоступности сервиса и кнопку "Назад".
        """
        text = f"⚙️ <b>{self.title}</b>\n\n<i>Сервис временно недоступен. Ведутся технические работы.</i>"

        kb = InlineKeyboardBuilder()
        # Кнопка "Назад" просто инициирует обновление карты (рефреш)
        kb.button(text="🔙 Назад", callback_data=NavigationCallback(action="refresh", target_id="").pack())

        return text, kb.as_markup()
