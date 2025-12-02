# app/services/game_service/combat/combat_calculator.py
import random
from typing import Any

from loguru import logger as log


class CombatCalculator:
    """
    Чистая математика боя (Pure Logic).
    """

    @staticmethod
    def calculate_hit(
        stats_atk: dict[str, float],
        stats_def: dict[str, float],
        current_shield: int,
        attack_zones: list[str],
        block_zones: list[str],
        damage_type: str = "physical",
        flags: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Рассчитывает результат одного удара.

        Args:
            stats_atk: Агрегированные статы атакующего.
            stats_def: Агрегированные статы защищающегося.
            current_shield: Текущее значение щита цели.
            attack_zones: Зоны атаки.
            block_zones: Зоны блока.
            damage_type: Тип урона.
            flags: Словарь правил из активного скилла.

        Returns:
            Словарь с результатом удара.
        """
        if flags is None:
            flags = {}
        if "override_damage_type" in flags:
            damage_type = flags["override_damage_type"]

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
        log.trace(f"CalculateHitStart | damage_type={damage_type} flags={flags}")

        # 1. PARRY
        can_parry = damage_type == "physical"
        if not flags.get("ignore_parry") and can_parry:
            parry_chance = min(stats_def.get("parry_chance", 0.0), stats_def.get("parry_cap", 0.5))
            if CombatCalculator._check_chance(parry_chance):
                ctx["is_parried"] = True
                ctx["tokens_gained_def"]["parry"] = 1
                log.debug(f"HitResult | result=parry chance={parry_chance}")
                return CombatCalculator._finalize_log(ctx, 0, 0, attack_zones, block_zones)

        # 2. DODGE
        if not flags.get("ignore_dodge"):
            dodge_val = stats_def.get("dodge_chance", 0.0)
            anti_dodge = stats_atk.get("anti_dodge_chance", 0.0)
            final_dodge = max(0.0, min(stats_def.get("dodge_cap", 0.75), dodge_val - anti_dodge))
            if CombatCalculator._check_chance(final_dodge):
                ctx["is_dodged"] = True
                if CombatCalculator._check_chance(stats_def.get("counter_attack_chance", 0.0)):
                    ctx["is_counter"] = True
                    ctx["tokens_gained_def"]["counter"] = 1
                    log.debug("HitResult | sub_event=counter_attack")
                log.debug(f"HitResult | result=dodge chance={final_dodge}")
                return CombatCalculator._finalize_log(ctx, 0, 0, attack_zones, block_zones)

        # 3. BLOCK CHECK
        if not flags.get("ignore_block"):
            CombatCalculator._step_block(stats_def, attack_zones, block_zones, ctx)

        # 4. DAMAGE ROLL
        CombatCalculator._step_roll_damage(stats_atk, stats_def, damage_type, ctx, flags)

        # 5. MITIGATION & FINAL CALC
        if ctx["is_blocked"] and ctx["block_type"] == "geo":
            if ctx["is_crit"]:
                CombatCalculator._step_mitigation(stats_atk, stats_def, damage_type, ctx)
                ctx["damage_final"] = int(ctx["damage_final"] * 0.5)
                log.trace(f"GeoBlockCrit | damage_final={ctx['damage_final']}")
            else:
                ctx["damage_final"] = 0
                log.trace("GeoBlockNormal | damage_final=0")
        else:
            CombatCalculator._step_mitigation(stats_atk, stats_def, damage_type, ctx)

        # 6. Vampirism
        CombatCalculator._step_vampirism(stats_atk, ctx)

        # Tokens
        if ctx["is_blocked"]:
            ctx["tokens_gained_def"]["block"] = 1
        elif ctx["damage_final"] > 0:
            ctx["tokens_gained_atk"]["hit"] = 1
        if ctx["is_crit"]:
            ctx["tokens_gained_atk"]["crit"] = 1

        dmg_shield, dmg_hp = CombatCalculator._distribute_damage(current_shield, ctx["damage_final"])
        log.debug(f"DamageDistribution | total={ctx['damage_final']} shield_dmg={dmg_shield} hp_dmg={dmg_hp}")
        return CombatCalculator._finalize_log(ctx, dmg_shield, dmg_hp, attack_zones, block_zones)

    # --------------------------------------------------------------------------
    # ВНУТРЕННИЕ ШАГИ
    # --------------------------------------------------------------------------

    @staticmethod
    def _step_block(stats_def: dict, attack_zones: list, block_zones: list, ctx: dict) -> None:
        atk_set = set(attack_zones or [])
        blk_set = set(block_zones or [])
        if atk_set.intersection(blk_set):
            ctx["is_blocked"], ctx["block_type"] = True, "geo"
            log.trace("BlockStep | result=success type=geo")
            return

        block_chance = min(stats_def.get("shield_block_chance", 0.0), stats_def.get("shield_block_cap", 0.75))
        if CombatCalculator._check_chance(block_chance):
            ctx["is_blocked"], ctx["block_type"] = True, "passive"
            log.trace(f"BlockStep | result=success type=passive chance={block_chance}")

    @staticmethod
    def _step_roll_damage(stats_atk: dict, stats_def: dict, damage_type: str, ctx: dict, flags: dict) -> None:
        cat_prefix = "physical" if damage_type == "physical" else "magical"
        d_min, d_max = 0, 0

        if damage_type == "physical":
            d_min, d_max = int(stats_atk.get("physical_damage_min", 1)), int(stats_atk.get("physical_damage_max", 2))
        else:
            power = stats_atk.get("magical_damage_power", 0.0)
            if power > 0:
                d_min, d_max = int(power * 0.9), int(power * 1.1)
            else:
                d_min, d_max = int(stats_atk.get("magical_damage_min", 0)), int(stats_atk.get("magical_damage_max", 0))

        if d_max == 0 and damage_type == "physical":
            d_min, d_max = 1, 2
        if d_max == 0:
            ctx["damage_raw"] = 0
            return

        dmg = random.randint(d_min, max(d_min, d_max))
        log.trace(f"RollDamageBase | min={d_min} max={d_max} rolled={dmg}")

        spec_bonus = stats_atk.get(f"{damage_type}_damage_bonus", 0.0)
        gen_bonus = (
            stats_atk.get(f"{cat_prefix}_damage_bonus", 0.0) if damage_type not in ("physical", "magical") else 0.0
        )
        dmg = int(dmg * (1.0 + spec_bonus + gen_bonus))
        log.trace(f"RollDamageBonus | bonus_pct={spec_bonus + gen_bonus} after_bonus={dmg}")

        skill_mult = flags.get("damage_mult", 1.0)
        dmg = int(dmg * skill_mult)
        log.trace(f"RollDamageSkillMult | mult={skill_mult} after_mult={dmg}")

        crit_val = stats_atk.get(f"{damage_type}_crit_chance", 0.0) or stats_atk.get(f"{cat_prefix}_crit_chance", 0.0)
        skill_crit = flags.get("bonus_crit", 0.0)
        anti_crit = stats_def.get(f"anti_{cat_prefix}_crit_chance", 0.0) + stats_def.get("anti_crit_chance", 0.0)
        crit_cap = stats_atk.get(f"{cat_prefix}_crit_cap", 0.75)
        final_crit = max(0.0, min(crit_cap, (crit_val + skill_crit) - anti_crit))

        if CombatCalculator._check_chance(final_crit):
            ctx["is_crit"] = True
            crit_power = stats_atk.get(f"{cat_prefix}_crit_power_float", 1.5)
            dmg = int(dmg * crit_power)
            log.trace(f"RollDamageCrit | power={crit_power} after_crit={dmg}")

        if ctx["is_blocked"] and ctx["block_type"] == "passive":
            block_power = min(1.0, stats_def.get("shield_block_power", 0.5))
            dmg = int(dmg * (1.0 - block_power))
            log.trace(f"RollDamagePassiveBlock | power={block_power} after_block={dmg}")

        ctx["damage_raw"] = dmg

    @staticmethod
    def _step_mitigation(stats_atk: dict, stats_def: dict, damage_type: str, ctx: dict) -> None:
        dmg = ctx["damage_raw"]
        if dmg <= 0:
            ctx["damage_final"] = 0
            return

        cat_prefix = "physical" if damage_type == "physical" else "magical"
        res_key, pen_key = f"{damage_type}_resistance", f"{damage_type}_penetration"
        resistance = stats_def.get(res_key, 0.0) or (
            stats_def.get(f"{cat_prefix}_resistance", 0.0) if damage_type not in ("physical", "magical") else 0.0
        )
        penetration = stats_atk.get(pen_key, 0.0) or (
            stats_atk.get(f"{cat_prefix}_penetration", 0.0) if damage_type not in ("physical", "magical") else 0.0
        )
        res_cap = stats_def.get("resistance_cap", 0.85)
        net_resist = max(0.0, min(res_cap, resistance - penetration))
        dmg = int(dmg * (1.0 - net_resist))
        log.trace(f"MitigationResistance | net_resist={net_resist} after_resist={dmg}")

        flat_red = int(stats_def.get("damage_reduction_flat", 0))
        ctx["damage_final"] = max(1, dmg - flat_red)
        log.trace(f"MitigationFlat | flat_reduction={flat_red} after_flat_red={ctx['damage_final']}")

    @staticmethod
    def _step_vampirism(stats_atk: dict, ctx: dict) -> None:
        vamp_pow = stats_atk.get("vampiric_power", 0.0)
        vamp_ch = stats_atk.get("vampiric_trigger_chance", 0.0)
        if ctx["damage_final"] > 0 and vamp_pow > 0 and CombatCalculator._check_chance(vamp_ch):
            ctx["lifesteal_amount"] = int(ctx["damage_final"] * vamp_pow)
            log.trace(f"VampirismProc | power={vamp_pow} amount={ctx['lifesteal_amount']}")

    # --------------------------------------------------------------------------
    # УТИЛИТЫ (Helpers)
    # --------------------------------------------------------------------------

    @staticmethod
    def _finalize_log(ctx: dict, shield_dmg: int, hp_dmg: int, attack_zones: list, block_zones: list) -> dict:
        ctx["visual_bar"] = CombatCalculator._generate_visual_bar(attack_zones, block_zones, ctx)
        return CombatCalculator._pack_result(ctx, shield_dmg, hp_dmg)

    @staticmethod
    def _generate_visual_bar(attack_zones: list, block_zones: list, ctx: dict) -> str:
        """Генерирует визуальную полоску для лога боя."""
        zones_order = ["head", "chest", "belly", "legs", "feet"]
        if ctx.get("is_dodged"):
            return "💨 [DODGE]"
        if ctx.get("is_parried"):
            return "🗡 [PARRY]"

        symbols = []
        is_crit = ctx.get("is_crit", False)
        block_type = ctx.get("block_type")

        for zone in zones_order:
            is_attacked = zone in (attack_zones or [])
            is_blocked_dir = zone in (block_zones or [])

            if is_blocked_dir and not is_attacked:
                symbols.append("🟦")
            elif not is_attacked:
                symbols.append("▫️")
            elif is_crit:
                symbols.append("🟥")
            elif block_type == "passive":
                symbols.append("🛡")
            elif is_blocked_dir:
                symbols.append("⚔️")
            else:
                symbols.append("⬛")

        bar = f"[{''.join(symbols)}]"
        log.trace(
            f"GenerateVisualBar | attack_zones={attack_zones} block_zones={block_zones} ctx={ctx} result_bar='{bar}'"
        )
        return bar

    @staticmethod
    def _distribute_damage(current_shield: int, damage: int) -> tuple[int, int]:
        if damage <= 0:
            return 0, 0
        if current_shield >= damage:
            return damage, 0
        return current_shield, damage - current_shield

    @staticmethod
    def _check_chance(chance: float) -> bool:
        if chance <= 0:
            return False
        if chance >= 1.0:
            return True
        return random.random() < chance

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
            "tokens_atk": ctx.get("tokens_gained_atk", {}),
            "tokens_def": ctx.get("tokens_gained_def", {}),
            "logs": ctx.get("logs", []),
        }
