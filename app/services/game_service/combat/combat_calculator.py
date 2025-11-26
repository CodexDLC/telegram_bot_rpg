import random
from typing import Any

from app.resources.schemas_dto.modifier_dto import CombatParticipantDTO


class CombatCalculator:
    """
    Чистая математика боя (Pure Logic).
    """

    @staticmethod
    def calculate_exchange(
        attacker: CombatParticipantDTO,
        defender: CombatParticipantDTO,
        attack_zones: list[str],
        block_zones: list[str],
    ) -> dict[str, Any]:
        logs: list[str] = []
        context = {
            "logs": logs,
            "tokens_atk": {},
            "tokens_def": {},
            "is_crit": False,
            "is_blocked": False,
            "damage_raw": 0,  # Урон после ролла
            "damage_mitigated": 0,  # Урон после % резиста
            "damage_final": 0,  # Урон после плоской брони
        }

        # 1. Уворот
        if CombatCalculator._check_avoidance(attacker, defender, context):
            return CombatCalculator._pack_result(context, 0, 0)

        # 2. Блок (Геометрия)
        context["is_blocked"] = any(zone in block_zones for zone in attack_zones)

        # 3. Ролл Урона и Крита
        # (Тут теперь учитывается Anti-Crit)
        CombatCalculator._roll_damage_and_crit(attacker, defender, context)

        # 4. Митигация (Резист % -> Броня Flat)
        CombatCalculator._apply_mitigation(attacker, defender, context)

        # 5. Щит vs HP
        dmg_shield, dmg_hp = CombatCalculator._distribute_damage(defender, int(context["damage_final"]), context)

        return CombatCalculator._pack_result(context, dmg_shield, dmg_hp)

    # --- Steps ---

    @staticmethod
    def _check_avoidance(atk: CombatParticipantDTO, dfn: CombatParticipantDTO, ctx: dict) -> bool:
        # Шанс = Уворот цели - Точность атакующего (если есть)
        chance = dfn.stats.dodge_chance - atk.stats.magical_accuracy  # Или physical_accuracy, если добавим
        # Защита от отрицательного шанса
        chance = max(0.0, chance)

        if random.random() < chance:
            ctx["logs"].append("💨 <b>УВОРОТ!</b>")
            ctx["tokens_def"]["agility"] = 1
            return True
        return False

    @staticmethod
    def _roll_damage_and_crit(atk: CombatParticipantDTO, dfn: CombatParticipantDTO, ctx: dict) -> None:
        # 1. Базовый ролл
        dmg = random.randint(atk.stats.phys_damage_min, atk.stats.phys_damage_max)

        # 2. Крит (Атака - АнтиКрит)
        crit_chance = atk.stats.physical_crit_chance - dfn.stats.anti_physical_crit_chance
        crit_chance = max(0.0, crit_chance)

        if random.random() < crit_chance:
            ctx["is_crit"] = True
            dmg = int(dmg * atk.stats.physical_crit_power_float)
            ctx["tokens_atk"]["rage"] = 1

            if ctx["is_blocked"]:
                ctx["logs"].append("💥 <b>КРИТ ПРОБИВ!</b> (Блок пробит)")
                # Крит в блок режет урон (например на 30%)
                dmg = int(dmg * 0.7)
            else:
                ctx["logs"].append("💥 <b>КРИТИЧЕСКИЙ УДАР!</b>")
        else:
            if ctx["is_blocked"]:
                dmg = 0
                ctx["logs"].append("🛡 <b>БЛОК!</b>")
                ctx["tokens_def"]["tactics"] = 1
            else:
                ctx["logs"].append("🗡 Попадание.")

        ctx["damage_raw"] = dmg

    @staticmethod
    def _apply_mitigation(atk: CombatParticipantDTO, dfn: CombatParticipantDTO, ctx: dict) -> None:
        dmg = ctx["damage_raw"]
        if dmg <= 0:
            ctx["damage_final"] = 0
            return

        # 1. Процентный Резист (Resistance - Penetration)
        # physical_resistance в DTO должен быть float (например, 0.20 для 20%)
        res_percent = dfn.stats.physical_resistance - atk.stats.physical_penetration
        res_percent = max(0.0, min(0.85, res_percent))  # Кап резиста 85%

        dmg_after_res = int(dmg * (1.0 - res_percent))

        # 2. Плоская Броня (Flat Armor)
        # armor в DTO - это int (например, 10 ед.)
        flat_armor = dfn.stats.inventory_slots_bonus  # ВРЕМЕННО используем это поле или добавим 'armor' в DTO
        # Лучше добавь поле `armor: int` в CombatStatsDTO!

        # Если был Блок Щитом (не оружием), добавляем Броню Щита
        # if ctx['is_blocked_by_shield']: flat_armor += shield_armor

        final_dmg = max(1, dmg_after_res - flat_armor)  # Минимум 1 урона, если пробил уворот

        ctx["damage_final"] = final_dmg

        # Логирование (опционально, если резист сильный)
        # if res_percent > 0.3: ctx["logs"].append(f"🛡 Резист поглотил часть урона.")

    @staticmethod
    def _distribute_damage(dfn: CombatParticipantDTO, damage: int, ctx: dict) -> tuple[int, int]:
        if damage <= 0:
            return 0, 0

        current_shield = dfn.state.energy_current

        if current_shield >= damage:
            ctx["logs"].append(f"🛡 Энерго-щит: -{damage}")
            return damage, 0
        else:
            shield_dmg = current_shield
            hp_dmg = damage - current_shield
            ctx["logs"].append("💔 <b>ЩИТ СНЯТ!</b>")
            ctx["logs"].append(f"🩸 Ранение: <b>-{hp_dmg} HP</b>")
            return shield_dmg, hp_dmg

    @staticmethod
    def _pack_result(ctx: dict, shield_dmg: int, hp_dmg: int) -> dict:
        return {
            "damage_total": ctx["damage_final"],
            "shield_dmg": shield_dmg,
            "hp_dmg": hp_dmg,
            "tokens_attacker": ctx["tokens_atk"],
            "tokens_defender": ctx["tokens_def"],
            "logs": ctx["logs"],
        }
