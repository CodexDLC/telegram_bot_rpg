# app/services/ui_service/arena_ui_service/arena_builder.py
from typing import Any  # Необходимо добавить для совместимости BaseUIService

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
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

    async def render_mode_menu(self, match_type: str) -> tuple[str, InlineKeyboardMarkup]:
        """
        Меню конкретного режима (например, 1v1).
        """
        # Текст (можно потом усложнить статистикой)
        text = (
            f"<b>{self.actor_name}:</b> Режим дуэли <b>[1x1]</b>.\n\n"
            f"Здесь правят личные навыки и удача. Никакой помощи, только ты и враг.\n"
            f"<i>Победа даст рейтинг и золото. Поражение ударит по гордости.</i>\n\n"
            f"Готов к бою?"
        )

        kb = InlineKeyboardBuilder()

        # Кнопка ПОИСК
        cb_submit = ArenaQueueCallback(char_id=self.char_id, action="submit_queue_1x1", match_type=match_type).pack()
        kb.button(text="⚔️ Найти противника", callback_data=cb_submit)

        # Кнопка НАЗАД (в главное меню Арены)
        # ВАЖНО: action="menu_main" вернет нас в handler из arena_main.py
        cb_back = ArenaQueueCallback(char_id=self.char_id, action="menu_main").pack()
        kb.row(InlineKeyboardButton(text="🔙 Назад в меню", callback_data=cb_back))

        kb.adjust(1)
        return text, kb.as_markup()

    async def render_searching_screen(self, match_type: str) -> tuple[str, InlineKeyboardMarkup]:
        """
        Экран ожидания (Searching...).
        """
        text = (
            f"<b>{self.actor_name}:</b> 🔎 Сканирование сигнатур...\n\n"
            f"Поиск достойного соперника в режиме <b>{match_type}</b>.\n"
            f"<i>Ожидайте соединения...</i>"
        )

        kb = InlineKeyboardBuilder()

        # Кнопка ОТМЕНА
        cb_cancel = ArenaQueueCallback(char_id=self.char_id, action="cancel_queue", match_type=match_type).pack()
        kb.button(text="❌ Отмена", callback_data=cb_cancel)

        return text, kb.as_markup()
