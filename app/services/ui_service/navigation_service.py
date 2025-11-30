# app/services/ui_service/navigation_service.py
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

from app.resources.keyboards.callback_data import NavigationCallback, ServiceEntryCallback
from app.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from app.services.core_service.manager.account_manager import account_manager
from app.services.core_service.manager.world_manager import world_manager
from app.services.game_service.game_world_service import game_world_service
from app.services.ui_service.base_service import BaseUIService

# Точка спавна по умолчанию (Safe Zone)
DEFAULT_SPAWN_POINT = "portal_plats"


class NavigationService(BaseUIService):
    """
    Сервис-Оркестратор для Навигации.
    Используется в хандлерах
    """

    def __init__(
        self,
        char_id: int,
        state_data: dict[str, Any],
        symbiote_name: str | None = None,
    ):
        super().__init__(state_data=state_data, char_id=char_id)
        self.actor_name = symbiote_name or DEFAULT_ACTOR_NAME
        log.debug(f"Инициализирован NavigationService для char_id={self.char_id}")

    async def get_navigation_ui(self, state: str, loc_id: str) -> tuple[str, InlineKeyboardMarkup | None]:
        """
        Главный метод получения UI.
        """
        if state == "world":
            await world_manager.add_player_to_location(loc_id, self.char_id)

            nav_data = await game_world_service.get_location_for_navigation(loc_id)

            # Если данные не найдены — возвращаем None, чтобы запустить Unstuck
            if not nav_data:
                return (
                    f"<b>{self.actor_name}:</b> Ошибка реальности. Локация '{loc_id}' рассыпалась.",
                    None,
                )

            account_data = await account_manager.get_account_data(self.char_id)
            prev_loc_id = account_data.get("prev_location_id") if account_data else None

            text = await self._format_location_text(nav_data)
            kb = self._get_world_location_kb(nav_data.get("exits", {}), loc_id, prev_loc_id)

            return text, kb

        elif state == "s_d":
            return f"<b>{self.actor_name}:</b> (Заглушка) Вы в подземелье.", None

        else:
            return f"<b>{self.actor_name}:</b> Критическая ошибка координат.", None

    async def reload_current_ui(self) -> tuple[str, InlineKeyboardMarkup | None]:
        """
        Перезагружает UI. Включает механику 'Unstuck' (Аварийный телепорт).
        Если текущая локация сломана, переносит игрока на спавн.
        """
        data = await account_manager.get_account_data(self.char_id)
        if not data:
            return "Ошибка аккаунта", None

        current_state = data.get("state", "world")
        current_loc_id = data.get("location_id", DEFAULT_SPAWN_POINT)

        # 1. Пробуем загрузить текущую локацию
        text, kb = await self.get_navigation_ui(current_state, current_loc_id)

        # 2. Если клавиатуры нет (kb is None) — значит мы в "черной дыре"
        if kb is None:
            log.warning(
                f"User char_id={self.char_id} застрял в '{current_loc_id}'. Выполняем аварийный телепорт (Unstuck)."
            )

            # АВАРИЙНАЯ ЭВАКУАЦИЯ
            target_safe_zone = DEFAULT_SPAWN_POINT

            # А. Удаляем из старой (сломанной) локации (на всякий случай)
            await world_manager.remove_player_from_location(current_loc_id, self.char_id)

            # Б. Обновляем запись в Redis насильно
            await account_manager.update_account_fields(
                self.char_id,
                {
                    "location_id": target_safe_zone,
                    "prev_location_id": target_safe_zone,  # Сбрасываем историю
                },
            )

            # В. Получаем UI спавна
            text, kb = await self.get_navigation_ui("world", target_safe_zone)

            # Г. Добавляем сообщение о спасении
            text = (
                f"⚠️ <b>{self.actor_name}:</b> Критический сбой навигации detected.\n"
                "🌀 <i>Протокол аварийной эвакуации активирован...</i>\n\n"
                f"{text}"
            )

        return text, kb

    # --- 2. Приватные методы (Логика UI) ---

    async def _format_location_text(self, nav_data: dict) -> str:
        loc_name = nav_data.get("name", "Неизвестное место")
        loc_desc = nav_data.get("description", "...")

        text = f"<b>{self.actor_name}:</b> Локация идентифицирована.\n📍 <b>{loc_name}</b>\n\n{loc_desc}"

        exits = nav_data.get("exits", {})
        if isinstance(exits, dict) and exits:
            text += "\n\n<b>Визуальный обзор путей:</b>"
            for _target_id, exit_data in exits.items():
                if isinstance(exit_data, dict):
                    path_desc = exit_data.get("desc_next_room")
                    if path_desc:
                        text += f"\n👁 <i>{path_desc}</i>"
        return text

    def _get_world_location_kb(
        self, exits_dict: dict, current_loc_id: str, prev_loc_id: str | None
    ) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()

        if isinstance(exits_dict, dict):
            for target_id, exit_data in exits_dict.items():
                if isinstance(exit_data, dict):
                    button_text = exit_data.get("text_button", ">>>")

                    # 🔥 НОВАЯ ЛОГИКА: ПРОВЕРКА ПРЕФИКСА КЛЮЧА
                    if target_id.startswith("svc_"):
                        # Если это Сервисный Хаб, используем ServiceEntryCallback
                        callback_data = ServiceEntryCallback(char_id=self.char_id, target_loc=target_id).pack()
                        log.debug(f"Создан ServiceEntryCallback для {target_id}")

                    else:
                        # Иначе — обычная навигация
                        callback_data = NavigationCallback(action="move", target_id=target_id).pack()
                        log.debug(f"Создан NavigationCallback для {target_id}")

                    kb.button(text=button_text, callback_data=callback_data)
        kb.adjust(1)

        if prev_loc_id and prev_loc_id != current_loc_id:
            back_btn = InlineKeyboardButton(
                text="↩️ Шаг назад",
                callback_data=NavigationCallback(action="move", target_id=prev_loc_id).pack(),
            )
            kb.row(back_btn)

        return kb.as_markup()

    # --- 3. Логика Действий (Move) ---

    async def move_player(self, target_loc_id: str) -> tuple[float, str, InlineKeyboardMarkup | None] | None:
        current_data = await account_manager.get_account_data(self.char_id)
        if not current_data:
            return None

        current_state = current_data.get("state", "world")
        current_loc_id = current_data.get("location_id")

        if current_state == "world" and isinstance(current_loc_id, str):
            # Проверка существования целевой локации
            target_exists = await game_world_service.get_location_for_navigation(target_loc_id)
            if not target_exists:
                error_text = f"<b>{self.actor_name}:</b> Ошибка. Путь '{target_loc_id}' нестабилен или разрушен."
                return 0.0, error_text, None

            travel_time = 0.0
            current_loc_data = await game_world_service.get_location_for_navigation(current_loc_id)

            if current_loc_data:
                exits = current_loc_data.get("exits", {})
                target_exit = exits.get(target_loc_id)
                if target_exit and isinstance(target_exit, dict):
                    travel_time = float(target_exit.get("time_duration", 0))

            await world_manager.remove_player_from_location(current_loc_id, self.char_id)

            await account_manager.update_account_fields(
                self.char_id,
                {
                    "location_id": target_loc_id,
                    "prev_location_id": current_loc_id,
                },
            )

            new_text, new_kb = await self.get_navigation_ui("world", target_loc_id)
            return travel_time, new_text, new_kb

        return None
