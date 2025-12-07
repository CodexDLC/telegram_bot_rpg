"""
Конфигурация географии мира (Якоря, Хаб, Сектора).
"""

from typing import TypedDict

WORLD_WIDTH = 105
WORLD_HEIGHT = 105
SECTOR_SIZE = 15

# Центр Хаба (D4)
HUB_CENTER: dict[str, int] = {"x": 52, "y": 52}


# Якоря Стихий (Крестовая схема)
# A4, G4, D1, D7 (Центры секторов)
class _Anchor(TypedDict):
    x: int
    y: int
    power: float
    falloff: float
    type: str


ANCHORS: list[_Anchor] = [
    {"x": 7, "y": 52, "power": 1.2, "falloff": 0.08, "type": "north_anchor"},  # A4 (North)
    {"x": 97, "y": 52, "power": 1.2, "falloff": 0.08, "type": "south_anchor"},  # G4 (South)
    {"x": 52, "y": 7, "power": 1.2, "falloff": 0.08, "type": "west_anchor"},  # D1 (West)
    {"x": 52, "y": 97, "power": 1.2, "falloff": 0.08, "type": "east_anchor"},  # D7 (East)
]

# Параметры Портала (Стабилизатор)
PORTAL_PARAMS: dict[str, float] = {"power": 2.0, "falloff": 0.04}

# Маппинг Секторов (для справки)
# Col (X): 1..7, Row (Y): A..G
SECTOR_ROWS: list[str] = ["A", "B", "C", "D", "E", "F", "G"]
