from enum import Enum
from typing import Any

from pydantic import BaseModel

# --- Request Models (API) ---


class MoveRequest(BaseModel):
    char_id: int
    direction: str


class InteractRequest(BaseModel):
    char_id: int
    action: str
    target_id: str | None = None


class UseServiceRequest(BaseModel):
    char_id: int
    service_id: str


# --- Navigation Grid DTOs ---


class GridButtonDTO(BaseModel):
    """
    Кнопка навигационной сетки.
    """

    id: str  # Уникальный ID кнопки (например, "n", "search")
    label: str  # Текст на кнопке ("⬆️ Север", "🔍 Поиск")
    action: str  # API Action ("move:n", "interact:search")
    is_active: bool  # Доступна ли кнопка
    style: str = "primary"  # Стиль кнопки (primary, secondary, danger)


class NavigationGridDTO(BaseModel):
    """
    Раскладка клавиатуры навигации (3x3 + Services).
    """

    # Крестовина (Move)
    n: GridButtonDTO | None = None
    s: GridButtonDTO | None = None
    w: GridButtonDTO | None = None
    e: GridButtonDTO | None = None

    # Углы (Context)
    nw: GridButtonDTO | None = None
    ne: GridButtonDTO | None = None
    sw: GridButtonDTO | None = None
    se: GridButtonDTO | None = None

    # Центр
    center: GridButtonDTO | None = None

    # Нижний ряд (Services)
    services: list[GridButtonDTO] = []


# --- HUD DTOs ---


class HudType(str, Enum):
    EXPLORATION = "exploration"
    ALERT = "alert"


class BaseHudDTO(BaseModel):
    type: HudType


class ExplorationHudDTO(BaseHudDTO):
    type: HudType = HudType.EXPLORATION
    threat_tier: int
    players_count: int
    battles_count: int
    is_safe_zone: bool


class AlertHudDTO(BaseHudDTO):
    type: HudType = HudType.ALERT
    message: str
    style: str = "warning"  # warning, info, error


# --- World DTO ---


class WorldNavigationDTO(BaseModel):
    """
    Полные данные для отрисовки экрана навигации (Карта).
    """

    # Core Info
    loc_id: str
    title: str
    description: str

    # Context
    visual_objects: list[str] = []  # Объекты в тексте
    players_nearby: int = 0  # Legacy

    # UI Components
    grid: NavigationGridDTO
    hud: ExplorationHudDTO | AlertHudDTO | None = None

    # UI Flags (Legacy)
    threat_tier: int = 0
    is_safe_zone: bool = False

    # Legacy Support
    metadata: dict[str, Any] = {}


# --- List DTO ---


class ListItemDTO(BaseModel):
    id: str
    text: str
    action: str  # Callback data при клике


class ExplorationListDTO(BaseModel):
    """
    DTO для отображения списков (Бои, Люди, Квесты).
    """

    title: str
    items: list[ListItemDTO]
    page: int
    total_pages: int
    back_action: str = "look_around"  # Куда ведет кнопка Назад


# --- Encounter DTOs ---


class EncounterType(str, Enum):
    COMBAT = "COMBAT"
    NARRATIVE = "NARRATIVE"
    MERCHANT = "MERCHANT"
    QUEST = "QUEST"


class DetectionStatus(str, Enum):
    AMBUSH = "AMBUSH"
    DETECTED = "DETECTED"


class EnemyPreviewDTO(BaseModel):
    """
    Превью врага в энкаунтере (зависит от Bestiary).
    """

    name: str | None = None  # "Волк" или "???"
    level: int | None = None
    hp_percent: int | None = None  # Примерное HP
    image: str | None = None


class EncounterOptionDTO(BaseModel):
    """
    Вариант действия в энкаунтере.
    """

    id: str  # ID действия ("attack", "flee")
    label: str  # Текст кнопки ("⚔️ Атаковать")
    style: str = "primary"  # Стиль кнопки


class EncounterDTO(BaseModel):
    """
    Данные события (Энкаунтера).
    """

    id: str
    type: EncounterType
    status: DetectionStatus | None = None  # DETECTED / AMBUSH

    title: str
    description: str
    image: str | None = None

    # Content
    enemies: list[EnemyPreviewDTO] = []
    info_level: int = 0  # Уровень знаний (Bestiary)

    options: list[EncounterOptionDTO]

    # Technical Data
    session_id: str | None = None  # ID боевой сессии (если бой)
    metadata: dict[str, Any] = {}
