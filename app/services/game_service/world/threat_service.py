from operator import itemgetter
from typing import TypedDict

from app.resources.game_data.world_config import (
    ANCHORS,
    HUB_CENTER,
    HYBRID_TAGS,  # <--- Добавили импорт
    INFLUENCE_TAGS,
    PORTAL_PARAMS,
)


class _Influence(TypedDict):
    tags: list[str]
    val: float
    type: str  # 'north_prime', 'south_prime' и т.д.


class ThreatService:
    """
    Сервис расчета уровня угрозы на основе 'Полевой Теории'.
    """

    # Маппинг: Тип Якоря -> Тип Стихии (для поиска в конфигах)
    TYPE_MAP = {
        "north_prime": "ice",
        "south_prime": "fire",
        "west_prime": "gravity",
        "east_prime": "bio",
    }

    @staticmethod
    def calculate_threat(x: int, y: int) -> float:
        """
        Рассчитывает уровень угрозы (0.0 - 1.0) для точки.
        """
        dist_hub = ThreatService._get_dist(x, y, HUB_CENTER["x"], HUB_CENTER["y"])
        stability = PORTAL_PARAMS["power"] / (1 + dist_hub * PORTAL_PARAMS["falloff"])

        danger = 0.0
        for anchor in ANCHORS:
            dist = ThreatService._get_dist(x, y, anchor["x"], anchor["y"])
            danger += anchor["power"] / (1 + dist * anchor["falloff"])

        total = danger - stability
        return max(0.0, min(1.0, total))

    @staticmethod
    def get_tier_from_threat(threat: float) -> int:
        if threat < 0.05:
            return 0
        if threat < 0.20:
            return 1
        if threat < 0.35:
            return 2
        if threat < 0.55:
            return 3
        if threat < 0.75:
            return 4
        if threat < 0.90:
            return 5
        if threat < 0.98:
            return 6
        return 7

    @staticmethod
    def get_narrative_tags(x: int, y: int) -> list[str]:
        """
        Возвращает список тегов. Учитывает:
        1. Подавление Порталом (Gatekeeper).
        2. Градиенты силы (Tier-based tags).
        3. Гибридные реакции (Hybrid Tags).
        """
        threat_val = ThreatService.calculate_threat(x, y)
        current_tier = ThreatService.get_tier_from_threat(threat_val)

        # 1. Gatekeeper: Если зона безопасна, стихии не активны
        if threat_val < 0.15:
            return []

        active_tags: list[str] = []
        influences: list[_Influence] = []

        for anchor in ANCHORS:
            dist = ThreatService._get_dist(x, y, anchor["x"], anchor["y"])
            influence_val = anchor["power"] / (1 + dist * anchor["falloff"])
            influences.append(
                {
                    "tags": anchor["narrative_tags"],
                    "val": influence_val,
                    "type": anchor.get("type", "unknown"),
                }
            )

        influences.sort(key=itemgetter("val"), reverse=True)
        primary = influences[0]
        secondary = influences[1]

        # 2. Основная стихия (через Градиент)
        if primary["val"] > 0.15:
            grad_tags = ThreatService._get_gradient_tags(primary["type"], current_tier)
            if grad_tags:
                active_tags.extend(grad_tags)
            else:
                active_tags.extend(primary["tags"])

        # 3. Смешивание и Реакции
        # Если вторая стихия достаточно сильна (> 70% от первой)
        if secondary["val"] > 0.15 and secondary["val"] > (primary["val"] * 0.7):
            sec_tier = max(1, current_tier - 1)

            # А. Добавляем "фоновые" теги второй стихии
            grad_tags_sec = ThreatService._get_gradient_tags(secondary["type"], sec_tier)
            if grad_tags_sec:
                active_tags.extend(grad_tags_sec)
            else:
                active_tags.extend(secondary["tags"])

            # Б. Ищем УНИКАЛЬНУЮ ГИБРИДНУЮ РЕАКЦИЮ
            # Превращаем типы якорей (north_prime) в стихии (ice)
            key1 = ThreatService.TYPE_MAP.get(primary["type"])
            key2 = ThreatService.TYPE_MAP.get(secondary["type"])

            if key1 and key2:
                # Ищем пару во frozenset ключах словаря HYBRID_TAGS
                combo_key = frozenset([key1, key2])
                hybrid_reaction = HYBRID_TAGS.get(combo_key)

                if hybrid_reaction:
                    # Ура! Нашли уникальное описание (напр. "frozen_lightning")
                    active_tags.extend(hybrid_reaction)
                else:
                    # Если уникальной реакции нет, ставим дефолт
                    active_tags.append("elemental_clash")

        return list(dict.fromkeys(active_tags))

    @staticmethod
    def _get_gradient_tags(anchor_type: str, tier: int) -> list[str] | None:
        gradient_key = ThreatService.TYPE_MAP.get(anchor_type)
        if not gradient_key or gradient_key not in INFLUENCE_TAGS:
            return None

        tier_map = INFLUENCE_TAGS[gradient_key]
        for (min_t, max_t), tags in tier_map.items():
            if min_t <= tier <= max_t:
                return tags
        return None

    @staticmethod
    def _get_dist(x1: int, y1: int, x2: int, y2: int) -> float:
        return max(abs(x1 - x2), abs(y1 - y2))
