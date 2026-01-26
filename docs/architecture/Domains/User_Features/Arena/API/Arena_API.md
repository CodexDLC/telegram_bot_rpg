# 🔌 Arena API Specification

[⬅️ Назад: Arena Manifest](../Manifest.md)

## 🤖 AI CONTEXT
API арены работает через единый action-based эндпоинт. Gateway маршрутизирует действия на соответствующие методы Service. Все ответы упакованы в `CoreResponseDTO` с `header` (`current_state`) и `payload`.

## 📍 Base Path
`/arena/{char_id}/action`

## 🔹 Endpoints

### POST `/arena/{char_id}/action`
Универсальный эндпоинт для всех действий арены.

**Path Parameters:**

| Param | Type | Description |
| :--- | :--- | :--- |
| `char_id` | `int` | ID персонажа |

**Request Body:**

```json
{
  "action": "string",
  "mode": "string | null",
  "value": "any | null"
}
```

**Actions:**

| Action | Mode | Value | Описание |
| :--- | :--- | :--- | :--- |
| `menu_main` | - | - | Получить главное меню арены |
| `menu_mode` | `1v1` / `group` | - | Получить меню режима |
| `join_queue` | `1v1` | - | Встать в очередь |
| `check_match` | `1v1` | - | Проверить статус матча |
| `cancel_queue` | `1v1` | - | Отменить поиск |
| `leave` | - | - | Выйти из арены в лобби |

**Response:** `CoreResponseDTO`

```json
{
  "header": {
    "current_state": "arena | combat | lobby",
    "error": "string | null"
  },
  "payload": "ArenaUIPayloadDTO | CombatDashboardDTO | null"
}
```

## 📦 Payload DTOs

### `ArenaUIPayloadDTO`
Payload для UI арены (меню, поиск).

```python
class ArenaUIPayloadDTO(BaseModel):
    screen: ArenaScreenEnum        # main_menu, mode_menu, searching, match_found
    mode: str | None = None        # 1v1, group, tournament
    title: str
    description: str
    buttons: list[ButtonDTO]
    
    # Для searching screen
    gs: int | None = None
    
    # Для match_found screen
    opponent_name: str | None = None
    is_shadow: bool = False
```

### `ArenaScreenEnum`
```python
class ArenaScreenEnum(str, Enum):
    MAIN_MENU = "main_menu"
    MODE_MENU = "mode_menu"
    SEARCHING = "searching"
    MATCH_FOUND = "match_found"
```

### `ButtonDTO`
```python
class ButtonDTO(BaseModel):
    text: str
    action: str
    mode: str | None = None
    value: str | None = None
```

## 🔄 State Transitions

| Текущий State | Action | Новый State | Условие |
| :--- | :--- | :--- | :--- |
| `arena` | `join_queue` | `arena` | Начало поиска |
| `arena` | `check_match` | `arena` | Матч не найден |
| `arena` | `check_match` | `combat` | Матч найден / Shadow создан |
| `arena` | `leave` | `lobby` | Выход |

## 📊 Response Examples

### `menu_main`
```json
{
  "header": {"current_state": "arena"},
  "payload": {
    "screen": "main_menu",
    "title": "Ангар Арены",
    "description": "Выберите тип матча или покиньте полигон.",
    "buttons": [
      {"text": "⚔️ Схватка (1x1)", "action": "menu_mode", "mode": "1v1"},
      {"text": "👥 Командные бои", "action": "menu_mode", "mode": "group"},
      {"text": "🚪 Выйти", "action": "leave"}
    ]
  }
}
```

### `join_queue`
```json
{
  "header": {"current_state": "arena"},
  "payload": {
    "screen": "searching",
    "mode": "1v1",
    "title": "Поиск противника",
    "description": "Сканирование сигнатур...",
    "gs": 150,
    "buttons": [
      {"text": "❌ Отмена", "action": "cancel_queue", "mode": "1v1"}
    ]
  }
}
```

### `check_match` (найден)
```json
{
  "header": {"current_state": "combat"},
  "payload": null
}
```

> При переходе в `combat` клиент сам запрашивает dashboard по `char_id` через Combat API.