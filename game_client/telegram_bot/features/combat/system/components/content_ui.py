from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from game_client.telegram_bot.common.dto.view_dto import ViewResultDTO
from game_client.telegram_bot.common.schemas.combat import CombatDashboardDTO
from game_client.telegram_bot.features.combat.resources.formatters.combat_formatters import CombatFormatter
from game_client.telegram_bot.features.combat.resources.keyboards.combat_callback import (
    CombatControlCallback,
    CombatFlowCallback,
)


class CombatContentUI:
    """
    UI-сервис для Нижнего сообщения (Content Message).
    Stateless рендерер.
    v2.0: Поддержка финтов и новой структуры RBC.
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
        """Отрисовка основного экрана боя (Дашборд + Финты)."""
        player_dict = snapshot.hero.model_dump()

        # Передаем полный объект цели (если есть)
        target_dict = snapshot.target.model_dump() if snapshot.target else None

        text = self.fmt.format_dashboard(
            player_state=player_dict,
            target_state=target_dict,
            enemies_list=[e.model_dump() for e in snapshot.enemies],
            allies_list=[a.model_dump() for a in snapshot.allies],
            timer_text="⏳ <i>Ваш ход...</i>",
        )

        # Рендерим клавиатуру с финтами
        kb = self._kb_feints_grid(snapshot, selection)

        return ViewResultDTO(text=text, kb=kb)

    async def _render_skills_menu(self, snapshot: CombatDashboardDTO) -> ViewResultDTO:
        """Меню активных умений (Заглушка)."""
        # TODO: Получать список абилок из DTO
        active_skills = snapshot.hero.effects  # Пока используем эффекты как заглушку

        # Временный хак для форматтера
        class ActorMock:
            def __init__(self, dto):
                self.name = dto.name
                self.state = type("State", (), {"energy_current": dto.energy_current, "switch_charges": 0})()

        actor_mock = ActorMock(snapshot.hero)
        text = self.fmt.format_skills_menu(actor_mock, active_skills)

        kb = self._kb_skills_menu(active_skills)
        return ViewResultDTO(text=text, kb=kb)

    async def _render_items_menu(self, snapshot: CombatDashboardDTO) -> ViewResultDTO:
        """Меню предметов в поясе (Заглушка)."""
        # TODO: Получать belt_items из DTO
        belt_items = []  # snapshot.belt_items

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

    def _kb_feints_grid(self, snapshot: CombatDashboardDTO, selection: dict) -> InlineKeyboardMarkup:
        """
        Клавиатура:
        1. Список финтов (Radio Button)
        2. Кнопка Атаки (Только если status == 'active')
        3. Навигация (Skills, Items)
        """
        kb = InlineKeyboardBuilder()

        # 1. Финты
        feints_map = snapshot.hero.feints
        selected_feint = selection.get("feint_id")

        if feints_map:
            for f_id, f_name in feints_map.items():
                is_selected = f_id == selected_feint
                label = f"✅ {f_name}" if is_selected else f"⭕ {f_name}"

                # Используем layer="feint" для обработки в Orchestrator
                cb = CombatControlCallback(action="zone", layer="feint", value=f_id).pack()
                kb.row(InlineKeyboardButton(text=label, callback_data=cb))

        # 2. Кнопка Атаки (Скрываем, если ждем)
        if snapshot.status == "active":
            cb_submit = CombatFlowCallback(action="submit").pack()
            kb.row(InlineKeyboardButton(text="⚔️ Атаковать", callback_data=cb_submit))
        else:
            # Можно добавить кнопку "Обновить" вместо атаки, если статус waiting
            # Но у нас есть авто-обновление через анимацию.
            # Оставим пустым или добавим "⏳ Ожидание..." (неактивную)
            kb.row(InlineKeyboardButton(text="⏳ Ожидание...", callback_data="ignore"))

        # 3. Навигация
        cb_skills = CombatControlCallback(action="nav", layer="root", value="skills").pack()
        cb_items = CombatControlCallback(action="nav", layer="root", value="items").pack()

        # Дары (Skills) и Предметы (Items)
        kb.row(
            InlineKeyboardButton(text="⚡ Дары", callback_data=cb_skills),
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
