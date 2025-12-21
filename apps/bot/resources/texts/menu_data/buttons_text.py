"""
Модуль содержит текстовые константы для кнопок меню и их раскладок.

Определяет, какие кнопки должны отображаться в главном меню в зависимости
от текущего этапа игры (`game_stage`), а также тексты для этих кнопок.
"""


class ButtonsTextData:
    MENU_LAYOUTS = {
        "creation": ["logout"],
        "tutorial_stats": ["status", "logout"],
        "tutorial_skill": ["status", "navigation", "logout"],
        "in_game": ["status", "inventory", "navigation", "refresh_menu", "logout"],
        "world": ["status", "inventory", "navigation", "refresh_menu", "logout"],  # Добавлено для стадии 'world'
    }

    MENU_LAYOUTS_MAIN = {
        "creation": [],
        "tutorial_stats": ["status"],
        "tutorial_skill": ["status", "navigation"],
        "in_game": ["status", "inventory", "navigation", "refresh_menu"],
        "world": ["status", "inventory", "navigation", "refresh_menu"],  # Добавлено для стадии 'world'
    }

    BUTTONS_MENU_FULL = {
        "status": "ℹ️ Статус",
        "inventory": "📦 Инвентарь",
        "navigation": "🗺️ Навигация",
        "refresh_menu": "🔄 Обновить меню",
        "logout": "[🔙 Выйти из мира ]",
    }

    TEXT_MENU = "<code>Игровое меню</code>"
