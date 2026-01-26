# 📋 Arena Enums

[⬅️ Назад: Arena Manifest](../Manifest.md)

## 🤖 AI CONTEXT
Перечисления (Enums), используемые в логике Arena.

## 📍 Расположение
**Файл:** `common/schemas/enums.py` (или `backend/domains/user_features/arena/schemas/enums.py`)

## 📋 Enums

### `ArenaScreenEnum`
Определяет текущий экран UI.
```python
class ArenaScreenEnum(str, Enum):
    MAIN_MENU = "main_menu"
    MODE_MENU = "mode_menu"
    SEARCHING = "searching"
    MATCH_FOUND = "match_found"
```

### `ArenaModeEnum`
Режимы игры.
```python
class ArenaModeEnum(str, Enum):
    ONE_VS_ONE = "1v1"
    GROUP = "group"
    TOURNAMENT = "tournament"
```

### `ArenaActionEnum`
Действия пользователя (callback data).
```python
class ArenaActionEnum(str, Enum):
    MENU_MAIN = "menu_main"
    MENU_MODE = "menu_mode"
    JOIN_QUEUE = "join_queue"
    CHECK_MATCH = "check_match"
    CANCEL_QUEUE = "cancel_queue"
    LEAVE = "leave"
    START_BATTLE = "start_battle"
```