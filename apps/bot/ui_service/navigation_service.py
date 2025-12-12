from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

from apps.bot.resources.keyboards.callback_data import NavigationCallback, ServiceEntryCallback
from apps.bot.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from apps.bot.ui_service.base_service import BaseUIService
from apps.bot.ui_service.helpers_ui.formatters.navigation_formatter import NavigationFormatter
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.combat_manager import CombatManager
from apps.common.services.core_service.manager.world_manager import WorldManager

# TODO [ARCH-DEBT]: Разделить GameWorldService на Reader (для UI) и Logic (для Core).
# UI не должен импортировать логику мира напрямую.
from apps.game_core.game_service.world.game_world_service import GameWorldService

# Точка спавна по умолчанию (Safe Zone)
DEFAULT_SPAWN_POINT = "52_52"


class NavigationService(BaseUIService):
    """
    Сервис-Оркестратор для Навигации.
    Формирует UI на основе данных из Redis (WorldManager, CombatManager).
    """

    def __init__(
        self,
        char_id: int,
        state_data: dict[str, Any],
        account_manager: AccountManager,
        world_manager: WorldManager,
        game_world_service: GameWorldService,
        combat_manager: CombatManager,
        symbiote_name: str | None = None,
    ):
        super().__init__(state_data=state_data, char_id=char_id)
        self.actor_name = symbiote_name or DEFAULT_ACTOR_NAME
        self.account_manager = account_manager
        self.world_manager = world_manager
        self.game_world_service = game_world_service
        self.combat_manager = combat_manager
        log.debug(f"NavigationService | status=initialized char_id={self.char_id}")

    async def get_navigation_ui(self, state: str, loc_id: str) -> tuple[str, InlineKeyboardMarkup | None]:
        """
        Сборка полного UI локации (Текст + Клавиатура).
        """
        log.debug(f"get_navigation_ui | state={state}, loc_id={loc_id}")

        if state == "world":
            # 1. Отмечаем присутствие игрока в локации (Redis)
            await self.world_manager.add_player_to_location(loc_id, self.char_id)

            # 2. Получаем данные локации (Layer 3)
            nav_data = await self.game_world_service.get_location_for_navigation(loc_id)

            if not nav_data:
                log.warning(f"get_navigation_ui | Локация не найдена: loc_id={loc_id}")
                return (
                    f"<b>{self.actor_name}:</b> ⚠️ Ошибка реальности. Локация '{loc_id}' рассыпалась.",
                    None,
                )

            # --- СБОР ДАННЫХ ДЛЯ ФОРМАТТЕРА ---

            # Координаты (52_52 -> 52:52)
            xy_coord = loc_id.replace("_", ":")

            # Флаги и Угроза
            flags = nav_data.get("flags", {})
            threat_tier = flags.get("threat_tier", 0)
            threat_info = NavigationFormatter.get_threat_info(threat_tier)

            # Список игроков в локации (исключая себя)
            players_set = await self.world_manager.get_players_in_location(loc_id)
            players_set.discard(str(self.char_id))
            players_count = len(players_set)

            # Проверка активных боев
            active_battles = 0
            if players_count > 0:
                for pid in players_set:
                    # Метод get_player_status должен быть в CombatManager
                    st = await self.combat_manager.get_player_status(int(pid))
                    if st and st.startswith("combat:"):
                        active_battles += 1

            # Визуальные объекты (Входы в здания)
            visual_objects = []
            service_key = nav_data.get("service")
            if service_key:
                service_map = {
                    "arena": "Вход: Арена",
                    "taverna": "Таверна 'Едальня'",
                    "town_hall": "Палатка Совета",
                    "market": "Рынок",
                }
                # Находим первый ключ из карты, который содержится в service_key
                for key, text in service_map.items():
                    if key in service_key:
                        visual_objects.append(text)
                        break
                else:
                    # Если ни один известный ключ не найден, добавляем "Неизвестное строение"
                    visual_objects.append("Неизвестное строение")

            # 3. Формирование Текста (через новый NavigationFormatter)
            text = NavigationFormatter.format_composite_message(
                actor_name=self.actor_name,
                loc_name=nav_data.get("name", "???"),
                loc_desc=nav_data.get("description", "..."),
                xy_coord=xy_coord,
                threat_data=threat_info,
                visual_objects=visual_objects,
                players_count=players_count,
                active_battles=active_battles,
                exits_data=nav_data.get("exits", {}),
                current_loc_id=loc_id,
                system_buttons_legend=None,
            )

            # 4. Формирование Клавиатуры (3x3 Grid)
            kb = self._get_world_location_kb(
                nav_data.get("exits", {}),
                loc_id,
                flags,
            )

            return text, kb

        elif state == "s_d":
            # Заглушка для подземелий (Solo Dungeon)
            return f"<b>{self.actor_name}:</b> (Заглушка) Вы в подземелье.", None

        else:
            log.error(f"get_navigation_ui | Неизвестный state: {state}")
            return f"<b>{self.actor_name}:</b> Критическая ошибка координат.", None

    async def reload_current_ui(self) -> tuple[str, InlineKeyboardMarkup | None]:
        """
        Перезагружает UI для текущей локации игрока.
        Включает механику 'Unstuck' (Аварийный телепорт), если локация сломана.
        """
        data = await self.account_manager.get_account_data(self.char_id)
        if not data:
            return "Ошибка аккаунта", None

        current_state = data.get("state", "world")
        current_loc_id = data.get("location_id", DEFAULT_SPAWN_POINT)

        text, kb = await self.get_navigation_ui(current_state, current_loc_id)

        # Если клавиатуры нет (значит, локация сломана или нет выходов), делаем Unstuck
        if kb is None:
            log.warning(f"User char_id={self.char_id} застрял в '{current_loc_id}'. Unstuck activated.")
            target_safe_zone = DEFAULT_SPAWN_POINT

            # Удаляем из старой, пишем в новую
            await self.world_manager.remove_player_from_location(current_loc_id, self.char_id)
            await self.account_manager.update_account_fields(
                self.char_id,
                {"location_id": target_safe_zone, "prev_location_id": target_safe_zone},
            )

            text, kb = await self.get_navigation_ui("world", target_safe_zone)
            text = f"⚠️ <b>{self.actor_name}:</b> Сбой навигации.\n🌀 <i>Протокол аварийной эвакуации...</i>\n\n{text}"

        return text, kb

    async def move_player(self, target_loc_id: str) -> tuple[float, str, InlineKeyboardMarkup | None] | None:
        """
        Перемещает игрока в новую локацию.
        Возвращает: (время_перехода, текст, клавиатура).
        """
        log.debug(f"move_player | char_id={self.char_id}, target_loc_id={target_loc_id}")
        current_data = await self.account_manager.get_account_data(self.char_id)
        if not current_data:
            return None

        current_state = current_data.get("state", "world")
        current_loc_id = current_data.get("location_id")

        if current_state == "world" and isinstance(current_loc_id, str):
            # Проверка существования целевой локации
            target_exists = await self.game_world_service.get_location_for_navigation(target_loc_id)
            if not target_exists:
                return 0.0, f"<b>{self.actor_name}:</b> Путь '{target_loc_id}' заблокирован.", None

            travel_time = 0.0
            current_loc_data = await self.game_world_service.get_location_for_navigation(current_loc_id)

            if current_loc_data:
                exits = current_loc_data.get("exits", {})
                # Поддержка ключей с префиксом nav: и без него
                full_target_key = f"nav:{target_loc_id}"
                target_exit = exits.get(full_target_key) or exits.get(target_loc_id)

                if target_exit and isinstance(target_exit, dict):
                    travel_time = float(target_exit.get("time_duration", 0))

            # Перемещение в Redis
            await self.world_manager.remove_player_from_location(current_loc_id, self.char_id)
            await self.account_manager.update_account_fields(
                self.char_id,
                {"location_id": target_loc_id, "prev_location_id": current_loc_id},
            )

            new_text, new_kb = await self.get_navigation_ui("world", target_loc_id)
            return travel_time, new_text, new_kb

        return None

    def _get_world_location_kb(self, exits_dict: dict, current_loc_id: str, flags: dict) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()

        # 1. Инициализация сетки ЗАГЛУШКАМИ (Стена/Тупик)
        # Если выхода нет — показываем "⛔️"
        btn_wall = InlineKeyboardButton(text="⛔️", callback_data="ignore")

        grid = {"n": btn_wall, "s": btn_wall, "w": btn_wall, "e": btn_wall}

        # 2. Сервисные кнопки (Входы)
        service_buttons = []

        # 3. Парсинг текущих координат
        try:
            cx, cy = map(int, current_loc_id.split("_"))
        except ValueError:
            log.error(f"NavUI | Error parsing coords: {current_loc_id}")
            cx, cy = 0, 0

        # 4. Распределение выходов (Перезаписываем "Стену" на "Стрелку" там, где есть проход)
        if isinstance(exits_dict, dict):
            for key, data in exits_dict.items():
                if not isinstance(data, dict):
                    continue

                # Парсим ID
                if ":" in key:
                    pfx, tid = key.split(":", 1)
                else:
                    pfx, tid = "nav", key

                # Входы в здания
                if pfx == "svc":
                    text = f"🚪 {data.get('text_button', 'Вход')}"
                    cb = ServiceEntryCallback(char_id=self.char_id, target_loc=tid).pack()
                    service_buttons.append(InlineKeyboardButton(text=text, callback_data=cb))
                    continue

                # Навигация
                if pfx == "nav":
                    try:
                        tx, ty = map(int, tid.split("_"))
                        dx = tx - cx
                        dy = ty - cy

                        btn_text, dir_key = None, None

                        # Логика: (0, -1) = Север (Y уменьшается вверх)
                        if dx == 0 and dy == -1:
                            dir_key, btn_text = "n", "⬆️ СЕВЕР"
                        elif dx == 0 and dy == 1:
                            dir_key, btn_text = "s", "⬇️ ЮГ"
                        elif dx == -1 and dy == 0:
                            dir_key, btn_text = "w", "⬅️ ЗАПАД"
                        elif dx == 1 and dy == 0:
                            dir_key, btn_text = "e", "➡️ ВОСТОК"

                        if dir_key and btn_text:
                            cb = NavigationCallback(action="move", target_id=tid).pack()
                            grid[dir_key] = InlineKeyboardButton(text=btn_text, callback_data=cb)

                    except ValueError:
                        continue

        # 5. Сборка Сетки 3x3

        # [NW] ПОИСК
        btn_search = InlineKeyboardButton(text="🔍 ПОИСК", callback_data="nav:action:search")

        # [NE] БОИ / МИР
        is_safe = flags.get("is_safe_zone", False)
        if is_safe:
            btn_context = InlineKeyboardButton(text="☮️ МИР", callback_data="nav:action:safe_zone")
        else:
            btn_context = InlineKeyboardButton(text="⚔️ БОИ", callback_data="nav:action:battles")

        # [C] ОБЗОР
        btn_look = InlineKeyboardButton(text="👁 ОБЗОР", callback_data="nav:action:look_around")

        # [SW] ЛЮДИ
        btn_social = InlineKeyboardButton(text="👥 ЛЮДИ", callback_data="nav:action:people")

        # [SE] АВТОПИЛОТ
        btn_auto = InlineKeyboardButton(text="🧭 АВТО", callback_data="nav:action:auto")

        # Ряд 1: [ ПОИСК ] [ СЕВЕР/⛔️ ] [ БОИ ]
        kb.row(btn_search, grid["n"], btn_context)

        # Ряд 2: [ ЗАПАД/⛔️ ] [ ОБЗОР ] [ ВОСТОК/⛔️ ]
        kb.row(grid["w"], btn_look, grid["e"])

        # Ряд 3: [ ЛЮДИ ] [ ЮГ/⛔️ ] [ АВТО ]
        kb.row(btn_social, grid["s"], btn_auto)

        # 6. Сервисы (Входы)
        if service_buttons:
            kb.row(*service_buttons, width=1)

        return kb.as_markup()

    def _btn_dummy(self) -> InlineKeyboardButton:
        """Создает пустую прозрачную кнопку-заглушку."""
        return InlineKeyboardButton(text="⚫️", callback_data="ignore")
