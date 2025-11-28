# app/services/game_service/combat/combat_calculator.py
import random
from typing import Any

from loguru import logger as log


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
        log.debug(
            f"Расчет удара: Тип={damage_type}, Щит цели={current_shield}, "
            f"Зоны атаки={attack_zones}, Зоны блока={block_zones}"
        )

        if CombatCalculator._step_parry(stats_def, damage_type, ctx):
            ctx["tokens_gained_def"]["parry"] = 1
            log.debug("Результат: Парирование")
            return CombatCalculator._finalize_log(ctx, 0, 0, attack_zones, block_zones)

        if CombatCalculator._step_dodge(stats_atk, stats_def, damage_type, ctx):
            if ctx["is_counter"]:
                ctx["tokens_gained_def"]["counter"] = 1
            log.debug(f"Результат: Уклонение (Контратака: {ctx['is_counter']})")
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
        log.debug(f"Итог: Урон по щиту={dmg_shield}, Урон по HP={dmg_hp}, Крит={ctx['is_crit']}")

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
        parry_chance = stats_def.get("parry_chance", 0.0)
        if damage_type == "phys" and CombatCalculator._check_chance(parry_chance):
            ctx["is_parried"] = True
            log.trace(f"Шаг: Парирование (Шанс: {parry_chance:.2f}) -> Успех")
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
                log.trace(f"Шаг: Уклонение (Шанс: {dodge_chance:.2f}) -> Успех")
                counter_chance = stats_def.get("counter_attack_chance", 0.0)
                if CombatCalculator._check_chance(counter_chance):
                    ctx["is_counter"] = True
                    log.trace(f"Шаг: Контратака (Шанс: {counter_chance:.2f}) -> Успех")
                return True
        return False

    @staticmethod
    def _step_block(stats_def: dict, attack_zones: list, block_zones: list, ctx: dict) -> None:
        atk_set = set(attack_zones) if attack_zones else set()
        blk_set = set(block_zones) if block_zones else set()
        if atk_set.intersection(blk_set):
            ctx["is_blocked"] = True
            ctx["block_type"] = "geo"
            log.trace("Шаг: Блок -> Успех (Геометрический)")
            return
        shield_block_chance = stats_def.get("shield_block_chance", 0.0)
        if CombatCalculator._check_chance(shield_block_chance):
            ctx["is_blocked"] = True
            ctx["block_type"] = "passive"
            log.trace(f"Шаг: Блок (Шанс: {shield_block_chance:.2f}) -> Успех (Пассивный)")

    @staticmethod
    def _step_roll_damage(stats_atk: dict, stats_def: dict, damage_type: str, ctx: dict) -> None:
        # 1. Определяем правильный префикс (physical или magical)
        # Если damage_type="phys", то prefix="physical". Это совпадает с ключами Агрегатора.
        prefix = "magical" if damage_type == "magic" else "physical"

        # 2. Ищем ключи 'physical_damage_min' / 'physical_damage_max'
        # Используем prefix, а не dmg_prefix
        d_min = int(stats_atk.get(f"{prefix}_damage_min", 1))
        d_max = int(stats_atk.get(f"{prefix}_damage_max", 2))

        # 3. Роллим урон
        dmg = random.randint(d_min, max(d_min, d_max))

        log.trace(f"Шаг: Ролл урона -> База: {dmg} (из [{d_min}-{d_max}])")

        crit_chance = max(
            0.0,
            min(
                CombatCalculator.CAP_PHYS_CRIT,
                stats_atk.get(f"{prefix}_crit_chance", 0.0) - stats_def.get(f"anti_{prefix}_crit_chance", 0.0),
            ),
        )
        if CombatCalculator._check_chance(crit_chance):
            ctx["is_crit"] = True
            crit_power = stats_atk.get(f"{prefix}_crit_power_float", 1.5)
            if not ctx["is_blocked"]:
                dmg = int(dmg * crit_power)
                log.trace(f"Шаг: Крит (Шанс: {crit_chance:.2f}) -> Успех! Урон x{crit_power} -> {dmg}")

        if ctx["is_blocked"]:
            block_power = min(1.0, stats_def.get("shield_block_power", 0.5))
            dmg = int(dmg * (1.0 - block_power))
            log.trace(f"Шаг: Урон в блоке -> Снижение на {block_power * 100}% -> {dmg}")

        ctx["damage_raw"] = dmg

    @staticmethod
    def _step_mitigation(stats_atk: dict, stats_def: dict, damage_type: str, ctx: dict) -> None:
        dmg = ctx["damage_raw"]
        if dmg <= 0:
            ctx["damage_final"] = 0
            log.trace("Шаг: Митигация -> Пропущен (урон <= 0)")
            return

        res_stat = "magical_resistance" if damage_type == "magic" else "physical_resistance"
        pen_stat = "magical_penetration" if damage_type == "magic" else "physical_penetration"

        resistance = stats_def.get(res_stat, 0.0)
        penetration = stats_atk.get(pen_stat, 0.0)
        net_resist = min(0.85, resistance - penetration)
        dmg_after_res = int(dmg * (1.0 - net_resist))
        log.trace(
            f"Шаг: Митигация (Броня %) -> Урон {dmg} * (1 - ({resistance:.2f} - {penetration:.2f})) -> {dmg_after_res}"
        )
        dmg = dmg_after_res

        flat_reduction = int(stats_def.get("damage_reduction_flat", 0))
        dmg_after_flat = max(1, dmg - flat_reduction)
        log.trace(f"Шаг: Митигация (Броня Flat) -> Урон {dmg} - {flat_reduction} -> {dmg_after_flat}")

        ctx["damage_final"] = dmg_after_flat

    @staticmethod
    def _step_vampirism(stats_atk: dict, ctx: dict) -> None:
        vamp_power = stats_atk.get("vampiric_power", 0.0)
        vamp_chance = stats_atk.get("vampiric_trigger_chance", 0.8)
        if ctx["damage_final"] > 0 and vamp_power > 0 and CombatCalculator._check_chance(vamp_chance):
            lifesteal = int(ctx["damage_final"] * vamp_power)
            ctx["lifesteal_amount"] = lifesteal
            log.trace(
                f"Шаг: Вампиризм (Шанс: {vamp_chance:.2f}) -> Успех! "
                f"Украдено {lifesteal} HP ({ctx['damage_final']} * {vamp_power:.2f})"
            )

    @staticmethod
    def _distribute_damage(current_shield: int, damage: int) -> tuple[int, int]:
        if damage <= 0:
            return 0, 0
        if current_shield >= damage:
            log.trace(f"Распределение урона: {damage} урона полностью поглощено щитом ({current_shield})")
            return damage, 0
        shield_dmg = current_shield
        hp_dmg = damage - current_shield
        log.trace(
            f"Распределение урона: Щит ({current_shield}) сломан! {shield_dmg} урона по щиту, {hp_dmg} урона по HP."
        )
        return shield_dmg, hp_dmg

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
            # 🔥 FIX: Заменили 0 на {}, чтобы не ломать итерацию в сервисе
            "tokens_atk": ctx.get("tokens_gained_atk", {}),
            "tokens_def": ctx.get("tokens_gained_def", {}),
            # Логи (из предыдущего фикса)
            "logs": ctx.get("logs", []),
        }
