# frontend/telegram_bot/features/exploration/system/components/navigation_ui.py

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.frontend.telegram_bot.base.view_dto import ViewResultDTO
from src.frontend.telegram_bot.features.exploration.resources.keyboards.exploration_callbacks import (
    EncounterCallback,
    NavigationCallback,
)
from src.shared.schemas.exploration import AlertHudDTO, ExplorationHudDTO, GridButtonDTO, WorldNavigationDTO


class NavigationUI:
    """
    UI-компонент для рендеринга экрана навигации.
    Форматирует текст и строит клавиатуру на основе WorldNavigationDTO.
    """

    def render(self, dto: WorldNavigationDTO) -> ViewResultDTO:
        """Рендерит экран навигации."""
        text = self._format_text(dto)
        kb = self._build_keyboard(dto)
        return ViewResultDTO(text=text, kb=kb)

    # =========================================================================
    # Text Formatting
    # =========================================================================

    def _format_text(self, dto: WorldNavigationDTO) -> str:
        """Форматирует текст локации."""
        sections = []

        # Header
        xy_coord = dto.loc_id.replace("_", ":")
        header = f"📍 <b>{dto.title}</b> <code>[{xy_coord}]</code>"
        sections.append(header)

        # Description
        sections.append(f"\n<i>{dto.description}</i>")

        # Visual Objects
        if dto.visual_objects:
            sections.append("")
            for obj in dto.visual_objects:
                sections.append(f"🏛 <b>{obj}</b>")

        # HUD
        hud_text = self._format_hud(dto)
        if hud_text:
            sections.append(f"\n{hud_text}")

        return "\n".join(sections)

    def _format_hud(self, dto: WorldNavigationDTO) -> str:
        """Форматирует HUD (панель информации)."""
        hud = dto.hud

        if isinstance(hud, ExplorationHudDTO):
            threat_info = self._get_threat_info(hud.threat_tier)
            threat_icon = threat_info["emoji"]
            threat_label = threat_info["label"]

            lines = [
                "<code>╔══════════════════════════╗</code>",
                f"<code>║ 📟 {threat_icon} {threat_label:8} 👥 {hud.players_count:2} ⚔️ {hud.battles_count:2} ║</code>",
                "<code>╚══════════════════════════╝</code>",
            ]
            return "\n".join(lines)

        elif isinstance(hud, AlertHudDTO):
            icon = "⚠️" if hud.style == "warning" else "ℹ️" if hud.style == "info" else "🚫"
            return f"\n{icon} <b>{hud.message}</b>"

        # Fallback для legacy данных
        elif dto.threat_tier > 0 or dto.players_nearby > 0:
            threat_info = self._get_threat_info(dto.threat_tier)
            return f"<code>[ 📟 {threat_info['emoji']} {threat_info['label']} | 👥 {dto.players_nearby} ]</code>"

        return ""

    def _get_threat_info(self, tier: int) -> dict:
        """Возвращает иконку и метку угрозы по tier."""
        tiers = {
            0: {"emoji": "🟢", "label": "SAFE"},
            1: {"emoji": "🟡", "label": "LOW"},
            2: {"emoji": "🟡", "label": "LOW"},
            3: {"emoji": "🟠", "label": "MED"},
            4: {"emoji": "🟠", "label": "MED"},
            5: {"emoji": "🔴", "label": "HIGH"},
            6: {"emoji": "🔴", "label": "HIGH"},
            7: {"emoji": "⚫", "label": "HELL"},
        }
        return tiers.get(tier, {"emoji": "⚪", "label": "???"})

    # =========================================================================
    # Keyboard Building
    # =========================================================================

    def _build_keyboard(self, dto: WorldNavigationDTO) -> InlineKeyboardMarkup:
        """Строит клавиатуру на основе NavigationGridDTO."""
        kb = InlineKeyboardBuilder()
        grid = dto.grid

        # Row 1: NW, N, NE
        if grid.nw and grid.n and grid.ne:
            kb.row(self._make_button(grid.nw), self._make_button(grid.n), self._make_button(grid.ne))

        # Row 2: W, Center, E
        if grid.w and grid.center and grid.e:
            kb.row(self._make_button(grid.w), self._make_button(grid.center), self._make_button(grid.e))

        # Row 3: SW, S, SE
        if grid.sw and grid.s and grid.se:
            kb.row(self._make_button(grid.sw), self._make_button(grid.s), self._make_button(grid.se))

        # Row 4+: Services
        if grid.services:
            for service in grid.services:
                kb.row(self._make_button(service))

        return kb.as_markup()

    def _make_button(self, btn: GridButtonDTO) -> InlineKeyboardButton:
        """Создаёт кнопку из GridButtonDTO."""
        if not btn.is_active:
            if btn.id in ("n", "s", "w", "e"):
                return InlineKeyboardButton(text="⛔️", callback_data="noop")
            return InlineKeyboardButton(text=btn.label, callback_data="noop")

        callback_data = self._parse_action(btn.action, btn.id)
        return InlineKeyboardButton(text=btn.label, callback_data=callback_data)

    def _parse_action(self, action: str, btn_id: str) -> str:
        """Парсит action из DTO и создаёт callback_data."""
        if ":" not in action:
            if action == "look_around":
                return NavigationCallback(action="look_around").pack()
            return EncounterCallback(action=action).pack()

        prefix, value = action.split(":", 1)

        if prefix == "move":
            # action="move:target_id:time"
            # value = "target_id:time"
            parts = action.split(":")
            target_id = parts[1] if len(parts) > 1 else None
            duration = float(parts[2]) if len(parts) > 2 else 0.0

            return NavigationCallback(action="move", target_id=target_id, duration=duration).pack()

        elif prefix == "interact":
            return EncounterCallback(action=value).pack()
        elif prefix == "service":
            return EncounterCallback(action="use_service", target_id=value).pack()

        return EncounterCallback(action=action).pack()
