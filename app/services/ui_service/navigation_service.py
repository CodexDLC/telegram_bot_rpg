# app/services/ui_service/navigation_service.py
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

from app.resources.keyboards.callback_data import NavigationCallback, ServiceEntryCallback
from app.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from app.services.core_service.manager.account_manager import AccountManager
from app.services.core_service.manager.world_manager import WorldManager
from app.services.game_service.world.game_world_service import GameWorldService
from app.services.ui_service.base_service import BaseUIService

# Точка спавна по умолчанию (Safe Zone)
DEFAULT_SPAWN_POINT = "52_52"


class NavigationService(BaseUIService):
    """
    Сервис-Оркестратор для Навигации.
    """

    def __init__(
        self,
        char_id: int,
        state_data: dict[str, Any],
        account_manager: AccountManager,
        world_manager: WorldManager,
        game_world_service: GameWorldService,
        symbiote_name: str | None = None,
    ):
        super().__init__(state_data=state_data, char_id=char_id)
        self.actor_name = symbiote_name or DEFAULT_ACTOR_NAME
        self.account_manager = account_manager
        self.world_manager = world_manager
        self.game_world_service = game_world_service
        log.debug(f"Инициализирован NavigationService для char_id={self.char_id}")

    async def get_navigation_ui(self, state: str, loc_id: str) -> tuple[str, InlineKeyboardMarkup | None]:
        """
        Главный метод получения UI.
        """
        log.debug(f"get_navigation_ui | state={state}, loc_id={loc_id}")
        if state == "world":
            await self.world_manager.add_player_to_location(loc_id, self.char_id)

            nav_data = await self.game_world_service.get_location_for_navigation(loc_id)

            if not nav_data:
                log.warning(f"get_navigation_ui | Локация не найдена: loc_id={loc_id}")
                return (
                    f"<b>{self.actor_name}:</b> Ошибка реальности. Локация '{loc_id}' рассыпалась.",
                    None,
                )

            account_data = await self.account_manager.get_account_data(self.char_id)
            prev_loc_id = account_data.get("prev_location_id") if account_data else None
            log.debug(f"get_navigation_ui | prev_loc_id={prev_loc_id}")

            text = await self._format_location_text(nav_data)
            kb = self._get_world_location_kb(nav_data.get("exits", {}), loc_id, prev_loc_id)

            return text, kb

        elif state == "s_d":
            return f"<b>{self.actor_name}:</b> (Заглушка) Вы в подземелье.", None

        else:
            log.error(f"get_navigation_ui | Неизвестный state: {state}")
            return f"<b>{self.actor_name}:</b> Критическая ошибка координат.", None

    async def reload_current_ui(self) -> tuple[str, InlineKeyboardMarkup | None]:
        """
        Перезагружает UI. Включает механику 'Unstuck' (Аварийный телепорт).
        """
        log.debug(f"reload_current_ui | char_id={self.char_id}")
        data = await self.account_manager.get_account_data(self.char_id)
        if not data:
            log.error(f"reload_current_ui | Не удалось получить данные аккаунта для char_id={self.char_id}")
            return "Ошибка аккаунта", None

        current_state = data.get("state", "world")
        current_loc_id = data.get("location_id", DEFAULT_SPAWN_POINT)
        log.debug(f"reload_current_ui | current_state={current_state}, current_loc_id={current_loc_id}")

        text, kb = await self.get_navigation_ui(current_state, current_loc_id)

        if kb is None:
            log.warning(
                f"User char_id={self.char_id} застрял в '{current_loc_id}'. Выполняем аварийный телепорт (Unstuck)."
            )
            target_safe_zone = DEFAULT_SPAWN_POINT
            await self.world_manager.remove_player_from_location(current_loc_id, self.char_id)
            await self.account_manager.update_account_fields(
                self.char_id,
                {"location_id": target_safe_zone, "prev_location_id": target_safe_zone},
            )
            log.info(f"reload_current_ui | Unstuck | char_id={self.char_id} перемещен в {target_safe_zone}")
            text, kb = await self.get_navigation_ui("world", target_safe_zone)
            text = (
                f"⚠️ <b>{self.actor_name}:</b> Критический сбой навигации detected.\n"
                "🌀 <i>Протокол аварийной эвакуации активирован...</i>\n\n"
                f"{text}"
            )
        return text, kb

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

        nav_buttons = []
        service_buttons = []

        if isinstance(exits_dict, dict):
            for target_id_with_prefix, exit_data in exits_dict.items():
                if not isinstance(exit_data, dict):
                    continue

                button_text = exit_data.get("text_button", ">>>")

                try:
                    prefix, target_id = target_id_with_prefix.split(":", 1)
                except ValueError:
                    log.warning(f"Некорректный ключ выхода: {target_id_with_prefix}")
                    continue

                if prefix == "svc":
                    callback_data = ServiceEntryCallback(char_id=self.char_id, target_loc=target_id).pack()
                    button = InlineKeyboardButton(text=button_text, callback_data=callback_data)
                    service_buttons.append(button)
                    log.debug(f"Создана кнопка сервиса для {target_id}")
                elif prefix == "nav":
                    callback_data = NavigationCallback(action="move", target_id=target_id).pack()
                    button = InlineKeyboardButton(text=button_text, callback_data=callback_data)
                    nav_buttons.append(button)
                    log.debug(f"Создана кнопка навигации для {target_id}")

        if nav_buttons:
            kb.add(*nav_buttons)
            kb.adjust(2)

        if service_buttons:
            kb.row(*service_buttons, width=1)

        if prev_loc_id and prev_loc_id != current_loc_id:
            back_btn = InlineKeyboardButton(
                text="↩️ Шаг назад",
                callback_data=NavigationCallback(action="move", target_id=prev_loc_id).pack(),
            )
            kb.row(back_btn)

        return kb.as_markup()

    async def move_player(self, target_loc_id: str) -> tuple[float, str, InlineKeyboardMarkup | None] | None:
        log.debug(f"move_player | char_id={self.char_id}, target_loc_id={target_loc_id}")
        current_data = await self.account_manager.get_account_data(self.char_id)
        if not current_data:
            log.error(f"move_player | Не удалось получить данные аккаунта для char_id={self.char_id}")
            return None

        current_state = current_data.get("state", "world")
        current_loc_id = current_data.get("location_id")
        log.debug(f"move_player | current_state={current_state}, current_loc_id={current_loc_id}")

        if current_state == "world" and isinstance(current_loc_id, str):
            target_exists = await self.game_world_service.get_location_for_navigation(target_loc_id)
            if not target_exists:
                log.warning(f"move_player | Целевая локация не найдена: target_loc_id={target_loc_id}")
                error_text = f"<b>{self.actor_name}:</b> Ошибка. Путь '{target_loc_id}' нестабилен или разрушен."
                return 0.0, error_text, None

            travel_time = 0.0
            current_loc_data = await self.game_world_service.get_location_for_navigation(current_loc_id)
            log.debug(f"move_player | current_loc_data exists: {bool(current_loc_data)}")

            if current_loc_data:
                exits = current_loc_data.get("exits", {})
                # ИСПРАВЛЕНО: Ищем ключ с префиксом и без него для обратной совместимости и кнопки "Назад"
                full_target_key_with_prefix = f"nav:{target_loc_id}"
                target_exit = exits.get(full_target_key_with_prefix) or exits.get(target_loc_id)

                if target_exit and isinstance(target_exit, dict):
                    travel_time = float(target_exit.get("time_duration", 0))
                log.debug(f"move_player | travel_time={travel_time}")

            await self.world_manager.remove_player_from_location(current_loc_id, self.char_id)

            await self.account_manager.update_account_fields(
                self.char_id,
                {"location_id": target_loc_id, "prev_location_id": current_loc_id},
            )
            log.info(f"move_player | char_id={self.char_id} перемещен в {target_loc_id}")

            new_text, new_kb = await self.get_navigation_ui("world", target_loc_id)
            return travel_time, new_text, new_kb

        log.warning(f"move_player | Некорректное состояние для перемещения: current_state={current_state}")
        return None
