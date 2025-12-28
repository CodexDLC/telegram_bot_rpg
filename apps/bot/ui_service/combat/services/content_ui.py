from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.bot.resources.keyboards.combat_callback import (
    CombatControlCallback,
    CombatFlowCallback,
)
from apps.bot.ui_service.combat.formatters.combat_formatters import CombatFormatter
from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO
from apps.common.schemas_dto.combat_source_dto import CombatDashboardDTO


class CombatContentUI:
    """
    UI-сервис для Нижнего сообщения (Content Message).
    Stateless рендерер.
    """

    def __init__(self):
        self.fmt = CombatFormatter

    async def render_content(self, screen: str, snapshot: CombatDashboardDTO, selection: dict) -> ViewResultDTO:
        """
        Единая точка входа для рендера контента.
        screen: 'main', 'skills', 'items'
        """
        if screen == "skills":
            return await self._render_skills_menu(snapshot)
        elif screen == "items":
            return await self._render_items_menu(snapshot)
        else:
            # По умолчанию - Main Dashboard
            return await self._render_dashboard(snapshot, selection)

    # --- Internal Renderers ---

    async def _render_dashboard(self, snapshot: CombatDashboardDTO, selection: dict) -> ViewResultDTO:
        """Отрисовка основного экрана боя (Дашборд + Сетка)."""
        player_dict = snapshot.player.model_dump()
        player_dict["switch_charges"] = snapshot.switch_charges

        text = self.fmt.format_dashboard(
            player_state=player_dict,
            target_id=snapshot.current_target.char_id if snapshot.current_target else None,
            enemies_list=[e.model_dump() for e in snapshot.enemies],
            allies_list=[a.model_dump() for a in snapshot.allies],
            timer_text="⏳ <i>Ваш ход...</i>",
        )

        # Определяем layout из снапшота игрока
        layout = snapshot.player.weapon_layout

        if layout == "dual":
            kb = self._kb_dual_grid(selection)
        elif layout == "2h":
            kb = self._kb_2h_grid(selection)
        else:
            kb = self._kb_standard_grid(selection)

        return ViewResultDTO(text=text, kb=kb)

    async def _render_skills_menu(self, snapshot: CombatDashboardDTO) -> ViewResultDTO:
        """Меню активных умений."""
        active_skills = snapshot.player.effects

        # Временный хак: создаем объект с нужной структурой для форматтера
        class ActorMock:
            def __init__(self, dto):
                self.name = dto.name
                self.state = type(
                    "State", (), {"energy_current": dto.energy_current, "switch_charges": snapshot.switch_charges}
                )()

        actor_mock = ActorMock(snapshot.player)
        text = self.fmt.format_skills_menu(actor_mock, active_skills)

        kb = self._kb_skills_menu(active_skills)
        return ViewResultDTO(text=text, kb=kb)

    async def _render_items_menu(self, snapshot: CombatDashboardDTO) -> ViewResultDTO:
        """Меню предметов в поясе."""
        belt_items = snapshot.belt_items  # list[dict]

        text = "🎒 <b>Выберите предмет:</b>\n\n"
        if not belt_items:
            text += "<i>Пояс пуст.</i>"
        else:
            for item in belt_items:
                name = item.get("name", "Item")
                qty = item.get("quantity", 1)
                text += f"• {name} (x{qty})\n"

        kb = self._kb_items_menu(belt_items)
        return ViewResultDTO(text=text, kb=kb)

    # --- Keyboards ---

    def _kb_standard_grid(self, selection: dict) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        sel_atk = selection.get("atk_main")
        sel_def = selection.get("def")

        rows = [
            ("head", "🗡 Голова", "head_chest", "🛡 Гол+Груд"),
            ("chest", "🗡 Грудь", "chest_belly", "🛡 Груд+Жив"),
            ("belly", "🗡 Живот", "belly_legs", "🛡 Жив+Ноги"),
            ("legs", "🗡 Ноги", "legs_feet", "🛡 Ноги+Ступ"),
            ("feet", "🗡 Ступни", "feet_head", "🛡 Ступ+Гол"),
        ]

        for atk_id, atk_name, def_id, def_name in rows:
            txt_atk = f"✅ {atk_name}" if sel_atk == atk_id else atk_name
            cb_atk = CombatControlCallback(action="zone", layer="atk_main", value=atk_id).pack()

            txt_def = f"✅ {def_name}" if sel_def == def_id else def_name
            cb_def = CombatControlCallback(action="zone", layer="def", value=def_id).pack()

            kb.row(
                InlineKeyboardButton(text=txt_atk, callback_data=cb_atk),
                InlineKeyboardButton(text=txt_def, callback_data=cb_def),
            )

        return self._add_common_buttons(kb)

    def _kb_2h_grid(self, selection: dict) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        sel_atk = selection.get("atk_main")
        sel_def = selection.get("def")

        rows = [
            ("head", "🗡 Голова", "head", "🛡 Голова"),
            ("chest", "🗡 Грудь", "chest", "🛡 Грудь"),
            ("belly", "🗡 Живот", "belly", "🛡 Живот"),
            ("legs", "🗡 Ноги", "legs", "🛡 Ноги"),
            ("feet", "🗡 Ступни", "feet", "🛡 Ступни"),
        ]

        for atk_id, atk_name, def_id, def_name in rows:
            txt_atk = f"✅ {atk_name}" if sel_atk == atk_id else atk_name
            cb_atk = CombatControlCallback(action="zone", layer="atk_main", value=atk_id).pack()

            txt_def = f"✅ {def_name}" if sel_def == def_id else def_name
            cb_def = CombatControlCallback(action="zone", layer="def", value=def_id).pack()

            kb.row(
                InlineKeyboardButton(text=txt_atk, callback_data=cb_atk),
                InlineKeyboardButton(text=txt_def, callback_data=cb_def),
            )

        return self._add_common_buttons(kb)

    def _kb_dual_grid(self, selection: dict) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        sel_atk_m = selection.get("atk_main")
        sel_atk_o = selection.get("atk_off")
        sel_def = selection.get("def")

        rows = [
            ("head", "🗡 Голова", "head", "OH", "head_chest", "🛡 Г+Г"),
            ("chest", "🗡 Грудь", "chest", "OH", "chest_belly", "🛡 Г+Ж"),
            ("belly", "🗡 Живот", "belly", "OH", "belly_legs", "🛡 Ж+Н"),
            ("legs", "🗡 Ноги", "legs", "OH", "legs_feet", "🛡 Н+С"),
            ("feet", "🗡 Ступни", "feet", "OH", "feet_head", "🛡 С+Г"),
        ]

        for atk_m_id, atk_m_name, atk_o_id, atk_o_name, def_id, def_name in rows:
            txt_m = f"✅ {atk_m_name}" if sel_atk_m == atk_m_id else atk_m_name
            cb_m = CombatControlCallback(action="zone", layer="atk_main", value=atk_m_id).pack()

            txt_o = f"✅{atk_o_name}" if sel_atk_o == atk_o_id else atk_o_name
            cb_o = CombatControlCallback(action="zone", layer="atk_off", value=atk_o_id).pack()

            txt_def = f"✅ {def_name}" if sel_def == def_id else def_name
            cb_def = CombatControlCallback(action="zone", layer="def", value=def_id).pack()

            kb.row(
                InlineKeyboardButton(text=txt_m, callback_data=cb_m),
                InlineKeyboardButton(text=txt_o, callback_data=cb_o),
                InlineKeyboardButton(text=txt_def, callback_data=cb_def),
            )

        return self._add_common_buttons(kb)

    def _add_common_buttons(self, kb: InlineKeyboardBuilder) -> InlineKeyboardMarkup:
        cb_submit = CombatFlowCallback(action="submit").pack()
        kb.row(InlineKeyboardButton(text="🔥 В атаку!", callback_data=cb_submit))

        cb_skills = CombatControlCallback(action="nav", layer="root", value="skills").pack()
        cb_items = CombatControlCallback(action="nav", layer="root", value="items").pack()
        kb.row(
            InlineKeyboardButton(text="⚡ Умения", callback_data=cb_skills),
            InlineKeyboardButton(text="🎒 Предметы", callback_data=cb_items),
        )
        return kb.as_markup()

    def _kb_skills_menu(self, active_skills: list[str]) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        for skill_key in active_skills:
            cb = CombatControlCallback(action="pick", layer="abil", value=skill_key).pack()
            kb.button(text=skill_key.capitalize(), callback_data=cb)
        kb.adjust(2)

        cb_back = CombatControlCallback(action="nav", layer="root", value="main").pack()
        kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data=cb_back))
        return kb.as_markup()

    def _kb_items_menu(self, belt_items: list[dict]) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        for item in belt_items:
            item_id = item.get("id") or item.get("item_id")
            if item_id:
                cb = CombatControlCallback(action="pick", layer="item", value=str(item_id)).pack()
                name = item.get("name", "Item")
                qty = item.get("quantity", 1)
                kb.button(text=f"{name} (x{qty})", callback_data=cb)
        kb.adjust(2)

        cb_back = CombatControlCallback(action="nav", layer="root", value="main").pack()
        kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data=cb_back))
        return kb.as_markup()
