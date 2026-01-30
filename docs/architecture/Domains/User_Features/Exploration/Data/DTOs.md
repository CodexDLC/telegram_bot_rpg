# 📦 Exploration Data Objects

## Navigation Grid (Клавиатура)
Описывает состояние кнопок навигации (3x3 + низ).

```python
class GridButtonDTO(BaseModel):
    id: str             # "n", "s", "search", "menu"
    label: str          # "⬆️ Север", "🔍 Поиск"
    action: str         # "move:n", "svc:search"
    is_active: bool     # True (можно нажать) / False (серое/стоп)
    style: str          # "primary", "secondary", "danger"

class NavigationGridDTO(BaseModel):
    # Крестовина (Move)
    n: GridButtonDTO    # Север
    s: GridButtonDTO    # Юг
    w: GridButtonDTO    # Запад
    e: GridButtonDTO    # Восток
    
    # Углы (Context/Services)
    nw: GridButtonDTO   # (Top-Left) e.g., "Search"
    ne: GridButtonDTO   # (Top-Right) e.g., "Map/Mode"
    sw: GridButtonDTO   # (Bottom-Left) e.g., "Social"
    se: GridButtonDTO   # (Bottom-Right) e.g., "Auto"
    
    # Нижний ряд (Services & Interactions)
    services: list[GridButtonDTO] 
```

## WorldNavigationDTO
Данные для отрисовки экрана "Карта".

```python
class WorldNavigationDTO(BaseModel):
    # Core Info
    loc_id: str
    title: str
    description: str
    
    # Context
    visual_objects: list[str]   # ["Сундук", "Труп"]
    players_nearby: int
    
    # UI Components
    grid: NavigationGridDTO     # Готовая раскладка кнопок
    
    # UI Flags
    threat_tier: int            # 0-5
    is_safe_zone: bool
```

## Encounter Response
Используется, когда движение прервано событием.

```python
class EncounterOptionDTO(BaseModel):
    id: str             # "attack", "flee"
    label: str          # "Атаковать"
    style: str          # "danger", "primary", "secondary"

class EncounterDTO(BaseModel):
    id: str
    type: str           # "combat", "narrative"
    
    title: str
    description: str
    image: str | None
    
    options: list[EncounterOptionDTO]
    
    # Technical
    session_id: str | None # Если начался бой
```
