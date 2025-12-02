"""
Модуль содержит текстовые константы для кнопок и этапов игры.

Определяет тексты кнопок, используемых в UI, и перечисление `GameStage`
для обозначения текущего этапа прохождения игры персонажем.
"""

from enum import StrEnum


class Buttons:
    START = {"start_adventure": "🧭 Начать приключение!"}
    GENDER = {"gender:male": "⚓ Мужчина", "gender:female": "✨ Женщина"}
    LOBBY_KB_UP = {
        "select": "Выбор персонажа",
        "create": "[ ➕ Создать ]",
    }
    LOBBY_KB_DOWN = {"login": "[ ⚔️ Войти в мир ]", "delete": "[❌ Удалить персонажа]", "logout": "[🔙 Выйти из мира ]"}
    CONFIRM = {"confirm": "Принять эту форму"}
    TUTORIAL_START_BUTTON = {"tut:start": """[ 🧠 ] "Я готов. Начинай." """}


class GameStage(StrEnum):
    CREATION = "creation"
    TUTORIAL_STATS = "tutorial_stats"
    TUTORIAL_SKILL = "tutorial_skill"
    TUTORIAL_WORLD = "tutorial_world"
    IN_GAME = "in_game"
