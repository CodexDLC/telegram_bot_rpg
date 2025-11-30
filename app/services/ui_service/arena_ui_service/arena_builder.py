# app/services/ui_service/arena_ui_service/arena_builder.py
from typing import Any  # Необходимо добавить для совместимости BaseUIService

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.keyboards.callback_data import ArenaQueueCallback
from app.services.ui_service.base_service import BaseUIService


class ArenaUIBuilder(BaseUIService):
    """
    UI-билдер для формирования главного меню Арены.
    Рендерит стартовый экран с режимами боя.
    """

    def __init__(self, char_id: int, state_data: dict[str, Any], session: AsyncSession):
        # state_data нужен, чтобы BaseUIService извлек actor_name
        super().__init__(char_id=char_id, state_data=state_data)
        self.session = session
        log.debug(f"Инициализирован ArenaUIBuilder для char_id={char_id}.")

    async def render_menu(self) -> tuple[str, InlineKeyboardMarkup | None]:
        """
        Главный метод, рендерит UI Арены.
        """
        # 🔥 ИСПОЛЬЗУЕМ НАСЛЕДОВАННЫЙ self.actor_name
        text = f"<b>{self.actor_name}:</b> Вы вошли в Ангар Арены. \n\nВыберите тип матча или покиньте полигон."
        kb = self._main_kb()

        return text, kb

    def _main_kb(self) -> InlineKeyboardMarkup:
        """
        Строит клавиатуру главного меню Арены (1v1, Group, Exit).
        """
        kb = InlineKeyboardBuilder()

        # Мы используем action="match_menu" для перехода в подменю,
        # где будет кнопка "Подать заявку" и "Просмотр статуса".

        # 1. Бой 1 на 1
        cb_1v1 = ArenaQueueCallback(char_id=self.char_id, action="match_menu", match_type="1v1").pack()
        kb.button(text="⚔️ 1 на 1 (Хаос)", callback_data=cb_1v1)

        # 2. Групповой бой (Заглушка)
        cb_group = ArenaQueueCallback(char_id=self.char_id, action="match_menu", match_type="group").pack()
        kb.button(text="👥 Групповой Бой (WIP)", callback_data=cb_group)

        # 3. Выйти
        cb_exit = ArenaQueueCallback(char_id=self.char_id, action="exit_service").pack()
        kb.button(text="🚪 Выйти с Полигона", callback_data=cb_exit)

        kb.adjust(1)

        return kb.as_markup()
