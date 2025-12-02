# app/services/ui_service/arena_ui_service/arena_ui_service.py
from collections.abc import Awaitable, Callable
from functools import partial

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log
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

    def __init__(self, char_id: int, session: AsyncSession, state_data: dict):
        """
        Args:
            char_id: ID персонажа.
            session: Сессия SQLAlchemy.
            state_data: Данные состояния FSM.
        """
        super().__init__(state_data=state_data, char_id=char_id)
        self.session = session
        self._logic = ArenaService(session, char_id)
        log.debug(f"ArenaUIServiceInit | char_id={char_id}")

    # =========================================================================
    # 🎮 ACTIONS (Действия)
    # =========================================================================

    async def action_join_queue(self, mode: str) -> int | None:
        """
        Попытка вступить в очередь.

        Args:
            mode: Режим игры (e.g., "1v1").

        Returns:
            Gear Score персонажа, если успешно, иначе None.
        """
        log.info(f"ActionJoinQueue | char_id={self.char_id} mode={mode}")
        gs = await self._logic.join_queue(mode)
        if gs is None:
            log.warning(f"ActionJoinQueueFail | char_id={self.char_id} mode={mode}")
        return gs

    async def action_cancel_queue(self, mode: str) -> bool:
        """
        Отмена поиска матча.

        Args:
            mode: Режим игры.

        Returns:
            True, если отмена успешна.
        """
        log.info(f"ActionCancelQueue | char_id={self.char_id} mode={mode}")
        return await self._logic.cancel_queue(mode)

    async def action_create_shadow_battle(self, mode: str) -> str:
        """
        Создание боя с тенью при таймауте поиска.

        Args:
            mode: Режим игры.

        Returns:
            ID созданной сессии боя.
        """
        log.info(f"ActionCreateShadowBattle | char_id={self.char_id} mode={mode}")
        session_id = await self._logic.create_shadow_battle(mode)
        log.info(f"ShadowBattleCreated | session_id={session_id} char_id={self.char_id}")
        return session_id

    def get_check_func(self, mode: str) -> Callable[[int], Awaitable[str | None]]:
        """
        Возвращает partial-функцию для поллинга состояния матча.

        Args:
            mode: Режим игры.

        Returns:
            Функция, принимающая int (номер попытки) и возвращающая ID сессии или None.
        """
        log.debug(f"GetCheckFunc | char_id={self.char_id} mode={mode}")
        return partial(self._logic.check_match, mode)

    # =========================================================================
    # 🖼️ VIEWS (Отображение)
    # =========================================================================

    async def view_main_menu(self) -> tuple[str, InlineKeyboardMarkup]:
        """
        Рендерит главный экран Арены.

        Returns:
            Кортеж (текст, клавиатура).
        """
        log.debug(f"ViewMainMenu | char_id={self.char_id}")
        text = f"<b>{self.actor_name}:</b> Вы вошли в Ангар Арены.\n\nВыберите тип матча или покиньте полигон."
        kb = InlineKeyboardBuilder()
        cb_1v1 = ArenaQueueCallback(char_id=self.char_id, action="match_menu", match_type="1v1").pack()
        kb.button(text="⚔️ 1 на 1 (Хаос)", callback_data=cb_1v1)
        cb_group = ArenaQueueCallback(char_id=self.char_id, action="match_menu", match_type="group").pack()
        kb.button(text="👥 Групповой Бой (WIP)", callback_data=cb_group)
        cb_exit = ArenaQueueCallback(char_id=self.char_id, action="exit_service").pack()
        kb.button(text="🚪 Выйти с Полигона", callback_data=cb_exit)
        kb.adjust(1)
        return text, kb.as_markup()

    async def view_mode_menu(self, match_type: str) -> tuple[str, InlineKeyboardMarkup]:
        """
        Рендерит подменю выбранного режима.

        Args:
            match_type: Тип матча ("1v1", "group").

        Returns:
            Кортеж (текст, клавиатура).
        """
        log.debug(f"ViewModeMenu | char_id={self.char_id} match_type={match_type}")
        # TODO: В будущем вынести тексты в ресурсы
        text = (
            f"<b>{self.actor_name}:</b> Режим дуэли <b>[1x1]</b>.\n\n"
            f"Здесь правят личные навыки и удача. Никакой помощи, только ты и враг.\n"
            f"<i>Победа даст рейтинг и золото. Поражение ударит по гордости.</i>\n\n"
            f"Готов к бою?"
        )

        kb = InlineKeyboardBuilder()
        action = "submit_queue_1x1" if match_type == "1v1" else "submit_queue_group"
        cb_submit = ArenaQueueCallback(char_id=self.char_id, action=action, match_type=match_type).pack()
        kb.button(text="⚔️ Найти противника", callback_data=cb_submit)
        cb_back = ArenaQueueCallback(char_id=self.char_id, action="menu_main").pack()
        kb.row(InlineKeyboardButton(text="🔙 Назад в меню", callback_data=cb_back))
        kb.adjust(1)
        return text, kb.as_markup()

    async def view_searching_screen(self, match_type: str, gs: int | None = None) -> tuple[str, InlineKeyboardMarkup]:
        """
        Рендерит экран поиска матча.

        Args:
            match_type: Тип матча.
            gs: Gear Score игрока (опционально).

        Returns:
            Кортеж (текст, клавиатура).
        """
        log.debug(f"ViewSearchingScreen | char_id={self.char_id} match_type={match_type} gs={gs}")
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
