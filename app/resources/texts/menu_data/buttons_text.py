# app/resources/texts/menu_data/buttons_text.py


class ButtonsTextData:
    MENU_LAYOUTS = {
        "creation": ["logout"],
        "tutorial_stats": ["status", "logout"],
        "tutorial_skill": ["status", "navigation", "logout"],
        "in_game": ["status", "inventory", "navigation", "quick_heal", "logout"],
    }

    # 🔥 НОВЫЙ ЛЕЙАУТ БЕЗ LOGOUT ДЛЯ ОСНОВНОГО РЯДА
    MENU_LAYOUTS_MAIN = {
        "creation": [],
        "tutorial_stats": ["status"],
        "tutorial_skill": ["status", "navigation"],
        "in_game": ["status", "inventory", "navigation", "quick_heal"],
    }

    BUTTONS_MENU_FULL = {
        "status": "ℹ️ Статус",
        "inventory": "📦 Инвентарь",
        "navigation": "🗺️ Навигация",
        "quick_heal": "➕ Быстрое лечение",
        "logout": "[🔙 Выйти из мира ]",
        "arena_test": "⚔️ Тренировка (Тест)",
    }

    TEXT_MENU = "<code>Игровое меню</code>"
