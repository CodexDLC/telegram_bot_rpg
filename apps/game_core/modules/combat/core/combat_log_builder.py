# apps/game_core/modules/combat/core/combat_log_builder.py
import random
from typing import Any

from apps.game_core.resources.game_data.combat_flavor import COMBAT_PHRASES


class CombatLogBuilder:
    """
    Сервис для формирования человеко-читаемых записей лога боя.

    На основе результатов удара генерирует текстовые сообщения для фронтенда,
    включая визуальные индикаторы, фразы и дополнительную информацию.
    """

    @staticmethod
    def _get_phrase_key(result: dict[str, Any]) -> str:
        """
        Определяет ключ для выбора основной фразы лога на основе результата удара.

        Args:
            result: Словарь с результатами расчета удара.

        Returns:
            Строка-ключ для словаря `COMBAT_PHRASES`.
        """
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
        result: dict[str, Any],
        defender_hp: int,
        defender_energy: int,
    ) -> str:
        """
        Строит одну человеко-читаемую запись лога для конкретного удара.

        Args:
            attacker_name: Имя атакующего актора.
            defender_name: Имя защищающегося актора.
            result: Словарь с результатами расчета удара.
            defender_hp: Текущее HP защищающегося актора после удара.
            defender_energy: Текущая Energy защищающегося актора после удара.

        Returns:
            Форматированная строка лога боя.
        """
        visual = result.get("visual_bar", "")
        parts = [f"{visual}"]

        phrase_key = CombatLogBuilder._get_phrase_key(result)
        templates = COMBAT_PHRASES.get(phrase_key, COMBAT_PHRASES["hit"])
        template = random.choice(templates)

        text = template.format(attacker=attacker_name, defender=defender_name, damage=result.get("damage_total", 0))

        if not result.get("is_dodged"):
            text += f" <b>({defender_hp} HP | {defender_energy} EN)</b>"

        parts.append(text)

        if result.get("shield_dmg", 0) > 0 and result.get("hp_dmg", 0) > 0:
            parts.append(random.choice(COMBAT_PHRASES["shield_break"]).format(defender=defender_name))

        if result.get("lifesteal", 0) > 0:
            parts.append(f"💚 <b>{attacker_name}</b> восстановил {result['lifesteal']} HP.")

        if result.get("logs"):
            parts.extend(result["logs"])

        return " ".join(parts)
