from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

from common.schemas.scenario import ScenarioButtonDTO, ScenarioPayloadDTO
from game_client.telegram_bot.base.view_dto import ViewResultDTO
from game_client.telegram_bot.features.scenario.resources.formatters.scenario_formatter import ScenarioFormatter
from game_client.telegram_bot.features.scenario.resources.keyboards.scenario_callback import ScenarioCallback


class ScenarioUIService:
    """
    Чистый UI-сервис для отрисовки сцен сценария.
    Принимает DTO и возвращает готовый ViewResultDTO.
    """

    def render_scene(self, payload: ScenarioPayloadDTO) -> ViewResultDTO:
        """
        Рендерит сцену: текст, статус-бар и адаптивную клавиатуру.
        """
        # 1. Адаптируем текст и кнопки (если кнопки слишком длинные)
        final_text, adapted_buttons = ScenarioFormatter.adapt_buttons_to_text(payload)

        # 2. Клавиатура собирается внутренним методом
        kb = self._build_adaptive_keyboard(adapted_buttons)

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
            kb.button(text=button.label, callback_data=ScenarioCallback(action="step", action_id=button.action_id))
        for button in long_buttons:
            kb.button(text=button.label, callback_data=ScenarioCallback(action="step", action_id=button.action_id))

        kb.adjust(*row_widths)

        return kb.as_markup()
