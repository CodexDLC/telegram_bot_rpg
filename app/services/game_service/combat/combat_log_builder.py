# app/services/game_service/combat/combat_log_builder.py
import random
from typing import Any

from app.resources.texts.combat_flavor import COMBAT_PHRASES


class CombatLogBuilder:
    """
    Собирает человеко-читаемую строку лога для фронтенда на основе результата удара.
    """

    @staticmethod
    def _get_phrase_key(result: dict[str, Any]) -> str:
        """Определяет ключ основной фразы на основе результата боя."""
        if result.get("is_dodged"):
            return "dodge"
        if result.get("is_parried"):
            return "parry"
        if result.get("is_crit"):
            return "crit"
        if result.get("is_blocked") and result.get("damage_total", 0) == 0:
            return "block_full"
        return "hit"

    @staticmethod
    def build_log_entry(
        attacker_name: str,
        defender_name: str,
        result: dict,
        defender_hp: int,
        defender_energy: int,
    ) -> str:
        """
        Строит одну строку лога для конкретного удара.
        """
        visual = result.get("visual_bar", "")
        parts = [f"{visual}"]

        # 1. Тип события (Hit, Crit, Block, Dodge...)
        phrase_key = "hit"
        if result.get("is_dodged"):
            phrase_key = "dodge"
        elif result.get("is_parried"):
            phrase_key = "parry"
        elif result.get("is_blocked") and result.get("damage_total", 0) == 0:
            # Полный блок (урон 0)
            phrase_key = "block_full"
        elif result.get("is_crit"):
            phrase_key = "crit"

        # 2. Выбираем фразу и форматируем
        templates = COMBAT_PHRASES.get(phrase_key, COMBAT_PHRASES["hit"])
        template = random.choice(templates)

        text = template.format(attacker=attacker_name, defender=defender_name, damage=result.get("damage_total", 0))

        if not result.get("is_dodged"):
            text += f" <b>({defender_hp} HP | {defender_energy} EN)</b>"

        parts.append(text)

        # 3. Доп. инфо (щит пробит)
        if result.get("shield_dmg", 0) > 0 and result.get("hp_dmg", 0) > 0:
            parts.append(random.choice(COMBAT_PHRASES["shield_break"]).format(defender=defender_name))

        # 4. Вампиризм
        if result.get("lifesteal", 0) > 0:
            parts.append(f"💚 <b>{attacker_name}</b> восстановил {result['lifesteal']} HP.")

        # 5. Внешние логи (от абилок, ядов и т.д.)
        if result.get("logs"):
            parts.extend(result["logs"])

        return " ".join(parts)
