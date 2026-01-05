# apps/game_core/modules/combat/core/combat_calculator.py
import random
from typing import Any

from loguru import logger as log


class CombatCalculator:
    """
    Сервис для выполнения чистых математических расчетов в бою.
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
            "thorns_damage": 0,
            "tokens_gained_atk": {},
            "tokens_gained_def": {},
        }
        log.debug(f"CalculateHit | event=start damage_type='{damage_type}' flags='{flags}'")

        # --- ЭТАП 0: Расчет сырого урона и Крита ---
        CombatCalculator._step_roll_damage(stats_atk, stats_def, damage_type, ctx, flags)

        if ctx["is_crit"]:
            ctx["tokens_gained_atk"]["crit"] = 1

        if ctx["damage_raw"] <= 0:
            return CombatCalculator._finalize_log(ctx, 0, 0, attack_zones, block_zones)

        # --- ЭТАП 1: Парирование ---
        can_parry = damage_type == "physical"
        if not flags.get("ignore_parry") and can_parry:
            parry_chance = min(stats_def.get("parry_chance", 0.0), stats_def.get("parry_cap", 0.5))
            if CombatCalculator._check_chance(parry_chance):
                ctx["is_parried"] = True
                ctx["damage_final"] = 0
                ctx["tokens_gained_def"]["parry"] = 1
                log.debug(f"CalculateHit | result=parry chance={parry_chance:.2f}")
                return CombatCalculator._finalize_log(ctx, 0, 0, attack_zones, block_zones)

        # --- ЭТАП 2: Уворот и Контратака ---
        if not flags.get("ignore_dodge"):
            dodge_val = stats_def.get("dodge_chance", 0.0)
            anti_dodge = stats_atk.get("anti_dodge_chance", 0.0)
            final_dodge = max(0.0, min(stats_def.get("dodge_cap", 0.75), dodge_val - anti_dodge))

            if CombatCalculator._check_chance(final_dodge):
                ctx["is_dodged"] = True
                ctx["damage_final"] = 0
                ctx["tokens_gained_def"]["dodge"] = 1  # Явно выдаем токен уворота

                counter_chance = min(
                    stats_def.get("counter_attack_chance", 0.0), stats_def.get("counter_attack_cap", 0.5)
                )
                if CombatCalculator._check_chance(counter_chance):
                    ctx["is_counter"] = True
                    ctx["tokens_gained_def"]["counter"] = 1
                    log.debug(f"CalculateHit | sub_event=counter_attack chance={counter_chance:.2f}")

                log.debug(f"CalculateHit | result=dodge chance={final_dodge:.2f}")
                return CombatCalculator._finalize_log(ctx, 0, 0, attack_zones, block_zones)

        # --- ЭТАП 3: Блок (Щит или Гео) ---
        is_shield_proc = False
        if not flags.get("ignore_block"):
            shield_block_chance = min(
                stats_def.get("shield_block_chance", 0.0), stats_def.get("shield_block_cap", 0.75)
            )
            if CombatCalculator._check_chance(shield_block_chance):
                is_shield_proc = True

        is_geo_block = False
        if not is_shield_proc:
            is_geo_block = CombatCalculator._check_geo_block(attack_zones, block_zones)

        if is_shield_proc or is_geo_block:
            ctx["is_blocked"] = True
            ctx["block_type"] = "passive" if is_shield_proc else "geo"
            ctx["thorns_damage"] = CombatCalculator._check_thorns(stats_def)

            # Выдача токенов
            ctx["tokens_gained_def"]["block"] = 1  # Общий токен блока
            if is_shield_proc:
                ctx["tokens_gained_def"]["shield_block"] = 1  # Специфичный токен щита
            if is_geo_block:
                ctx["tokens_gained_def"]["geo_block"] = 1  # Специфичный токен гео

            if ctx["is_crit"]:
                block_power = stats_def.get("shield_block_power", 0.5)
                ctx["damage_final"] = int(ctx["damage_raw"] * (1.0 - block_power))
                ctx["logs"].append(f"🛡️ {'Щит' if is_shield_proc else 'Гео-блок'} ослабил критический удар!")
            else:
                ctx["damage_final"] = 0
                log.debug(f"CalculateHit | result=blocked type={ctx['block_type']} damage=0")
                return CombatCalculator._finalize_log(ctx, 0, 0, attack_zones, block_zones)

        # --- ЭТАП 4: Снижение урона ---
        if ctx["damage_final"] == 0 and not ctx["is_blocked"]:
            ctx["damage_final"] = ctx["damage_raw"]

        CombatCalculator._step_mitigation(stats_atk, stats_def, damage_type, ctx)

        # --- ЭТАП 5: Пост-эффекты ---
        CombatCalculator._step_vampirism(stats_atk, ctx)

        if ctx["damage_final"] > 0:
            ctx["tokens_gained_atk"]["hit"] = 1

        dmg_shield, dmg_hp = CombatCalculator._distribute_damage(current_shield, ctx["damage_final"])
        return CombatCalculator._finalize_log(ctx, dmg_shield, dmg_hp, attack_zones, block_zones)

    @staticmethod
    def _check_geo_block(attack_zones: list[str], block_zones: list[str]) -> bool:
        atk_set = set(attack_zones or [])
        blk_set = set(block_zones or [])
        return bool(atk_set.intersection(blk_set))

    @staticmethod
    def _check_thorns(stats_def: dict[str, float]) -> int:
        thorns_damage = int(stats_def.get("thorns_damage_flat", 0.0))
        if thorns_damage > 0:
            log.debug(f"ThornsDamage | damage={thorns_damage}")
        return thorns_damage

    @staticmethod
    def _step_roll_damage(
        stats_atk: dict[str, float],
        stats_def: dict[str, float],
        damage_type: str,
        ctx: dict[str, Any],
        flags: dict[str, Any],
    ) -> None:
        cat_prefix = "physical" if damage_type == "physical" else "magical"
        d_min, d_max = 0, 0

        if damage_type == "physical":
            d_min, d_max = int(stats_atk.get("physical_damage_min", 0)), int(stats_atk.get("physical_damage_max", 0))
        else:
            power = stats_atk.get("magical_damage_power", 0.0)
            if power > 0:
                d_min, d_max = int(power * 0.9), int(power * 1.1)
            else:
                d_min, d_max = int(stats_atk.get("magical_damage_min", 0)), int(stats_atk.get("magical_damage_max", 0))

        if d_max <= 0:
            ctx["damage_raw"] = 0
            return

        dmg = random.randint(d_min, max(d_min, d_max))

        spec_bonus = stats_atk.get(f"{damage_type}_damage_bonus", 0.0)
        gen_bonus = (
            stats_atk.get(f"{cat_prefix}_damage_bonus", 0.0) if damage_type not in ("physical", "magical") else 0.0
        )
        dmg = int(dmg * (1.0 + spec_bonus + gen_bonus))

        skill_mult = flags.get("damage_mult", 1.0)
        dmg = int(dmg * skill_mult)

        crit_val = stats_atk.get(f"{damage_type}_crit_chance", 0.0) or stats_atk.get(f"{cat_prefix}_crit_chance", 0.0)
        skill_crit = flags.get("bonus_crit", 0.0)
        anti_crit = stats_def.get(f"anti_{cat_prefix}_crit_chance", 0.0) + stats_def.get("anti_crit_chance", 0.0)
        crit_cap = stats_atk.get(f"{cat_prefix}_crit_cap", 0.75)
        final_crit = max(0.0, min(crit_cap, (crit_val + skill_crit) - anti_crit))

        if CombatCalculator._check_chance(final_crit):
            ctx["is_crit"] = True
            crit_power = stats_atk.get(f"{cat_prefix}_crit_power_float", 1.5)
            dmg = int(dmg * crit_power)
            log.debug(f"RollDamage | event=crit_success power={crit_power:.2f} damage={dmg}")

        ctx["damage_raw"] = dmg

    @staticmethod
    def _step_mitigation(
        stats_atk: dict[str, float], stats_def: dict[str, float], damage_type: str, ctx: dict[str, Any]
    ) -> None:
        dmg = ctx["damage_final"]
        if dmg <= 0:
            return

        if damage_type == "physical":
            pierce_chance = min(stats_atk.get("physical_pierce_chance", 0.0), stats_atk.get("physical_pierce_cap", 0.3))
            if CombatCalculator._check_chance(pierce_chance):
                ctx["logs"].append("🎯 Атака пронзила броню!")
                log.debug(f"Mitigation | event=pierce_success chance={pierce_chance:.2f} damage_final={dmg}")
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

        flat_red = int(stats_def.get("damage_reduction_flat", 0))
        ctx["damage_final"] = max(1, dmg - flat_red)
        log.debug(f"Mitigation | event=flat_reduction reduction={flat_red} damage_final={ctx['damage_final']}")

    @staticmethod
    def _step_vampirism(stats_atk: dict[str, float], ctx: dict[str, Any]) -> None:
        vamp_pow_raw = stats_atk.get("vampiric_power", 0.0)
        vamp_ch_raw = stats_atk.get("vampiric_trigger_chance", 0.0)

        vamp_pow = min(vamp_pow_raw, stats_atk.get("vampiric_power_cap", 0.5))
        vamp_ch = min(vamp_ch_raw, stats_atk.get("vampiric_trigger_cap", 1.0))

        if ctx["damage_final"] > 0 and vamp_pow > 0 and CombatCalculator._check_chance(vamp_ch):
            ctx["lifesteal_amount"] = int(ctx["damage_final"] * vamp_pow)
            log.debug(
                f"Vampirism | event=proc power={vamp_pow:.2f} chance={vamp_ch:.2f} amount={ctx['lifesteal_amount']}"
            )

    @staticmethod
    def _finalize_log(
        ctx: dict[str, Any], shield_dmg: int, hp_dmg: int, attack_zones: list[str], block_zones: list[str]
    ) -> dict[str, Any]:
        ctx["visual_bar"] = CombatCalculator._generate_visual_bar(attack_zones, block_zones, ctx)
        if ctx.get("thorns_damage", 0) > 0:
            ctx["logs"].append(f"🥀 Нанесен урон шипами: <b>{ctx['thorns_damage']}</b>!")
        return CombatCalculator._pack_result(ctx, shield_dmg, hp_dmg)

    @staticmethod
    def _generate_visual_bar(attack_zones: list[str], block_zones: list[str], ctx: dict[str, Any]) -> str:
        zones_order = ["head", "chest", "belly", "legs", "feet"]
        if ctx.get("is_dodged"):
            if ctx.get("is_counter"):
                return "💨⚔️ [COUNTER]"
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
    def _pack_result(ctx: dict[str, Any], shield_dmg: int, hp_dmg: int) -> dict[str, Any]:
        return {
            "damage_total": ctx["damage_final"],
            "shield_dmg": shield_dmg,
            "hp_dmg": hp_dmg,
            "is_crit": ctx["is_crit"],
            "is_blocked": ctx["is_blocked"],
            "block_type": ctx.get("block_type"),
            "is_dodged": ctx.get("is_dodged", False),
            "is_parried": ctx.get("is_parried", False),
            "is_counter": ctx.get("is_counter", False),
            "lifesteal": ctx["lifesteal_amount"],
            "thorns_damage": ctx.get("thorns_damage", 0),
            "visual_bar": ctx.get("visual_bar", ""),
            "tokens_atk": ctx.get("tokens_gained_atk", {}),
            "tokens_def": ctx.get("tokens_gained_def", {}),
            "logs": ctx.get("logs", []),
        }
