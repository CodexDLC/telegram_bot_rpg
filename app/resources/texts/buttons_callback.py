from enum import StrEnum


class Buttons:
    # Стартовое приключение
    START = {
        "start_adventure": "🧭 Начать приключение!"
    }

    # Выбор пола
    GENDER = {
        "gender:male": "⚓ Мужчина",
        "gender:female": "✨ Женщина"
    }

    # Лобби
    LOBBY = {
        "lobby:select": "Выбор персонажа",  # текст можно динамически формировать
        "lobby:create": "[ ➕ Создать ]",
        "lobby:login": "[ ⚔️ Войти в мир ]",
        "logout": "[❌ Выйти из мира ❌]"
    }

    LOBBY_ACTION = {

        "lobby:action:bio" : "✔️ Базовая инфо",
        "lobby:action:stats" : "🔤 SPECIAL - STATS",

    }

    # Подтверждение
    CONFIRM = {
        "confirm": "Принять эту форму"
    }

    TUTORIAL_START_BUTTON = {
        "tut:start": """[ 🧠 ] "Я готов. Начинай." """
    }


class GameStage(StrEnum):
    CREATION = "creation"                   # Стадия по умолчанию в БД
    TUTORIAL_STATS = "tutorial_stats"       # "tutorial_1"
    TUTORIAL_SKILL = "tutorial_skill"       # "tutorial_skill"
    TUTORIAL_WORLD = "tutorial_world"       # На будущее
    IN_GAME = "in_game"                     # Обычная игра