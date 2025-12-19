# apps/bot/ui_service/combat/combat_ui_service.py
import json
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

from apps.bot.resources.keyboards.combat_callback import (
    CombatActionCallback,
    CombatItemCallback,
    CombatLogCallback,
    CombatZoneCallback,
)
from apps.bot.ui_service.base_service import BaseUIService
from apps.bot.ui_service.helpers_ui.formatters.combat_formatters import CombatFormatter
from apps.common.schemas_dto.combat_source_dto import CombatDashboardDTO


class CombatUIService(BaseUIService):
    """
    Тонкий UI-сервис боя.
    Принимает готовый Snapshot DTO и превращает его в текст и клавиатуры.
    """

    def __init__(self, state_data: dict[str, Any], char_id: int):
        super().__init__(state_data=state_data, char_id=char_id)
        self.fmt = CombatFormatter
        log.debug(f"CombatUIService (Thin) init: char={char_id}")

    async def render_dashboard(self, snapshot: CombatDashboardDTO, selection: dict) -> tuple[str, InlineKeyboardMarkup]:
        """Отрисовка основного экрана боя."""
        player_dict = snapshot.player.model_dump()
        player_dict["switch_charges"] = snapshot.switch_charges

        text = self.fmt.format_dashboard(
            player_state=player_dict,
            target_id=snapshot.current_target.char_id if snapshot.current_target else None,
            enemies_list=[e.model_dump() for e in snapshot.enemies],
            allies_list=[a.model_dump() for a in snapshot.allies],
            timer_text="⏳ <i>Ваш ход...</i>",
        )
        can_switch = snapshot.switch_charges > 0 and len(snapshot.enemies) > 1
        kb = self._kb_combat_grid(selection, can_switch=can_switch)
        return text, kb

    async def render_waiting_screen(self, snapshot: CombatDashboardDTO) -> tuple[str, InlineKeyboardMarkup]:
        """Экран ожидания просчета обмена."""
        text = (
            "<b>Ход принят.</b>\n\n"
            "⏳ <i>Ожидание ответного действия...</i>\n"
            f"<i>Целей в очереди: {snapshot.queue_count}</i>"
        )
        return text, InlineKeyboardBuilder().as_markup()

    async def render_spectator_mode(self, snapshot: CombatDashboardDTO) -> tuple[str, InlineKeyboardMarkup]:
        """Экран наблюдателя, если игрок пал."""
        enemies_text = self.fmt._format_unit_list([e.model_dump() for e in snapshot.enemies], None, is_enemy=True)
        allies_text = ""
        if snapshot.allies:
            formatted_allies = self.fmt._format_unit_list(
                [a.model_dump() for a in snapshot.allies], None, is_enemy=False
            )
            allies_text = f"\n\n<b>🔰 Союзники:</b>\n{formatted_allies}"

        text = (
            "💀 <b>ВЫ МЕРТВЫ</b>\n"
            "<i>Вы пали в бою, но ваша душа еще здесь...</i>\n\n"
            f"<b>🆚 Враги:</b>\n{enemies_text}"
            f"{allies_text}\n\n"
            "⏳ <i>Бой продолжается...</i>"
        )
        kb = InlineKeyboardBuilder()
        cb_refresh = CombatActionCallback(action="refresh").pack()
        kb.row(InlineKeyboardButton(text="🔄 Обновить (Наблюдать)", callback_data=cb_refresh))
        return text, kb.as_markup()

    async def render_results(self, snapshot: CombatDashboardDTO) -> tuple[str, InlineKeyboardMarkup]:
        """Экран итогов боя."""
        winner = snapshot.winner_team or "none"
        rewards = snapshot.rewards or {}
        text = self.fmt.format_results(
            player_snap=snapshot.player,
            winner_team=winner,
            duration=0,
            rewards=rewards,
        )
        kb = InlineKeyboardBuilder()
        cb_leave = CombatActionCallback(action="leave").pack()
        kb.row(InlineKeyboardButton(text="🔙 Выйти в Хаб", callback_data=cb_leave))
        return text, kb.as_markup()

    async def render_skills_menu(self, snapshot: CombatDashboardDTO) -> tuple[str, InlineKeyboardMarkup]:
        """Меню активных умений."""
        active_skills = snapshot.player.effects
        text = "⚡ <b>Выберите умение:</b>"
        kb = self._kb_skills_menu(active_skills)
        return text, kb

    async def render_items_menu(self, snapshot: CombatDashboardDTO) -> tuple[str, InlineKeyboardMarkup]:
        """Меню предметов в поясе."""
        belt_items = snapshot.belt_items
        text = "🎒 <b>Выберите предмет:</b>"
        kb = self._kb_items_menu(belt_items)
        return text, kb

    async def render_combat_log(self, snapshot: CombatDashboardDTO, page: int) -> tuple[str, InlineKeyboardMarkup]:
        """Отрисовка лога боя."""
        parsed_logs = []
        for log_json in snapshot.last_logs:
            try:
                parsed_logs.append(json.loads(log_json))
            except json.JSONDecodeError:
                continue
        text = self.fmt.format_log(parsed_logs, page, 5)
        kb = self._kb_log_pagination(snapshot.last_logs, page, 5)
        return text, kb

    def _kb_combat_grid(self, selection: dict, can_switch: bool) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        sel_atk = selection.get("atk", [])
        sel_def = selection.get("def", [])
        rows = [
            ("head", "🗡 Голова", "head_chest", "🛡 Гол+Груд"),
            ("chest", "🗡 Грудь", "chest_belly", "🛡 Груд+Жив"),
            ("belly", "🗡 Живот", "belly_legs", "🛡 Жив+Ноги"),
            ("legs", "🗡 Ноги", "legs_feet", "🛡 Ноги+Ступ"),
            ("feet", "🗡 Ступни", "feet_head", "🛡 Ступ+Гол"),
        ]
        for atk_id, atk_name, def_id, def_name in rows:
            txt_atk = f"✅ {atk_name}" if atk_id in sel_atk else atk_name
            cb_atk = CombatZoneCallback(layer="atk", zone_id=atk_id).pack()
            txt_def = f"✅ {def_name}" if def_id in sel_def else def_name
            cb_def = CombatZoneCallback(layer="def", zone_id=def_id).pack()
            kb.row(
                InlineKeyboardButton(text=txt_atk, callback_data=cb_atk),
                InlineKeyboardButton(text=txt_def, callback_data=cb_def),
            )

        # Кнопка "В атаку" должна быть всегда
        cb_submit = CombatActionCallback(action="submit").pack()
        kb.row(InlineKeyboardButton(text="🔥 В атаку!", callback_data=cb_submit))

        cb_skills = CombatActionCallback(action="menu").pack()
        kb.row(InlineKeyboardButton(text="⚡ Умения / 🎒 Предметы", callback_data=cb_skills))
        if can_switch:
            cb_switch = CombatActionCallback(action="switch_target").pack()
            kb.row(InlineKeyboardButton(text="🔄 Сменить цель (-1 тактика)", callback_data=cb_switch))
        return kb.as_markup()

    def _kb_skills_menu(self, active_skills: list[str]) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        for skill_key in active_skills:
            cb = CombatActionCallback(action=f"skill_use:{skill_key}").pack()
            kb.button(text=skill_key.capitalize(), callback_data=cb)
        kb.adjust(2)
        kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data=CombatActionCallback(action="refresh").pack()))
        return kb.as_markup()

    def _kb_items_menu(self, belt_items: list[dict]) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        for item in belt_items:
            cb = CombatItemCallback(action="use", item_id=item["id"]).pack()
            kb.button(text=f"{item['name']} (x{item['quantity']})", callback_data=cb)
        kb.adjust(2)
        kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data=CombatActionCallback(action="refresh").pack()))
        return kb.as_markup()

    def _kb_log_pagination(self, all_logs: list[str], page: int, page_size: int) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        total_pages = (len(all_logs) + page_size - 1) // page_size
        prev_page = page - 1
        next_page = page + 1
        buttons = []
        if prev_page >= 0:
            buttons.append(InlineKeyboardButton(text="⬅️", callback_data=CombatLogCallback(page=prev_page).pack()))
        buttons.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
        if next_page < total_pages:
            buttons.append(InlineKeyboardButton(text="➡️", callback_data=CombatLogCallback(page=next_page).pack()))
        kb.row(*buttons)
        kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data=CombatActionCallback(action="refresh").pack()))
        return kb.as_markup()
