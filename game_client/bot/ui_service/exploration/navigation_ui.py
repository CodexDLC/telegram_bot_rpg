# apps/bot/ui_service/exploration/navigation_ui.py

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

from apps.common.schemas_dto.exploration_dto import WorldNavigationDTO
from game_client.bot.resources.keyboards.callback_data import NavigationCallback, ServiceEntryCallback
from game_client.bot.ui_service.exploration.formatters.navigation_formatter import NavigationFormatter
from game_client.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO


class NavigationUI:
    """
    UI-компонент для отрисовки экрана навигации (Карты).
    """

    def __init__(self, char_id: int, actor_name: str):
        self.char_id = char_id
        self.actor_name = actor_name

    def render_location(self, dto: WorldNavigationDTO) -> ViewResultDTO:
        """
        Превращает DTO локации в текст сообщения и клавиатуру.
        """
        xy_coord = dto.loc_id.replace("_", ":")
        threat_tier = int(dto.flags.get("threat_tier", 0))
        threat_info = NavigationFormatter.get_threat_info(threat_tier)

        text = NavigationFormatter.format_composite_message(
            actor_name=self.actor_name,
            loc_name=dto.name,
            loc_desc=dto.description,
            xy_coord=xy_coord,
            threat_data=threat_info,
            visual_objects=dto.visual_objects,
            players_count=dto.players_count,
            active_battles=dto.active_battles,
            exits_data=dto.exits,
            current_loc_id=dto.loc_id,
            system_buttons_legend=None,
        )

        kb = self._get_world_location_kb(dto.exits, dto.loc_id, dto.flags)

        return ViewResultDTO(text=text, kb=kb)

    def _get_world_location_kb(self, exits_dict: dict, current_loc_id: str, flags: dict) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        btn_wall = InlineKeyboardButton(text="⛔️", callback_data="ignore")
        grid = {"n": btn_wall, "s": btn_wall, "w": btn_wall, "e": btn_wall}
        service_buttons = []

        try:
            cx, cy = map(int, current_loc_id.split("_"))
        except ValueError:
            log.error(f"NavUI | Error parsing coords: {current_loc_id}")
            cx, cy = 0, 0

        if isinstance(exits_dict, dict):
            for key, data in exits_dict.items():
                if not isinstance(data, dict):
                    continue

                if ":" in key:
                    pfx, tid = key.split(":", 1)
                else:
                    pfx, tid = "nav", key

                if pfx == "svc":
                    text = f"🚪 {data.get('text_button', 'Вход')}"
                    cb = ServiceEntryCallback(char_id=self.char_id, target_loc=tid).pack()
                    service_buttons.append(InlineKeyboardButton(text=text, callback_data=cb))
                    continue

                if pfx == "nav":
                    try:
                        tx, ty = map(int, tid.split("_"))
                        dx, dy = tx - cx, ty - cy
                        btn_text, dir_key = None, None

                        if dx == 0 and dy == -1:
                            dir_key, btn_text = "n", "⬆️ СЕВЕР"
                        elif dx == 0 and dy == 1:
                            dir_key, btn_text = "s", "⬇️ ЮГ"
                        elif dx == -1 and dy == 0:
                            dir_key, btn_text = "w", "⬅️ ЗАПАД"
                        elif dx == 1 and dy == 0:
                            dir_key, btn_text = "e", "➡️ ВОСТОК"

                        if dir_key and btn_text:
                            # Зашиваем время перехода в кнопку
                            travel_time = float(data.get("time_duration", 0.0))
                            cb = NavigationCallback(action="move", target_id=tid, t=travel_time).pack()
                            grid[dir_key] = InlineKeyboardButton(text=btn_text, callback_data=cb)

                    except ValueError:
                        continue

        btn_search = InlineKeyboardButton(text="🔍 ПОИСК", callback_data="nav:action:search")
        is_safe = flags.get("is_safe_zone", False)
        btn_context = InlineKeyboardButton(
            text="☮️ МИР" if is_safe else "⚔️ БОИ",
            callback_data="nav:action:safe_zone" if is_safe else "nav:action:battles",
        )
        btn_look = InlineKeyboardButton(text="👁 ОБЗОР", callback_data="nav:action:look_around")
        btn_social = InlineKeyboardButton(text="👥 ЛЮДИ", callback_data="nav:action:people")
        btn_auto = InlineKeyboardButton(text="🧭 АВТО", callback_data="nav:action:auto")

        kb.row(btn_search, grid["n"], btn_context)
        kb.row(grid["w"], btn_look, grid["e"])
        kb.row(btn_social, grid["s"], btn_auto)

        if service_buttons:
            kb.row(*service_buttons, width=1)

        return kb.as_markup()
