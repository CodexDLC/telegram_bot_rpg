# frontend/telegram_bot/features/exploration/system/components/encounter_ui.py

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.frontend.telegram_bot.base.view_dto import ViewResultDTO
from src.frontend.telegram_bot.features.exploration.resources.keyboards.exploration_callbacks import (
    EncounterCallback,
)
from src.shared.schemas.exploration import DetectionStatus, EncounterDTO, EncounterOptionDTO, EncounterType


class EncounterUI:
    """
    UI-компонент для рендеринга encounter'ов (встреч).
    Форматирует текст и строит клавиатуру на основе EncounterDTO.
    """

    def render(self, dto: EncounterDTO) -> ViewResultDTO:
        """Рендерит encounter в зависимости от типа."""
        if dto.type == EncounterType.COMBAT:
            return self._render_combat(dto)
        elif dto.type == EncounterType.MERCHANT:
            return self._render_merchant(dto)
        elif dto.type == EncounterType.QUEST:
            return self._render_quest(dto)
        else:
            return self._render_narrative(dto)

    # =========================================================================
    # Combat Encounter
    # =========================================================================

    def _render_combat(self, dto: EncounterDTO) -> ViewResultDTO:
        """Рендерит боевой encounter."""
        text = self._format_ambush(dto) if dto.status == DetectionStatus.AMBUSH else self._format_detected(dto)

        kb = self._build_options_keyboard(dto.options, dto.id)
        return ViewResultDTO(text=text, kb=kb)

    def _format_ambush(self, dto: EncounterDTO) -> str:
        """Форматирует текст засады."""
        lines = [
            "⚔️ <b>ЗАСАДА!</b>",
            "",
            f"<i>{dto.description}</i>",
            "",
        ]

        # Enemies preview
        if dto.enemies:
            lines.append("<b>Противники:</b>")
            for enemy in dto.enemies:
                name = enemy.name or "???"
                level = f"Ур.{enemy.level}" if enemy.level else ""
                lines.append(f"  • {name} {level}")

        lines.append("\n<i>Бой неизбежен!</i>")
        return "\n".join(lines)

    def _format_detected(self, dto: EncounterDTO) -> str:
        """Форматирует текст обнаруженной угрозы."""
        lines = [
            "👁 <b>УГРОЗА ОБНАРУЖЕНА</b>",
            "",
            f"<b>{dto.title}</b>",
            f"<i>{dto.description}</i>",
            "",
        ]

        # Enemies preview (зависит от info_level)
        if dto.enemies:
            lines.append("<b>Разведка:</b>")
            for enemy in dto.enemies:
                if dto.info_level >= 1:
                    name = enemy.name or "Неизвестное существо"
                    level = f"[Ур.{enemy.level}]" if enemy.level and dto.info_level >= 2 else ""
                    hp = f"HP: ~{enemy.hp_percent}%" if enemy.hp_percent and dto.info_level >= 3 else ""
                    lines.append(f"  • {name} {level} {hp}".strip())
                else:
                    lines.append("  • ???")

        return "\n".join(lines)

    # =========================================================================
    # Other Encounters
    # =========================================================================

    def _render_merchant(self, dto: EncounterDTO) -> ViewResultDTO:
        """Рендерит встречу с торговцем."""
        lines = [
            "🛒 <b>ТОРГОВЕЦ</b>",
            "",
            f"<b>{dto.title}</b>",
            f"<i>{dto.description}</i>",
        ]
        text = "\n".join(lines)
        kb = self._build_options_keyboard(dto.options, dto.id)
        return ViewResultDTO(text=text, kb=kb)

    def _render_quest(self, dto: EncounterDTO) -> ViewResultDTO:
        """Рендерит квестовую встречу."""
        lines = [
            "📜 <b>СОБЫТИЕ</b>",
            "",
            f"<b>{dto.title}</b>",
            f"<i>{dto.description}</i>",
        ]
        text = "\n".join(lines)
        kb = self._build_options_keyboard(dto.options, dto.id)
        return ViewResultDTO(text=text, kb=kb)

    def _render_narrative(self, dto: EncounterDTO) -> ViewResultDTO:
        """Рендерит нарративную встречу."""
        lines = [
            f"📖 <b>{dto.title.upper()}</b>",
            "",
            f"{dto.description}",
        ]
        text = "\n".join(lines)
        kb = self._build_options_keyboard(dto.options, dto.id)
        return ViewResultDTO(text=text, kb=kb)

    # =========================================================================
    # Keyboard Building
    # =========================================================================

    def _build_options_keyboard(self, options: list[EncounterOptionDTO], encounter_id: str) -> InlineKeyboardMarkup:
        """Строит клавиатуру из списка опций."""
        builder = InlineKeyboardBuilder()

        for option in options:
            callback = EncounterCallback(action=option.id, target_id=encounter_id).pack()
            builder.button(text=option.label, callback_data=callback)

        # Располагаем кнопки по 2 в ряд
        builder.adjust(2)
        return builder.as_markup()
