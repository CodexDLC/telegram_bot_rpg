from typing import Any


class OnboardingFormatter:
    """
    Форматтер для текстов процесса онбординга.
    Отвечает за подстановку переменных (имя, пол) в шаблоны сообщений.
    """

    @staticmethod
    def format_text(template: str, context: dict[str, Any] | None = None) -> str:
        """
        Форматирует шаблон текста, подставляя значения из контекста.

        Args:
            template: Строка-шаблон (например, "Привет, {name}!")
            context: Словарь с данными (например, {"name": "Alex", "gender": "male"})

        Returns:
            Отформатированная строка.
        """
        if not context:
            return template

        # Подготовка данных для форматирования
        format_data = context.copy()

        # Преобразование технических значений в читаемые для UI
        if "gender" in format_data:
            format_data["gender"] = OnboardingFormatter._format_gender(format_data["gender"])

        try:
            # Используем format, игнорируя отсутствующие ключи (если текст не требует их)
            return template.format(**format_data)
        except (KeyError, ValueError):
            # Если данных не хватает для шаблона или формат неверен, возвращаем исходный текст
            return template

    @staticmethod
    def _format_gender(gender_code: str) -> str:
        """Преобразует код пола в красивую строку."""
        if gender_code == "male":
            return "♂ Мужчина"
        elif gender_code == "female":
            return "♀ Женщина"
        return gender_code
