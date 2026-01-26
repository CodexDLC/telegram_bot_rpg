import re

from common.schemas.scenario import ScenarioButtonDTO, ScenarioPayloadDTO


class ScenarioFormatter:
    """
    Форматтер для UI-компонентов сценария.
    Отвечает за сборку финального текста сообщения и адаптацию кнопок.
    """

    @staticmethod
    def format_scene_text(payload: ScenarioPayloadDTO) -> str:
        """
        Собирает финальный текст сообщения:
        1. Форматирует системные сообщения (System: ...).
        2. Добавляет статус-бар.
        """
        text = payload.text

        # 1. Форматирование системных сообщений
        # Ищем строки, начинающиеся с "System:" или "[...]:" и оборачиваем их в <code>
        # Пример: "System: ВНИМАНИЕ..." -> "<code>System: ВНИМАНИЕ...</code>"
        lines = text.split("\n")
        formatted_lines = []
        for line in lines:
            # Исправлено: убрано избыточное экранирование ]
            if re.match(r"^(System:|\[.*?]:)", line.strip()):
                formatted_lines.append(f"<code>{line.strip()}</code>")
            else:
                formatted_lines.append(line)

        text = "\n".join(formatted_lines)

        # 2. Формируем статус-бар
        status_block = ""
        if payload.status_bar:
            status_lines = " | ".join(payload.status_bar)
            status_block = f"<code>{status_lines}</code>"

        # 3. Сборка
        if status_block:
            return f"{text}\n\n{status_block}"

        return text

    @staticmethod
    def adapt_buttons_to_text(payload: ScenarioPayloadDTO, max_len: int = 30) -> tuple[str, list[ScenarioButtonDTO]]:
        """
        Проверяет длину кнопок. Если они слишком длинные:
        1. Добавляет список действий в текст сообщения.
        2. Возвращает список "коротких" кнопок (иконки или номера).

        Если кнопки короткие, возвращает исходный текст и кнопки.
        """
        buttons = payload.buttons
        if not buttons:
            return ScenarioFormatter.format_scene_text(payload), buttons

        # Проверяем, есть ли длинные кнопки
        if any(len(b.label) > max_len for b in buttons):
            # Режим "списка"
            action_list_text = "\n\n<b>Варианты действий:</b>"
            short_buttons = []

            for i, btn in enumerate(buttons, 1):
                # Пытаемся извлечь иконку (первый символ, если это эмодзи)
                # Упрощенно: берем первый символ и проверяем, не буква ли это
                # icon = btn.label.split()[0] if btn.label else str(i)

                # Формируем строку списка
                action_list_text += f"\n{i}. {btn.label}"

                # Создаем короткую кнопку
                # Если есть иконка, используем её, иначе номер
                short_label = f"[{i}]"
                # Можно попробовать оставить иконку, если она есть
                # if not icon.isalnum(): short_label = f"[{icon}]"

                short_buttons.append(ScenarioButtonDTO(label=short_label, action_id=btn.action_id))

            # Добавляем список к тексту (перед статус-баром, если он есть)
            # Для этого нам нужно сначала отформатировать текст без статус-бара, потом добавить список, потом статус-бар

            # 1. Форматируем основной текст (системные сообщения и т.д.)
            base_text = ScenarioFormatter.format_scene_text(payload)

            # Если в тексте уже есть статус-бар (он добавляется в конце format_scene_text),
            # нам нужно вставить список ПЕРЕД ним.
            # Это немного костыльно, лучше бы format_scene_text принимал доп. контент.

            # Перепишем логику: сначала форматируем текст, потом добавляем список, потом статус-бар
            # Но format_scene_text уже добавляет статус-бар.

            # Разделим base_text на тело и статус-бар
            parts = base_text.rsplit("\n\n<code>", 1)
            if len(parts) == 2:
                body, status = parts
                final_text = f"{body}{action_list_text}\n\n<code>{status}"
            else:
                final_text = f"{base_text}{action_list_text}"

            return final_text, short_buttons

        # Если кнопки короткие, возвращаем стандартное форматирование
        return ScenarioFormatter.format_scene_text(payload), buttons
