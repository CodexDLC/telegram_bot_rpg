from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

from apps.bot.resources.keyboards.callback_data import ArenaQueueCallback


class ArenaUIService:
    """
    Чистый UI-сервис для Арены.
    Отвечает только за рендеринг интерфейсов (текст + кнопки).
    Не содержит бизнес-логики и не делает вызовов к другим сервисам.
    """

    def __init__(self, char_id: int, actor_name: str):
        """
        Args:
            char_id: ID персонажа.
            actor_name: Имя персонажа.
        """
        self.char_id = char_id
        self.actor_name = actor_name
        log.debug(f"ArenaUIService | Initialized for char_id={char_id}")

    async def view_main_menu(self) -> tuple[str, InlineKeyboardMarkup]:
        """
        Рендерит главный экран Арены (Уровень 0).
        """
        text = f"<b>{self.actor_name}:</b> Вы вошли в Ангар Арены.\n\nВыберите тип матча или покиньте полигон."
        kb = InlineKeyboardBuilder()

        cb_1v1 = ArenaQueueCallback(char_id=self.char_id, action="match_menu", match_type="1v1").pack()
        kb.button(text="⚔️ Арена: Схватка (1x1)", callback_data=cb_1v1)

        cb_group = ArenaQueueCallback(char_id=self.char_id, action="match_menu", match_type="group").pack()
        kb.button(text="👥 Арена: Командные бои", callback_data=cb_group)

        cb_exit = ArenaQueueCallback(char_id=self.char_id, action="exit_service").pack()
        kb.button(text="🚪 Выйти с Полигона", callback_data=cb_exit)
        kb.adjust(1)
        return text, kb.as_markup()

    async def view_mode_menu(self, match_type: str) -> tuple[str, InlineKeyboardMarkup]:
        """
        Рендерит подменю выбранного режима.
        """
        if match_type == "1v1":
            text = (
                f"<b>{self.actor_name}:</b> Режим дуэли <b>[1x1]</b>.\n\n"
                f"Здесь правят личные навыки и удача. Никакой помощи, только ты и враг.\n"
                f"<i>Победа даст рейтинг и золото. Поражение ударит по гордости.</i>\n\n"
                f"Готов к бою?"
            )
            kb = InlineKeyboardBuilder()
            # Эта кнопка теперь будет обрабатываться оркестратором
            cb_submit = ArenaQueueCallback(char_id=self.char_id, action="toggle_queue", match_type=match_type).pack()
            kb.button(text="⚔️ Найти противника", callback_data=cb_submit)
            cb_back = ArenaQueueCallback(char_id=self.char_id, action="menu_main").pack()
            kb.row(InlineKeyboardButton(text="🔙 Назад в меню", callback_data=cb_back))
            kb.adjust(1)
            return text, kb.as_markup()

        elif match_type == "group":
            # Логика для групповых боев остается прежней
            text = f"<b>{self.actor_name}:</b> Раздел <b>[Командные бои]</b> (WIP)."
            kb = InlineKeyboardBuilder()
            cb_back = ArenaQueueCallback(char_id=self.char_id, action="menu_main").pack()
            kb.row(InlineKeyboardButton(text="🔙 Назад в меню", callback_data=cb_back))
            return text, kb.as_markup()

        return "Неизвестный режим.", InlineKeyboardBuilder().as_markup()

    async def view_searching_screen(self, match_type: str, gs: int | None) -> tuple[str, InlineKeyboardMarkup]:
        """
        Рендерит экран поиска матча.
        """
        gs_text = f"\n📊 Ваш GS: {gs}" if gs else ""
        text = (
            f"<b>{self.actor_name}:</b> 🔎 Сканирование сигнатур...\n\n"
            f"Поиск достойного соперника в режиме <b>{match_type}</b>.{gs_text}\n"
            f"<i>Ожидайте соединения...</i>"
        )
        kb = InlineKeyboardBuilder()
        # Кнопка отмены теперь также будет вести на toggle_queue
        cb_cancel = ArenaQueueCallback(char_id=self.char_id, action="toggle_queue", match_type=match_type).pack()
        kb.button(text="❌ Отмена", callback_data=cb_cancel)
        return text, kb.as_markup()

    async def view_match_found(
        self, session_id: str | None, metadata: dict[str, Any]
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Рендерит экран найденного матча с кнопкой начала боя.
        """
        opponent_name = metadata.get("opponent_name", "Тень")
        text = f"✅ <b>Противник найден: {opponent_name}</b>\n\nПодтвердите готовность к бою."
        kb = InlineKeyboardBuilder()
        cb_start = ArenaQueueCallback(char_id=self.char_id, action="start_battle").pack()
        kb.button(text="⚔️ В БОЙ", callback_data=cb_start)
        return text, kb.as_markup()
