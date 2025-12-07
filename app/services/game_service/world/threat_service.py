from app.resources.game_data.world_config import ANCHORS, HUB_CENTER, PORTAL_PARAMS


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
