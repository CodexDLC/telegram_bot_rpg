from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO
from apps.bot.ui_service.scenario.formatters.scenario_formatter import ScenarioFormatter
from apps.common.schemas_dto.scenario_dto import ScenarioButtonDTO, ScenarioPayloadDTO


class ScenarioUIService:
    """
    Чистый UI-сервис для отрисовки сцен сценария.
    Принимает DTO и возвращает готовый ViewResultDTO.
    """

    def render_scene(self, payload: ScenarioPayloadDTO) -> ViewResultDTO:
        """
        Рендерит сцену: текст, статус-бар и адаптивную клавиатуру.
        """
        # 1. Получаем отформатированный текст через форматтер
        final_text = ScenarioFormatter.format_scene_text(payload)

        # 2. Клавиатура собирается внутренним методом
        kb = self._build_adaptive_keyboard(payload.buttons)

        return ViewResultDTO(text=final_text, kb=kb)

    def _build_adaptive_keyboard(self, buttons: list[ScenarioButtonDTO]) -> InlineKeyboardMarkup:
        """
        Строит адаптивную клавиатуру:
        - Короткие кнопки (до 20 символов) размещаются по 2 в ряд.
        - Длинные кнопки размещаются по 1 в ряд.
        """
        # Группируем кнопки по длине
        short_buttons = [b for b in buttons if len(b.label) <= 20]
        long_buttons = [b for b in buttons if len(b.label) > 20]

        # Формируем список row_widths для adjust
        row_widths = []
        if short_buttons:
            # Сколько полных рядов по 2
            full_rows = len(short_buttons) // 2
            row_widths.extend([2] * full_rows)
            # Если осталась одна кнопка
            if len(short_buttons) % 2 != 0:
                row_widths.append(1)

        if long_buttons:
            row_widths.extend([1] * len(long_buttons))

        # Пересоздаем билдер и добавляем все кнопки по порядку (короткие, потом длинные)
        kb = InlineKeyboardBuilder()
        for button in short_buttons:
            kb.button(text=button.label, callback_data=f"sc:{button.action_id}")
        for button in long_buttons:
            kb.button(text=button.label, callback_data=f"sc:{button.action_id}")

        kb.adjust(*row_widths)

        return kb.as_markup()
