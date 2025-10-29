

callbacks_dict_button = {




}

# Кнопка LOGAUT

LOGAUT_TEXT = "[❌ Выйти из мира ❌]"


# клавиатура вызывается при команде /start
START_ADVENTURE = "🧭 Начать приключение!"
START_ADVENTURE_CALLBACK = "start_adventure"

# клавиатура для выбора пола

# --- КНОПКИ (Текст, соответствующий ЛОРу) ---
GENDER_MALE_TEXT = "⚓ Облик Мужчины"
GENDER_FEMALE_TEXT = "✨ Облик Женщины"

GENDER_MAP = {
    "male": "Мужчина",
    "female": "Женщина",
}


# Каллбеки
LOBBY_SELECT = "lobby:select"
LOBBY_CREATE = "lobby:create"
LOBBY_ACTION_INSPECT="lobby:action:inspect"
LOBBY_ACTION_LOGIN="lobby:action:login"

# Кнопки
LOBBY_LOGIN_TEXT = "[ ⚔️ Войти в мир ]"



class Buttons:
    # Стартовое приключение
    START = {
        "start_adventure": "🧭 Начать приключение!"
    }

    # Выбор пола
    GENDER = {
        "gender:male": "⚓ Облик Мужчины",
        "gender:female": "✨ Облик Женщины"
    }

    # Лобби
    LOBBY = {
        "lobby:select": "Выбор персонажа",  # текст можно динамически формировать
        "lobby:create": "[ ➕ Создать ]",
        "lobby:action:login": "[ ⚔️ Войти в мир ]",
        "logout": "[❌ Выйти из мира ❌]"
    }

    # Подтверждение
    CONFIRM = {
        "confirm": "Принять эту форму"
    }

    TUTORIAL_START_BUTTON = {
        "tut:start": """[ 🧠 ] "Я готов. Начинай." """
    }