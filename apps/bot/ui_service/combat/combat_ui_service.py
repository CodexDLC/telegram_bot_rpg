# app/services/ui_service/combat/combat_ui_service.py
import json
import time
from contextlib import suppress
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
from apps.common.schemas_dto import (
    CombatSessionContainerDTO,
    InventoryItemDTO,
    StatSourceData,
)
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.combat_manager import CombatManager

# TODO [ARCH-DEBT]: UI не должен считать статы. Создать фасадный метод в CombatService, возвращающий DTO с MaxHP.
from apps.game_core.game_service.combat.stats_calculator import StatsCalculator


class CombatUIService(BaseUIService):
    def __init__(
        self,
        user_id: int,
        char_id: int,
        session_id: str,
        state_data: dict[str, Any],
        combat_manager: CombatManager,
        account_manager: AccountManager,
    ):
        super().__init__(state_data=state_data, char_id=char_id)
        self.user_id = user_id
        self.session_id = session_id
        self.combat_manager = combat_manager
        self.account_manager = account_manager
        self.fmt = CombatFormatter
        self.LOG_PAGE_SIZE = 5
        log.debug(f"CombatUIService init: user={user_id}, char={char_id}, sess={session_id}")

    async def render_combat_log(self, page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
        all_logs_json = await self.combat_manager.get_combat_log_list(self.session_id)
        all_logs = []
        for log_json in all_logs_json:
            with suppress(json.JSONDecodeError):
                all_logs.append(json.loads(log_json))

        text = self.fmt.format_log(all_logs, page, self.LOG_PAGE_SIZE)
        kb = self._kb_combat_log(page, len(all_logs))
        return text, kb

    async def render_dashboard(self, current_selection: dict) -> tuple[str, InlineKeyboardMarkup]:
        meta = await self.combat_manager.get_session_meta(self.session_id)
        if meta and int(meta.get("active", 1)) == 0:
            return await self._render_results(meta)

        player_dto, enemies_data, allies_data = await self._prepare_dashboard_data()

        if player_dto and player_dto.state and player_dto.state.hp_current <= 0:
            return self._render_spectator_mode(enemies_data, allies_data)

        target_id, charges, targets_count = None, 0, 0
        if player_dto and player_dto.state:
            targets = player_dto.state.targets
            targets_count = len(targets)
            charges = player_dto.state.switch_charges
            if targets:
                target_id = targets[0]

        p_state_dict = self._extract_player_state(player_dto)
        p_state_dict["switch_charges"] = charges

        text = self.fmt.format_dashboard(
            player_state=p_state_dict,
            target_id=target_id,
            enemies_list=enemies_data,
            allies_list=allies_data,
            timer_text="⏳ <i>Ваш ход...</i>",
        )
        can_switch = charges > 0 and targets_count > 1
        kb = self._kb_combat_grid(current_selection, can_switch=can_switch)
        return text, kb

    async def render_skills_menu(self) -> tuple[str, InlineKeyboardMarkup]:
        actor = await self._get_my_actor_dto()
        if not actor or not actor.state:
            return "Ошибка данных.", InlineKeyboardBuilder().as_markup()

        active_skills = actor.active_abilities or []
        text = self.fmt.format_skills_menu(actor, active_skills)
        kb = self._kb_skills_menu(active_skills)
        return text, kb

    async def render_items_menu(self) -> tuple[str, InlineKeyboardMarkup]:
        actor = await self._get_my_actor_dto()
        if not actor:
            return "Ошибка данных.", InlineKeyboardBuilder().as_markup()

        belt_items = actor.belt_items
        text = self.fmt.format_items_menu(belt_items, actor.quick_slot_limit)
        kb = self._kb_items_menu(belt_items, actor.quick_slot_limit)
        return text, kb

    async def _render_results(self, meta: dict) -> tuple[str, InlineKeyboardMarkup]:
        winner = meta.get("winner", "none")
        start_time = int(meta.get("start_time", 0))
        end_time = int(meta.get("end_time", time.time()))
        duration = max(0, end_time - start_time)
        player_dto = await self._get_my_actor_dto()

        if not player_dto:
            return "Ошибка загрузки результатов.", InlineKeyboardBuilder().as_markup()

        text = self.fmt.format_results(player_dto, winner, duration)
        kb = InlineKeyboardBuilder()
        cb_leave = CombatActionCallback(action="leave").pack()
        kb.row(InlineKeyboardButton(text="🔙 Выйти в Хаб", callback_data=cb_leave))
        return text, kb.as_markup()

    def _render_spectator_mode(self, enemies: list, allies: list) -> tuple[str, InlineKeyboardMarkup]:
        enemies_text = self.fmt._format_unit_list(enemies, None, is_enemy=True)
        allies_text = ""
        if allies:
            formatted_allies = self.fmt._format_unit_list(allies, None, is_enemy=False)
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
        kb.row(InlineKeyboardButton(text="🔄 Наблюдать (Обновить)", callback_data=cb_refresh))
        return text, kb.as_markup()

    async def _prepare_dashboard_data(self) -> tuple[CombatSessionContainerDTO | None, list[dict], list[dict]]:
        participant_ids = await self.combat_manager.get_session_participants(self.session_id)
        player_dto, enemies_data, allies_data, my_team = None, [], [], "blue"
        all_actors = []

        for pid_str in participant_ids:
            pid = int(pid_str)
            raw = await self.combat_manager.get_actor_json(self.session_id, pid)
            if raw:
                dto = CombatSessionContainerDTO.model_validate_json(raw)
                all_actors.append(dto)
                if pid == self.char_id:
                    player_dto = dto
                    my_team = dto.team

        now = time.time()
        for actor in all_actors:
            pending_move = await self.combat_manager.get_pending_move(self.session_id, actor.char_id, self.char_id)
            hp_max = 100
            if actor.stats:
                hp_base = actor.stats.get("hp_max", StatSourceData(base=100))
                hp_max = int(StatsCalculator.calculate("hp_max", hp_base))

            info = {
                "char_id": actor.char_id,
                "name": actor.name,
                "hp_current": actor.state.hp_current if actor.state else 0,
                "hp_max": hp_max,
                "is_ready": bool(pending_move),
                "last_action_time": now,
            }
            if actor.char_id == self.char_id:
                continue
            elif actor.team == my_team:
                allies_data.append(info)
            else:
                enemies_data.append(info)
        return player_dto, enemies_data, allies_data

    def _extract_player_state(self, player_dto: CombatSessionContainerDTO | None) -> dict:
        if not player_dto or not player_dto.state:
            return {"hp_current": 0, "tokens": {}}
        hp_max = int(StatsCalculator.calculate("hp_max", player_dto.stats.get("hp_max", StatSourceData(base=100))))
        en_max = int(
            StatsCalculator.calculate("energy_max", player_dto.stats.get("energy_max", StatSourceData(base=100)))
        )
        return {
            "hp_current": player_dto.state.hp_current,
            "hp_max": hp_max,
            "energy_current": player_dto.state.energy_current,
            "energy_max": en_max,
            "tokens": player_dto.state.tokens,
        }

    def _kb_combat_log(self, page: int, total_items: int) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        total_pages = (total_items + self.LOG_PAGE_SIZE - 1) // self.LOG_PAGE_SIZE
        btns = []
        if page < total_pages - 1:
            cb_old = CombatLogCallback(page=page + 1).pack()
            btns.append(InlineKeyboardButton(text="< Ранее", callback_data=cb_old))
        if page > 0:
            cb_new = CombatLogCallback(page=page - 1).pack()
            btns.append(InlineKeyboardButton(text="Позже >", callback_data=cb_new))
        if btns:
            kb.row(*btns)
        cb_refresh = CombatActionCallback(action="refresh").pack()
        kb.row(InlineKeyboardButton(text="🔄 Обновить лог", callback_data=cb_refresh))
        return kb.as_markup()

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
            btn_atk = InlineKeyboardButton(text=txt_atk, callback_data=cb_atk)
            txt_def = f"✅ {def_name}" if def_id in sel_def else def_name
            cb_def = CombatZoneCallback(layer="def", zone_id=def_id).pack()
            btn_def = InlineKeyboardButton(text=txt_def, callback_data=cb_def)
            kb.row(btn_atk, btn_def)

        cb_skills = CombatActionCallback(action="menu").pack()
        kb.row(InlineKeyboardButton(text="⚡ Умения / 🎒 Предметы", callback_data=cb_skills))
        if can_switch:
            cb_switch = CombatActionCallback(action="switch_target").pack()
            kb.row(InlineKeyboardButton(text="🔄 Сменить цель (-1 тактика)", callback_data=cb_switch))
        cb_submit = CombatActionCallback(action="submit").pack()
        kb.row(InlineKeyboardButton(text="✅ Подтвердить", callback_data=cb_submit))
        return kb.as_markup()

    def _kb_skills_menu(self, active_skills: list[str]) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        for skill_key in active_skills:
            skill_name = skill_key.capitalize()
            btn_text = f"{skill_name}"
            cb = CombatActionCallback(action=f"skill_use:{skill_key}").pack()
            kb.button(text=btn_text, callback_data=cb)
        kb.adjust(2)
        nav_row = []
        cb_switch = CombatActionCallback(action="menu_items").pack()
        nav_row.append(InlineKeyboardButton(text="🎒 Предметы", callback_data=cb_switch))
        cb_back = CombatActionCallback(action="refresh").pack()
        nav_row.append(InlineKeyboardButton(text="🔙 Назад", callback_data=cb_back))
        kb.row(*nav_row)
        return kb.as_markup()

    def _kb_items_menu(self, belt_items: list[InventoryItemDTO], max_slots: int) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        if max_slots > 0:
            slots_map = {}
            for item in belt_items:
                if not item.quick_slot_position:
                    continue
                slot_num = item.quick_slot_position.split("_")[-1]
                slots_map[slot_num] = item

            for i in range(1, max_slots + 1):
                slot_str = str(i)
                item_in_slot = slots_map.get(slot_str)
                if item_in_slot:
                    btn_text = f"[{i}]"
                    cb = CombatItemCallback(action="use", item_id=item_in_slot.inventory_id).pack()
                else:
                    btn_text = f"• {i} •"
                    cb = "ignore"
                kb.button(text=btn_text, callback_data=cb)
            kb.adjust(4)

        nav_row = []
        cb_switch = CombatActionCallback(action="menu_skills").pack()
        nav_row.append(InlineKeyboardButton(text="⚡ Умения", callback_data=cb_switch))
        cb_back = CombatActionCallback(action="refresh").pack()
        nav_row.append(InlineKeyboardButton(text="🔙 Назад", callback_data=cb_back))
        kb.row(*nav_row)
        return kb.as_markup()

    async def _get_my_actor_dto(self) -> CombatSessionContainerDTO | None:
        raw = await self.combat_manager.get_actor_json(self.session_id, self.char_id)
        if raw:
            return CombatSessionContainerDTO.model_validate_json(raw)
        return None

    async def render_waiting_screen(self) -> tuple[str, InlineKeyboardMarkup]:
        text = (
            f"<b>{self.actor_name}:</b> Ход принят.\n\n"
            f"⏳ <i>Синхронизация с нейро-интерфейсом противника...</i>\n"
            f"Ожидаем ответного действия."
        )
        kb = InlineKeyboardBuilder()
        cb_refresh = CombatActionCallback(action="refresh").pack()
        kb.row(InlineKeyboardButton(text="🔄 Проверить статус", callback_data=cb_refresh))
        return text, kb.as_markup()
