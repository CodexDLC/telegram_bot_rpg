# app/services/ui_service/menu_service.py
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.keyboards.callback_data import LobbySelectionCallback, MeinMenuCallback
from app.resources.keyboards.status_callback import StatusNavCallback
from app.resources.texts.menu_data.buttons_text import ButtonsTextData
from app.services.core_service.manager.account_manager import AccountManager
from app.services.game_service.game_sync_service import GameSyncService
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.base_service import BaseUIService


# 🔥 НАСЛЕДУЕМСЯ ОТ BASE_UI_SERVICE
class MenuService(BaseUIService):
    """
    Сервис для создания динамических верхних меню.
    """

    # 🔥 УБРАЛИ char_id/actor_name из __init__ — они идут через BaseUIService.
    # Добавили session для получения актуальных HP/EN.
    def __init__(self, game_stage: str, state_data: dict, session: AsyncSession, account_manager: AccountManager):
        """
        Инициализирует сервис меню.
        """
        # 🔥 ВЫЗОВ БАЗОВОГО КЛАССА: Устанавливает self.char_id, self.actor_name и self.state_data
        super().__init__(state_data=state_data)

        self.data = ButtonsTextData
        self.gs = game_stage
        self.session = session
        self.account_manager = account_manager

        # 🔥 ПОЛУЧЕНИЕ КЭШИРОВАННОГО char_name ИЗ state_data
        session_context = self.state_data.get(FSM_CONTEXT_KEY, {})
        self.char_name = session_context.get("char_name", f"Персонаж {self.char_id}")

        log.debug(f"Инициализирован {self.__class__.__name__} для game_stage='{self.gs}', char_id={self.char_id}")

    async def get_data_menu(self) -> tuple[str, InlineKeyboardMarkup]:
        """
        Возвращает текст и клавиатуру для текущего меню.
        """
        log.debug("Запрос на получение данных меню.")
        text = await self._format_menu_text()
        kb = self._create_menu_kb()
        return text, kb

    async def _format_menu_text(self) -> str:
        """
        Форматирует текст меню с HP, Energy и списком кнопок.
        """
        base_text = self.data.TEXT_MENU

        if self.char_id and self.gs == "in_game":
            sync_service = GameSyncService(self.session, self.account_manager)
            await sync_service.synchronize_player_state(self.char_id)

            hp_cur, en_cur = await sync_service.get_current_vitals(self.char_id)
            hp_max, en_max = await sync_service.get_max_vitals(self.char_id)

            buttons_map = {
                k: v
                for k, v in self.data.BUTTONS_MENU_FULL.items()
                if k in self.data.MENU_LAYOUTS_MAIN.get(self.gs, [])
            }

            info_block = (
                f"<b>{self.actor_name}:</b> [ Текущий статус ]\n\n"
                f"<code>"
                f"├ Имя: {self.char_name}\n"
                f"├ ❤️ HP: {hp_cur}/{hp_max}\n"
                f"└ ⚡ EN: {en_cur}/{en_max}\n"
                f"</code>\n"
                f"<b>[ Меню ]</b>\n"
                f"<code>\n"
            )

            for key in buttons_map:
                full_text = self.data.BUTTONS_MENU_FULL.get(key)
                if full_text:
                    parts = full_text.split()
                    icon = parts[0]
                    clean_text = " ".join(parts[1:]) if len(parts) > 1 else ""

                    info_block += f"├ {icon} {clean_text}\n"

            info_block += "</code>"
            return info_block

        return base_text

    def _create_menu_kb(self) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        # 🔥 ИСПОЛЬЗУЕМ НОВЫЙ СЛОВАРЬ ДЛЯ КНОПОК БЕЗ LOGOUT
        menu_layouts = self.data.MENU_LAYOUTS_MAIN
        buttons_full_data = self.data.BUTTONS_MENU_FULL

        buttons_to_create = menu_layouts.get(self.gs, [])

        # 1. Создание основных кнопок (в сетке)
        for key in buttons_to_create:
            button_text = buttons_full_data.get(key)
            if not button_text:
                continue

            # Логика извлечения минималистичного текста
            display_text = button_text.split()[0]
            if len(display_text) > 3 and not any(c in display_text for c in ["[", "]", "⚔️"]):
                display_text = display_text[0]

            # (Логика callback'ов остается прежней)
            if key == "status":
                callback_data = StatusNavCallback(key="bio", char_id=self.char_id).pack()

            elif key == "quick_heal" or key in ("navigation", "inventory"):
                callback_data = MeinMenuCallback(action=key, game_stage=self.gs, char_id=self.char_id).pack()

            elif key == "arena_test":
                callback_data = MeinMenuCallback(action="arena_start", game_stage=self.gs, char_id=self.char_id).pack()

            else:
                continue

            kb.button(text=display_text, callback_data=callback_data)

        # Выравнивание основных кнопок (например, 2x2)
        if self.gs == "in_game":
            kb.adjust(4)  # 4 кнопки в ряд
        elif self.gs == "tutorial_skill":
            kb.adjust(2)  # 2 кнопки в ряд
        # ❗ Внимание: для creation/tutorial_stats не нужны adjust, так как там 0 или 1 кнопка

        # 2. 🔥 ДОБАВЛЕНИЕ КНОПКИ "ВЫЙТИ" НА НОВЫЙ РЯД
        # Проверяем, нужна ли кнопка logout для текущей стадии (она нужна всегда, кроме FSM login)
        if "logout" in self.data.MENU_LAYOUTS.get(self.gs, []):
            logout_text = buttons_full_data.get("logout", "Выйти")
            logout_callback = LobbySelectionCallback(action="logout").pack()

            # Используем .row(), чтобы кнопка заняла всю ширину
            kb.row(InlineKeyboardButton(text=logout_text, callback_data=logout_callback))

        log.debug(f"Клавиатура меню для game_stage='{self.gs}' успешно создана.")
        return kb.as_markup()
