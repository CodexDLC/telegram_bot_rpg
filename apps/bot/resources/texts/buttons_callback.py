# apps/bot/resources/texts/buttons_callback.py


class Buttons:
    """
    Контейнер для текстов и callback_data кнопок.
    """

    START = {
        "adventure": "⚔️ Начать приключение",
        "settings": "⚙️ Настройки",
    }

    LOBBY_KB_UP = {"create": "➕ Создать"}

    LOBBY_KB_DOWN = {
        "login": "🎮 Войти в игру",
        "delete": "❌ Удалить",
        "logout": "🔙 Выход",  # Добавили кнопку
    }

    GENDER = {"male": "Мужской", "female": "Женский"}

    CONFIRM = {"confirm": "Подтвердить"}

    TUTORIAL_START_BUTTON = {"tut:start": "👁 Открыть глаза"}
