# Ключи для хранения данных в FSM (Redis)

# Ключ для хранения координат UI (ID сообщений Menu и Content)
KEY_UI_COORDS = "ui_coords"

# Ключ для хранения контекста сессии (char_id и т.д.)
# TODO: Проверить, используется ли он еще где-то, или можно заменить на KEY_UI_COORDS
FSM_CONTEXT_KEY = "session_context"
