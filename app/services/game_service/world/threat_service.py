from operator import itemgetter
from typing import TypedDict

from app.resources.game_data.world_config import ANCHORS, HUB_CENTER, PORTAL_PARAMS


class _Influence(TypedDict):
    tags: list[str]
    val: float


class ThreatService:
    """
    Сервис расчета уровня угрозы на основе 'Полевой Теории'.
    """

    @staticmethod
    def calculate_threat(x: int, y: int) -> float:
        """
        Рассчитывает уровень угрозы (0.0 - 1.0) для точки.
        Формула: Sum(Anchors) - Portal.
        """
        # 1. Негативное поле (Портал)
        dist_hub = ThreatService._get_dist(x, y, HUB_CENTER["x"], HUB_CENTER["y"])
        stability = PORTAL_PARAMS["power"] / (1 + dist_hub * PORTAL_PARAMS["falloff"])

        # 2. Позитивные поля (Якоря)
        danger = 0.0
        for anchor in ANCHORS:
            dist = ThreatService._get_dist(x, y, anchor["x"], anchor["y"])
            danger += anchor["power"] / (1 + dist * anchor["falloff"])

        # 3. Итог
        total = danger - stability
        return max(0.0, min(1.0, total))

    @staticmethod
    def get_tier_from_threat(threat: float) -> int:
        """
        Конвертирует float угрозы в игровой Tier (0-7).
        Использует перекрывающиеся диапазоны (вероятностная логика может быть добавлена позже).
        """
        if threat < 0.05:
            return 0  # Safe
        if threat < 0.20:
            return 1
        if threat < 0.35:
            return 2
        if threat < 0.55:
            return 3
        if threat < 0.75:
            return 4
        if threat < 0.90:
            return 5  # Эпицентр стихии
        if threat < 0.98:
            return 6
        return 7  # Rainbow / Anomaly

    @staticmethod
    def _get_dist(x1: int, y1: int, x2: int, y2: int) -> float:
        # Дистанция Чебышёва (для квадратной сетки) подходит лучше Евклидовой
        return max(abs(x1 - x2), abs(y1 - y2))

    @staticmethod
    def get_narrative_tags(x: int, y: int) -> list[str]:
        """
        Возвращает список нарративных тегов для координаты на основе влияния Якорей.
        Смешивает теги, если в точке пересекаются влияния двух сильных источников.
        """
        active_tags: list[str] = []
        influences: list[_Influence] = []

        # 1. Считаем влияние каждого Якоря
        for anchor in ANCHORS:
            dist = ThreatService._get_dist(x, y, anchor["x"], anchor["y"])
            influence_val = anchor["power"] / (1 + dist * anchor["falloff"])
            influences.append({"tags": anchor["narrative_tags"], "val": influence_val})

        # 2. Сортируем: от самого сильного влияния к слабому
        influences.sort(key=itemgetter("val"), reverse=True)

        # 3. Логика смешивания
        primary = influences[0]
        secondary = influences[1]

        # Если доминирующий якорь влияет достаточно сильно (> 0.25)
        if primary["val"] > 0.25:
            active_tags.extend(primary["tags"])

        # Если второй якорь тоже силен (его сила > 50% от первого) — это Зона Конфликта
        if secondary["val"] > 0.25 and secondary["val"] > (primary["val"] * 0.5):
            active_tags.extend(secondary["tags"])
            active_tags.append("elemental_clash")  # Тег для LLM: "Тут битва стихий"

        return list(dict.fromkeys(active_tags))  # Убираем дубликаты, сохраняя порядок
