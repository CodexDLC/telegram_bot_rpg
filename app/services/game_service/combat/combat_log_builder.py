import random

from app.resources.texts.combat_flavor import COMBAT_PHRASES


class CombatLogBuilder:
    @staticmethod
    def build_log_entry(attacker_name: str, defender_name: str, result: dict) -> str:
        visual = result.get("visual_bar", "")
        parts = [f"{visual}"]

        # 1. Тип события
        phrase_key = "hit"
        if result.get("is_dodged"):
            phrase_key = "dodge"
        elif result.get("is_parried"):
            phrase_key = "parry"
        elif result.get("is_blocked") and result.get("damage_total", 0) == 0:
            phrase_key = "block_full"
        elif result.get("is_crit"):
            phrase_key = "crit"

        # 2. Основная фраза
        templates = COMBAT_PHRASES.get(phrase_key, COMBAT_PHRASES["hit"])
        template = random.choice(templates)
        text = template.format(attacker=attacker_name, defender=defender_name, damage=result.get("damage_total", 0))
        parts.append(text)

        # 3. Доп. инфо (щит)
        if result.get("shield_dmg", 0) > 0 and result.get("hp_dmg", 0) > 0:
            parts.append(random.choice(COMBAT_PHRASES["shield_break"]).format(defender=defender_name))

        # 4. Вампиризм
        if result.get("lifesteal", 0) > 0:
            parts.append(f"💚 <b>{attacker_name}</b> восстановил {result['lifesteal']} HP.")

        # 5. 🔥 ВАЖНО: Добавляем внешние логи (например, про смерть)
        if result.get("logs"):
            parts.extend(result["logs"])

        return " ".join(parts)
