import random
from typing import Any


class AiProcessor:
    """
    Процессор принятия решений для AI (NPC).
    Отвечает за выбор зон атаки/блока и способностей.
    """

    def __init__(self):
        self.all_zones = ["head", "chest", "belly", "legs", "feet"]
        self.valid_block_pairs = [
            ["head", "chest"],
            ["chest", "belly"],
            ["belly", "legs"],
            ["legs", "feet"],
            ["feet", "head"],
        ]

    def decide_exchange(self, target_id: int) -> dict[str, Any]:
        """
        Генерирует payload для базовой атаки (Exchange).
        """
        # 1. Выбор зоны атаки (1 зона)
        attack_zones = [random.choice(self.all_zones)]

        # 2. Выбор зон блока (2 зоны, соседние)
        block_zones = random.choice(self.valid_block_pairs)

        return {
            "action": "attack",
            "target_id": target_id,
            "attack_zones": attack_zones,
            "block_zones": block_zones,
            # "skill_id": None # Пока без скиллов
        }
