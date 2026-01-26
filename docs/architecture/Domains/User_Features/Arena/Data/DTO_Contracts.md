# 📦 Arena DTO Contracts

[⬅️ Назад: Arena Manifest](../Manifest.md)

## 🤖 AI CONTEXT
Описание структур данных (DTO), используемых для обмена между клиентом и сервером в домене Arena.

## 📍 Расположение
**Файл:** `backend/domains/user_features/arena/schemas/arena_dto.py`

## 📋 Request DTOs

### `ArenaActionDTO`
Тело запроса к API.

```python
class ArenaActionDTO(BaseModel):
    action: str
    mode: str | None = None
    value: Any | None = None
```

## 📋 Response Payload DTOs

### `ArenaUIPayloadDTO`
Основной payload для рендеринга UI.

```python
class ArenaUIPayloadDTO(BaseModel):
    screen: ArenaScreenEnum
    mode: str | None = None
    title: str
    description: str
    buttons: list[ButtonDTO]
    
    # Optional fields for specific screens
    gs: int | None = None
    opponent_name: str | None = None
    is_shadow: bool = False
```

### `ButtonDTO`
Описание кнопки.

```python
class ButtonDTO(BaseModel):
    text: str
    action: str
    mode: str | None = None
    value: str | None = None
```

## 📋 Enums

### `ArenaScreenEnum`
```python
class ArenaScreenEnum(str, Enum):
    MAIN_MENU = "main_menu"
    MODE_MENU = "mode_menu"
    SEARCHING = "searching"
    MATCH_FOUND = "match_found"
```