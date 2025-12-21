from apps.common.schemas_dto.scenario_dto import ScenarioPayloadDTO


class ScenarioFormatter:
    """
    Форматтер для UI-компонентов сценария.
    Отвечает за сборку финального текста сообщения.
    """

    @staticmethod
    def format_scene_text(payload: ScenarioPayloadDTO) -> str:
        """
        Собирает финальный текст сообщения, добавляя отформатированный
        статус-бар в конец.
        """
        # 1. Формируем статус-бар (для Telegram это блок кода)
        status_block = ""
        if payload.status_bar:
            # Объединяем строки через разделитель " | "
            status_lines = " | ".join(payload.status_bar)
            status_block = f"<code>{status_lines}</code>"

        # 2. Собираем финальный текст (Текст + Статус-бар внизу)
        # Добавляем статус-бар только если он не пустой
        if status_block:
            return f"{payload.text}\n\n{status_block}"

        return payload.text
