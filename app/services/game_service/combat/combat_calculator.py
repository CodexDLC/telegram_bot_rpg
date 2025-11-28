# app/services/game_service/combat/combat_calculator.py
import random
from typing import Any


class CombatCalculator:
    """
    Чистая математика боя (Pure Logic).
    """

    CAP_PHYS_CRIT = 0.75
    CAP_MAGIC_CRIT = 0.50
    CAP_DODGE = 0.75

    @staticmethod
    def calculate_hit(
        stats_atk: dict[str, float],
        stats_def: dict[str, float],
        current_shield: int,
        attack_zones: list[str],
        block_zones: list[str],
        damage_type: str = "phys",
    ) -> dict[str, Any]:
        ctx: dict[str, Any] = {
            "logs": [],
            "is_crit": False,
            "is_blocked": False,
            "block_type": None,
            "is_dodged": False,
            "is_parried": False,
            "is_counter": False,
            "damage_raw": 0,
            "damage_final": 0,
            "lifesteal_amount": 0,
            "tokens_gained_atk": {},
            "tokens_gained_def": {},
        }

        if CombatCalculator._step_parry(stats_def, damage_type, ctx):
            ctx["tokens_gained_def"]["parry"] = 1
            return CombatCalculator._finalize_log(ctx, 0, 0, attack_zones, block_zones)

        if CombatCalculator._step_dodge(stats_atk, stats_def, damage_type, ctx):
            if ctx["is_counter"]:
                ctx["tokens_gained_def"]["counter"] = 1
            return CombatCalculator._finalize_log(ctx, 0, 0, attack_zones, block_zones)

        CombatCalculator._step_block(stats_def, attack_zones, block_zones, ctx)
        CombatCalculator._step_roll_damage(stats_atk, stats_def, damage_type, ctx)
        CombatCalculator._step_mitigation(stats_atk, stats_def, damage_type, ctx)
        CombatCalculator._step_vampirism(stats_atk, ctx)

        if ctx["is_blocked"]:
            ctx["tokens_gained_def"]["block"] = 1
        elif ctx["damage_final"] > 0 and not ctx["is_dodged"] and not ctx["is_parried"]:
            ctx["tokens_gained_atk"]["hit"] = 1

        if ctx["is_crit"]:
            ctx["tokens_gained_atk"]["crit"] = 1

        dmg_shield, dmg_hp = CombatCalculator._distribute_damage(current_shield, ctx["damage_final"])

        return CombatCalculator._finalize_log(ctx, dmg_shield, dmg_hp, attack_zones, block_zones)

    @staticmethod
    def _finalize_log(ctx: dict, shield_dmg: int, hp_dmg: int, attack_zones: list, block_zones: list) -> dict:
        visual_bar = CombatCalculator._generate_visual_bar(attack_zones, block_zones, ctx)
        ctx["visual_bar"] = visual_bar
        ctx["logs"] = []
        return CombatCalculator._pack_result(ctx, shield_dmg, hp_dmg)

    @staticmethod
    def _generate_visual_bar(attack_zones: list, block_zones: list, ctx: dict) -> str:
        zones_order = ["head", "chest", "legs", "feet"]
        symbols = []
        if ctx["is_dodged"] or ctx["is_parried"]:
            return ""
        for zone in zones_order:
            is_attacked = zone in (attack_zones or [])
            is_blocked = zone in (block_zones or [])
            if is_attacked and is_blocked:
                symbols.append("🛡")
            elif is_attacked:
                symbols.append("🟥")
            elif is_blocked:
                symbols.append("🟦")
            else:
                symbols.append("▫️")
        return f"[{''.join(symbols)}]"

    @staticmethod
    def _step_parry(stats_def: dict, damage_type: str, ctx: dict) -> bool:
        if damage_type == "phys" and CombatCalculator._check_chance(stats_def.get("parry_chance", 0.0)):
            ctx["is_parried"] = True
            return True
        return False

    @staticmethod
    def _step_dodge(stats_atk: dict, stats_def: dict, damage_type: str, ctx: dict) -> bool:
        if damage_type == "phys":
            dodge_chance = max(
                0.0,
                min(
                    CombatCalculator.CAP_DODGE,
                    stats_def.get("dodge_chance", 0.0) - stats_atk.get("anti_dodge", 0.0),
                ),
            )
            if CombatCalculator._check_chance(dodge_chance):
                ctx["is_dodged"] = True
                if CombatCalculator._check_chance(stats_def.get("counter_attack_chance", 0.0)):
                    ctx["is_counter"] = True
                return True
        return False

    @staticmethod
    def _step_block(stats_def: dict, attack_zones: list, block_zones: list, ctx: dict) -> None:
        atk_set = set(attack_zones) if attack_zones else set()
        blk_set = set(block_zones) if block_zones else set()
        if atk_set.intersection(blk_set):
            ctx["is_blocked"] = True
            ctx["block_type"] = "geo"
            return
        if CombatCalculator._check_chance(stats_def.get("shield_block_chance", 0.0)):
            ctx["is_blocked"] = True
            ctx["block_type"] = "passive"

    @staticmethod
    def _step_roll_damage(stats_atk: dict, stats_def: dict, damage_type: str, ctx: dict) -> None:
        prefix = "magical" if damage_type == "magic" else "physical"
        dmg_prefix = "magic" if damage_type == "magic" else "phys"
        d_min = int(stats_atk.get(f"{dmg_prefix}_damage_min", 1))
        d_max = int(stats_atk.get(f"{dmg_prefix}_damage_max", 2))
        dmg = random.randint(d_min, max(d_min, d_max))
        crit_chance = max(
            0.0,
            min(
                CombatCalculator.CAP_PHYS_CRIT,
                stats_atk.get(f"{prefix}_crit_chance", 0.0) - stats_def.get(f"anti_{prefix}_crit_chance", 0.0),
            ),
        )
        if CombatCalculator._check_chance(crit_chance):
            ctx["is_crit"] = True
            if not ctx["is_blocked"]:
                dmg = int(dmg * stats_atk.get(f"{prefix}_crit_power_float", 1.5))
        if ctx["is_blocked"]:
            dmg = int(dmg * (1.0 - min(1.0, stats_def.get("shield_block_power", 0.5))))
        ctx["damage_raw"] = dmg

    @staticmethod
    def _step_mitigation(stats_atk: dict, stats_def: dict, damage_type: str, ctx: dict) -> None:
        dmg = ctx["damage_raw"]
        if dmg <= 0:
            ctx["damage_final"] = 0
            return
        res_stat = "magical_resistance" if damage_type == "magic" else "physical_resistance"
        pen_stat = "magical_penetration" if damage_type == "magic" else "physical_penetration"
        net_resist = min(0.85, stats_def.get(res_stat, 0.0) - stats_atk.get(pen_stat, 0.0))
        dmg = int(dmg * (1.0 - net_resist))
        dmg = max(1, dmg - int(stats_def.get("damage_reduction_flat", 0)))
        ctx["damage_final"] = dmg

    @staticmethod
    def _step_vampirism(stats_atk: dict, ctx: dict) -> None:
        if (
            ctx["damage_final"] > 0
            and stats_atk.get("vampiric_power", 0.0) > 0
            and CombatCalculator._check_chance(stats_atk.get("vampiric_trigger_chance", 0.8))
        ):
            ctx["lifesteal_amount"] = int(ctx["damage_final"] * stats_atk.get("vampiric_power"))

    @staticmethod
    def _distribute_damage(current_shield: int, damage: int) -> tuple[int, int]:
        if damage <= 0:
            return 0, 0
        if current_shield >= damage:
            return damage, 0
        return current_shield, damage - current_shield

    @staticmethod
    def _check_chance(chance: float) -> bool:
        return chance >= 1.0 or (chance > 0 and random.random() < chance)

    @staticmethod
    def _pack_result(ctx: dict, shield_dmg: int, hp_dmg: int) -> dict:
        return {
            "damage_total": ctx["damage_final"],
            "shield_dmg": shield_dmg,
            "hp_dmg": hp_dmg,
            "is_crit": ctx["is_crit"],
            "is_blocked": ctx["is_blocked"],
            "is_dodged": ctx.get("is_dodged", False),
            "is_parried": ctx.get("is_parried", False),
            "is_counter": ctx.get("is_counter", False),
            "lifesteal": ctx["lifesteal_amount"],
            "visual_bar": ctx.get("visual_bar", ""),
            "tokens_atk": ctx.get("tokens_gained_atk", 0),
            "tokens_def": ctx.get("tokens_gained_def", 0),
        }
