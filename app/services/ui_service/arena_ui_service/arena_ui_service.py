# app/services/ui_service/arena_ui_service/arena_ui_service.py
from collections.abc import Awaitable, Callable
from functools import partial

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.keyboards.callback_data import ArenaQueueCallback
from app.services.game_service.arena.arena_service import ArenaService
from app.services.ui_service.base_service import BaseUIService


class ArenaUIService(BaseUIService):
    """
    FACADE UI SERVICE для Арены.
    Единственная точка входа для хэндлеров Арены.

    Ответственность:
    1. Actions: Вызов бизнес-логики (ArenaService).
    2. Views: Рендер интерфейсов (Текст + Кнопки).
    """

    def __init__(self, char_id: int, state_data: dict, session: AsyncSession):
        super().__init__(state_data=state_data, char_id=char_id)
        self.session = session
        # 🔥 СВЯЗЬ С ЛОГИКОЙ:
        # В будущем здесь будет self.api_client
        self._logic = ArenaService(session, char_id)

    # =========================================================================
    # 🎮 ACTIONS (Действия)
    # Хэндлеры вызывают эти методы, чтобы что-то СДЕЛАТЬ.
    # =========================================================================

    async def action_join_queue(self, mode: str) -> int | None:
        """Попытка вступить в очередь."""
        # Тут можно добавить UI-проверки (хватает ли денег на билет и т.д.)
        return await self._logic.join_queue(mode)

    async def action_cancel_queue(self, mode: str) -> bool:
        """Отмена поиска."""
        return await self._logic.cancel_queue(mode)

    async def action_create_shadow_battle(self, mode: str) -> str:
        """Создание боя с тенью (при таймауте)."""
        return await self._logic.create_shadow_battle(mode)

    def get_check_func(self, mode: str) -> Callable[[], Awaitable[str | None]]:
        """
        Возвращает функцию для поллинга (анимации ожидания).
        Хэндлеру не нужно знать, какой метод сервиса дергать.
        """
        return partial(self._logic.check_match, mode)

    # =========================================================================
    # 🖼️ VIEWS (Отображение)
    # Хэндлеры вызывают эти методы, чтобы что-то ПОКАЗАТЬ.
    # =========================================================================

    async def view_main_menu(self) -> tuple[str, InlineKeyboardMarkup]:
        """Главное меню Арены (Уровень 0)."""
        text = f"<b>{self.actor_name}:</b> Вы вошли в Ангар Арены.\n\nВыберите тип матча или покиньте полигон."

        kb = InlineKeyboardBuilder()

        # Кнопки режимов (ведут в подменю)
        cb_1v1 = ArenaQueueCallback(char_id=self.char_id, action="match_menu", match_type="1v1").pack()
        kb.button(text="⚔️ 1 на 1 (Хаос)", callback_data=cb_1v1)

        cb_group = ArenaQueueCallback(char_id=self.char_id, action="match_menu", match_type="group").pack()
        kb.button(text="👥 Групповой Бой (WIP)", callback_data=cb_group)

        # Выход
        cb_exit = ArenaQueueCallback(char_id=self.char_id, action="exit_service").pack()
        kb.button(text="🚪 Выйти с Полигона", callback_data=cb_exit)

        kb.adjust(1)
        return text, kb.as_markup()

    async def view_mode_menu(self, match_type: str) -> tuple[str, InlineKeyboardMarkup]:
        """Подменю режима (Уровень 1: Описание режима + Кнопка 'В бой')."""

        # TODO: В будущем вынести тексты в ресурсы
        text = (
            f"<b>{self.actor_name}:</b> Режим дуэли <b>[1x1]</b>.\n\n"
            f"Здесь правят личные навыки и удача. Никакой помощи, только ты и враг.\n"
            f"<i>Победа даст рейтинг и золото. Поражение ударит по гордости.</i>\n\n"
            f"Готов к бою?"
        )

        kb = InlineKeyboardBuilder()

        # Кнопка ПОИСК (Зависит от режима)
        action = "submit_queue_1x1" if match_type == "1v1" else "submit_queue_group"
        cb_submit = ArenaQueueCallback(char_id=self.char_id, action=action, match_type=match_type).pack()
        kb.button(text="⚔️ Найти противника", callback_data=cb_submit)

        # Кнопка НАЗАД
        cb_back = ArenaQueueCallback(char_id=self.char_id, action="menu_main").pack()
        kb.row(InlineKeyboardButton(text="🔙 Назад в меню", callback_data=cb_back))

        kb.adjust(1)
        return text, kb.as_markup()

    async def view_searching_screen(self, match_type: str, gs: int | None = None) -> tuple[str, InlineKeyboardMarkup]:
        """Экран ожидания (Searching...)."""

        gs_text = f"\n📊 Ваш GS: {gs}" if gs else ""
        text = (
            f"<b>{self.actor_name}:</b> 🔎 Сканирование сигнатур...\n\n"
            f"Поиск достойного соперника в режиме <b>{match_type}</b>.{gs_text}\n"
            f"<i>Ожидайте соединения...</i>"
        )

        kb = InlineKeyboardBuilder()
        cb_cancel = ArenaQueueCallback(char_id=self.char_id, action="cancel_queue", match_type=match_type).pack()
        kb.button(text="❌ Отмена", callback_data=cb_cancel)

        return text, kb.as_markup()
