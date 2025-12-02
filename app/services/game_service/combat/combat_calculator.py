import random
from typing import Any

from loguru import logger as log


class CombatCalculator:
    """
    Сервис для выполнения чистых математических расчетов в бою.

    Отвечает за расчет результатов одного удара, включая урон,
    шансы на критический удар, блокирование, уклонение и парирование.
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
        Рассчитывает результат одного удара в бою.

        Args:
            stats_atk: Агрегированные характеристики атакующего актора.
            stats_def: Агрегированные характеристики защищающегося актора.
            current_shield: Текущее значение щита защищающегося актора.
            attack_zones: Список зон, по которым атакует актор.
            block_zones: Список зон, которые блокирует защищающийся актор.
            damage_type: Тип наносимого урона ("physical" или "magical").
            flags: Дополнительные флаги, влияющие на расчет (например, "ignore_parry").

        Returns:
            Словарь, содержащий детальные результаты удара, включая нанесенный урон,
            флаги (крит, блок, уворот), логи и токены.
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
            "thorns_damage": 0,
            "tokens_gained_atk": {},
            "tokens_gained_def": {},
        }
        log.trace(f"CombatCalculator | event=calculate_hit damage_type='{damage_type}' flags='{flags}'")

        can_parry = damage_type == "physical"
        if not flags.get("ignore_parry") and can_parry:
            parry_chance = min(stats_def.get("parry_chance", 0.0), stats_def.get("parry_cap", 0.5))
            if CombatCalculator._check_chance(parry_chance):
                ctx["is_parried"] = True
                ctx["tokens_gained_def"]["parry"] = 1
                log.debug(f"CombatCalculator | result=parry chance={parry_chance}")
                ctx["thorns_damage"] = CombatCalculator._check_thorns(stats_def, damage_type, 1.0)
                return CombatCalculator._finalize_log(ctx, 0, 0, attack_zones, block_zones)

        if not flags.get("ignore_dodge"):
            dodge_val = stats_def.get("dodge_chance", 0.0)
            anti_dodge = stats_atk.get("anti_dodge_chance", 0.0)
            final_dodge = max(0.0, min(stats_def.get("dodge_cap", 0.75), dodge_val - anti_dodge))
            if CombatCalculator._check_chance(final_dodge):
                ctx["is_dodged"] = True
                if CombatCalculator._check_chance(stats_def.get("counter_attack_chance", 0.0)):
                    ctx["is_counter"] = True
                    ctx["tokens_gained_def"]["counter"] = 1
                    log.debug("CombatCalculator | sub_event=counter_attack")
                log.debug(f"CombatCalculator | result=dodge chance={final_dodge}")
                ctx["thorns_damage"] = CombatCalculator._check_thorns(stats_def, damage_type, 1.0)
                return CombatCalculator._finalize_log(ctx, 0, 0, attack_zones, block_zones)

        if not flags.get("ignore_block"):
            shield_block_chance = min(
                stats_def.get("shield_block_chance", 0.0), stats_def.get("shield_block_cap", 0.75)
            )
            if CombatCalculator._check_chance(shield_block_chance):
                ctx["is_blocked"], ctx["block_type"] = True, "passive"
                log.debug(f"CombatCalculator | result=passive_shield_block chance={shield_block_chance}")
                ctx["thorns_damage"] = CombatCalculator._check_thorns(
                    stats_def, damage_type, stats_def.get("shield_block_power", 0.0)
                )
                CombatCalculator._step_roll_damage(stats_atk, stats_def, damage_type, ctx, flags)
                block_power = min(1.0, stats_def.get("shield_block_power", 0.5))
                ctx["damage_final"] = int(ctx["damage_raw"] * (1.0 - block_power))
                dmg_shield, dmg_hp = CombatCalculator._distribute_damage(current_shield, ctx["damage_final"])
                log.debug(
                    f"CombatCalculator | damage_distribution total={ctx['damage_final']} shield_dmg={dmg_shield} hp_dmg={dmg_hp}"
                )
                return CombatCalculator._finalize_log(ctx, dmg_shield, dmg_hp, attack_zones, block_zones)

        is_geo_block = CombatCalculator._check_geo_block(attack_zones, block_zones)
        if is_geo_block:
            ctx["is_blocked"], ctx["block_type"] = True, "geo"
            log.trace("CombatCalculator | block_type=geo")

        CombatCalculator._step_roll_damage(stats_atk, stats_def, damage_type, ctx, flags)

        if ctx["is_blocked"] and ctx["block_type"] == "geo":
            if ctx["is_crit"]:
                CombatCalculator._step_mitigation(stats_atk, stats_def, damage_type, ctx)
                ctx["damage_final"] = int(ctx["damage_final"] * 0.5)
                log.trace(f"CombatCalculator | geo_block_crit damage_final={ctx['damage_final']}")
            else:
                ctx["damage_final"] = 0
                log.trace("CombatCalculator | geo_block_normal damage_final=0")
        else:
            CombatCalculator._step_mitigation(stats_atk, stats_def, damage_type, ctx)

        CombatCalculator._step_vampirism(stats_atk, ctx)

        if ctx["is_blocked"]:
            ctx["tokens_gained_def"]["block"] = 1
        elif ctx["damage_final"] > 0:
            ctx["tokens_gained_atk"]["hit"] = 1
        if ctx["is_crit"]:
            ctx["tokens_gained_atk"]["crit"] = 1

        dmg_shield, dmg_hp = CombatCalculator._distribute_damage(current_shield, ctx["damage_final"])
        log.debug(
            f"CombatCalculator | damage_distribution total={ctx['damage_final']} shield_dmg={dmg_shield} hp_dmg={dmg_hp}"
        )
        return CombatCalculator._finalize_log(ctx, dmg_shield, dmg_hp, attack_zones, block_zones)

    @staticmethod
    def _check_geo_block(attack_zones: list[str], block_zones: list[str]) -> bool:
        """
        Проверяет наличие геометрического (позиционного) блока.

        Args:
            attack_zones: Список зон атаки.
            block_zones: Список зон блокировки.

        Returns:
            True, если есть пересечение зон атаки и блокировки, иначе False.
        """
        atk_set = set(attack_zones or [])
        blk_set = set(block_zones or [])
        return bool(atk_set.intersection(blk_set))

    @staticmethod
    def _check_thorns(stats_def: dict[str, float], damage_type: str, block_mult: float) -> int:
        """
        Рассчитывает урон, отражаемый шипами (thorns damage).

        Args:
            stats_def: Агрегированные характеристики защищающегося актора.
            damage_type: Тип наносимого урона.
            block_mult: Множитель урона от блока.

        Returns:
            Количество отраженного урона в виде целого числа.
        """
        thorns_reflect_pct = stats_def.get("thorns_damage_reflect", 0.0)
        if thorns_reflect_pct <= 0:
            return 0

        hp_max = stats_def.get("hp_max", 100)
        base_reflect_damage = hp_max * 0.1
        thorns_damage = int(base_reflect_damage * thorns_reflect_pct * block_mult)

        if thorns_damage > 0:
            log.debug(
                f"CombatCalculator | thorns_damage_calculated damage={thorns_damage} reflect_pct={thorns_reflect_pct}"
            )
        return thorns_damage

    @staticmethod
    def _step_roll_damage(
        stats_atk: dict[str, float],
        stats_def: dict[str, float],
        damage_type: str,
        ctx: dict[str, Any],
        flags: dict[str, Any],
    ) -> None:
        """
        Выполняет бросок урона, учитывая тип урона, бонусы и критические удары.

        Args:
            stats_atk: Агрегированные характеристики атакующего.
            stats_def: Агрегированные характеристики защищающегося.
            damage_type: Тип наносимого урона.
            ctx: Контекст расчета удара.
            flags: Дополнительные флаги.
        """
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
        log.trace(f"CombatCalculator | roll_damage_base min={d_min} max={d_max} rolled={dmg}")

        spec_bonus = stats_atk.get(f"{damage_type}_damage_bonus", 0.0)
        gen_bonus = (
            stats_atk.get(f"{cat_prefix}_damage_bonus", 0.0) if damage_type not in ("physical", "magical") else 0.0
        )
        dmg = int(dmg * (1.0 + spec_bonus + gen_bonus))
        log.trace(f"CombatCalculator | roll_damage_bonus bonus_pct={spec_bonus + gen_bonus} after_bonus={dmg}")

        skill_mult = flags.get("damage_mult", 1.0)
        dmg = int(dmg * skill_mult)
        log.trace(f"CombatCalculator | roll_damage_skill_mult mult={skill_mult} after_mult={dmg}")

        crit_val = stats_atk.get(f"{damage_type}_crit_chance", 0.0) or stats_atk.get(f"{cat_prefix}_crit_chance", 0.0)
        skill_crit = flags.get("bonus_crit", 0.0)
        anti_crit = stats_def.get(f"anti_{cat_prefix}_crit_chance", 0.0) + stats_def.get("anti_crit_chance", 0.0)
        crit_cap = stats_atk.get(f"{cat_prefix}_crit_cap", 0.75)
        final_crit = max(0.0, min(crit_cap, (crit_val + skill_crit) - anti_crit))

        if CombatCalculator._check_chance(final_crit):
            ctx["is_crit"] = True
            crit_power = stats_atk.get(f"{cat_prefix}_crit_power_float", 1.5)
            dmg = int(dmg * crit_power)
            log.trace(f"CombatCalculator | roll_damage_crit power={crit_power} after_crit={dmg}")

        ctx["damage_raw"] = dmg

    @staticmethod
    def _step_mitigation(
        stats_atk: dict[str, float], stats_def: dict[str, float], damage_type: str, ctx: dict[str, Any]
    ) -> None:
        """
        Применяет снижение урона (сопротивления и плоскую редукцию).

        Args:
            stats_atk: Агрегированные характеристики атакующего.
            stats_def: Агрегированные характеристики защищающегося.
            damage_type: Тип наносимого урона.
            ctx: Контекст расчета удара.
        """
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
        log.trace(f"CombatCalculator | mitigation_resistance net_resist={net_resist} after_resist={dmg}")

        flat_red = int(stats_def.get("damage_reduction_flat", 0))
        ctx["damage_final"] = max(1, dmg - flat_red)
        log.trace(f"CombatCalculator | mitigation_flat flat_reduction={flat_red} after_flat_red={ctx['damage_final']}")

    @staticmethod
    def _step_vampirism(stats_atk: dict[str, float], ctx: dict[str, Any]) -> None:
        """
        Рассчитывает вампиризм (lifesteal) на основе нанесенного урона.

        Args:
            stats_atk: Агрегированные характеристики атакующего.
            ctx: Контекст расчета удара.
        """
        vamp_pow = stats_atk.get("vampiric_power", 0.0)
        vamp_ch = stats_atk.get("vampiric_trigger_chance", 0.0)
        if ctx["damage_final"] > 0 and vamp_pow > 0 and CombatCalculator._check_chance(vamp_ch):
            ctx["lifesteal_amount"] = int(ctx["damage_final"] * vamp_pow)
            log.trace(f"CombatCalculator | vampirism_proc power={vamp_pow} amount={ctx['lifesteal_amount']}")

    @staticmethod
    def _finalize_log(
        ctx: dict[str, Any], shield_dmg: int, hp_dmg: int, attack_zones: list[str], block_zones: list[str]
    ) -> dict[str, Any]:
        """
        Добавляет визуальную полоску и урон шипами в контекст, затем упаковывает результат.

        Args:
            ctx: Контекст расчета удара.
            shield_dmg: Урон, поглощенный щитом.
            hp_dmg: Урон, нанесенный HP.
            attack_zones: Зоны атаки.
            block_zones: Зоны блокировки.

        Returns:
            Словарь с финальными результатами удара.
        """
        ctx["visual_bar"] = CombatCalculator._generate_visual_bar(attack_zones, block_zones, ctx)
        if ctx.get("thorns_damage", 0) > 0:
            ctx["logs"].append(f"🥀 Нанесен урон шипами: <b>{ctx['thorns_damage']}</b>!")
        return CombatCalculator._pack_result(ctx, shield_dmg, hp_dmg)

    @staticmethod
    def _generate_visual_bar(attack_zones: list[str], block_zones: list[str], ctx: dict[str, Any]) -> str:
        """
        Генерирует текстовую визуальную полоску, отображающую результат удара по зонам.

        Args:
            attack_zones: Зоны, по которым была произведена атака.
            block_zones: Зоны, которые были заблокированы.
            ctx: Контекст расчета удара.

        Returns:
            Строка, представляющая визуальную полоску.
        """
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
        log.trace(f"CombatCalculator | generate_visual_bar result='{bar}'")
        return bar

    @staticmethod
    def _distribute_damage(current_shield: int, damage: int) -> tuple[int, int]:
        """
        Распределяет нанесенный урон между щитом и HP.

        Args:
            current_shield: Текущее значение щита.
            damage: Общий нанесенный урон.

        Returns:
            Кортеж `(shield_damage, hp_damage)`, где `shield_damage` — урон,
            поглощенный щитом, а `hp_damage` — урон, прошедший по HP.
        """
        if damage <= 0:
            return 0, 0
        if current_shield >= damage:
            return damage, 0
        return current_shield, damage - current_shield

    @staticmethod
    def _check_chance(chance: float) -> bool:
        """
        Проверяет, сработал ли шанс.

        Args:
            chance: Шанс в диапазоне от 0.0 до 1.0.

        Returns:
            True, если шанс сработал, иначе False.
        """
        if chance <= 0:
            return False
        if chance >= 1.0:
            return True
        return random.random() < chance

    @staticmethod
    def _pack_result(ctx: dict[str, Any], shield_dmg: int, hp_dmg: int) -> dict[str, Any]:
        """
        Упаковывает результаты расчета удара в финальный словарь.

        Args:
            ctx: Контекст расчета удара.
            shield_dmg: Урон, поглощенный щитом.
            hp_dmg: Урон, нанесенный HP.

        Returns:
            Словарь с финальными результатами удара.
        """
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
