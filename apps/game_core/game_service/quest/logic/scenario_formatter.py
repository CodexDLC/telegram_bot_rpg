import re
from typing import Any

from apps.common.schemas_dto.scenario_dto import (
    ScenarioButtonDTO,
    ScenarioPayloadDTO,
    ScenarioResponseDTO,
)


class ScenarioFormatter:
    """
    Саппорт-класс для подготовки данных для API.
    Реализует парсинг тегов в тексте и сборку DTO ответа.
    """

    def __init__(self):
        # Паттерн для поиска тегов типа [#stats:str] или [#p_gold]
        self.tag_pattern = re.compile(r"\[#(?:stats:)?(\w+)\]")

    # --- 1. Text Processing (Парсинг переменных в тексте) ---

    def format_text(self, text: str, context: dict[str, Any]) -> str:
        """
        Заменяет плейсхолдеры в тексте на реальные значения из контекста.
        """
        if not text:
            return ""

        def replace_tag(match):
            var_name = match.group(1)
            value = context.get(var_name, f"Unknown:{var_name}")
            return str(value)

        return self.tag_pattern.sub(replace_tag, text)

    # --- 2. Status Bar Builder (Подготовка данных для статус-бара) ---

    def build_status_bar_data(self, master_config: dict[str, Any], context: dict[str, Any]) -> list[str]:
        """
        Формирует список строк для статус-бара.
        Пример: ["❤️ HP: 100", "💰 Золото: 50"]
        """
        fields = master_config.get("status_bar_fields", [])
        if not fields:
            return []

        status_parts = []
        for field in fields:
            label = field.get("label", "")
            key = field.get("key")
            val = context.get(key, "??")
            status_parts.append(f"{label} {val}")

        return status_parts

    # --- 3. DTO Builder (Сборка финального пакета) ---

    def build_dto(
        self,
        node_data: dict[str, Any],
        available_actions: list[dict[str, Any]],
        context: dict[str, Any],
        master_config: dict[str, Any],
    ) -> ScenarioResponseDTO:
        """
        Собирает итоговый DTO, который уйдет через REST API.
        """
        # Подготавливаем художественный текст
        raw_text = node_data.get("text_content", "")
        formatted_text = self.format_text(raw_text, context)

        # Собираем данные для статус-бара
        status_bar_lines = self.build_status_bar_data(master_config, context)

        # Формируем список кнопок
        buttons_dto = [
            ScenarioButtonDTO(label=action["label"], action_id=action["action_id"]) for action in available_actions
        ]

        # Формируем Payload
        payload = ScenarioPayloadDTO(
            node_key=node_data.get("node_key", "unknown"),
            text=formatted_text,
            status_bar=status_bar_lines,
            buttons=buttons_dto,
            is_terminal=node_data.get("is_terminal", False),
        )

        # Формируем Response
        return ScenarioResponseDTO(status="success", payload=payload)
