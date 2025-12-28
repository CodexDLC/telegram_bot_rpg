# app/services/ui_service/menu_service.py
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.keyboards.callback_data import LobbySelectionCallback, MeinMenuCallback
from apps.bot.resources.keyboards.status_callback import StatusNavCallback
from apps.bot.resources.texts.menu_data.buttons_text import ButtonsTextData
from apps.bot.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from apps.bot.ui_service.base_service import BaseUIService
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.services.core_service.manager.account_manager import AccountManager

# TODO [ARCH-DEBT]: Убрать прямой импорт Core. Регенерацию перенести в Cron/Background Worker.
from apps.game_core.game_service.game_sync.game_sync_service import GameSyncService


class MenuService(BaseUIService):
    """
    Сервис для создания динамических верхних меню.
    """

    def __init__(self, game_stage: str, state_data: dict, session: AsyncSession, account_manager: AccountManager):
        """
        Инициализирует сервис меню.
        """
        super().__init__(state_data=state_data)

        self.data = ButtonsTextData
        self.gs = game_stage
        self.session = session
        self.account_manager = account_manager
        # Используем дефолтное имя, так как в BaseUIService его больше нет
        self.actor_name = DEFAULT_ACTOR_NAME

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

        # ИСПРАВЛЕНО: Добавлена проверка на "world"
        if self.char_id and self.gs in ("in_game", "world"):
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
        # 🔥 ИСПОЛЬЗУЕМ СЛОВАРЬ БЕЗ LOGOUT
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

            # (Логика callback'ов)
            if key == "status":
                callback_data = StatusNavCallback(key="bio", char_id=self.char_id).pack()

            # 🔥 ЧИСТКА: Объединение navigation, inventory и refresh_menu
            elif key in ("navigation", "inventory", "refresh_menu"):
                callback_data = MeinMenuCallback(action=key, game_stage=self.gs, char_id=self.char_id).pack()

            # 🔥 УДАЛЕН arena_test

            else:
                log.warning(f"MenuService | skip_button reason='unknown_key' key='{key}'")
                continue

            kb.button(text=display_text, callback_data=callback_data)

        # Выравнивание основных кнопок (например, 2x2)
        # ИСПРАВЛЕНО: Добавлена проверка на "world"
        if self.gs in ("in_game", "world"):
            # Учитывая, что сейчас 4 кнопки, это должно быть adjust(4)
            kb.adjust(4)
        elif self.gs == "tutorial_skill":
            kb.adjust(2)

        # 2. 🔥 ДОБАВЛЕНИЕ КНОПКИ "ВЫЙТИ" НА НОВЫЙ РЯД (через MENU_LAYOUTS)
        if "logout" in self.data.MENU_LAYOUTS.get(self.gs, []):
            logout_text = buttons_full_data.get("logout", "Выйти")
            logout_callback = LobbySelectionCallback(action="logout").pack()

            # Используем .row(), чтобы кнопка заняла всю ширину
            kb.row(InlineKeyboardButton(text=logout_text, callback_data=logout_callback))

        log.debug(f"Клавиатура меню для game_stage='{self.gs}' успешно создана.")
        return kb.as_markup()

    async def run_full_refresh_action(self) -> tuple[str, InlineKeyboardMarkup]:
        """
        Выполняет логику принудительного обновления.
        ВАЖНО: Предполагается, что синхронизация состояния (реген) уже выполнена вызывающей стороной.
        """
        log.info(f"FullRefresh | rendering refreshed menu for char_id={self.char_id}")

        # 1. Получаем финальный вид меню с НОВЫМИ цифрами.
        # Убедитесь, что `get_data_menu` и его внутренние вызовы (напр. `_format_menu_text`)
        # также не выполняют синхронизацию состояния.
        text, kb = await self.get_data_menu()

        # 2. Добавляем поясняющий текст о результате обновления.
        sync_service = GameSyncService(self.session, self.account_manager)
        hp_cur, en_cur = await sync_service.get_current_vitals(self.char_id)
        hp_max, en_max = await sync_service.get_max_vitals(self.char_id)

        if (hp_cur >= hp_max) and (en_cur >= en_max):
            text += "\n✅ <i>Силы полностью восстановлены.</i>"
        else:
            text += "\n🔄 <i>Данные обновлены. Текущий реген применен.</i>"

        return text, kb
