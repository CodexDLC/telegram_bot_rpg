# app/services/game_service/combat/combat_calculator.py
import random
from typing import Any

from loguru import logger as log


class CombatCalculator:
    """
    Чистая математика боя (Pure Logic).
    v4: Поддержка динамических статов (DTO), капов и флагов способностей.
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
            flags: Словарь правил из активного скилла (ignore_block, damage_mult...).
        """

        if flags is None:
            flags = {}

        # Скилл может подменить тип урона (например, меч -> огонь)
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

        log.trace(f"Calc Start: Type={damage_type}, Flags={flags}")

        # ==========================================================================
        # 1. ПАРИРОВАНИЕ (Parry)
        # ==========================================================================
        # Парировать можно только физику (по умолчанию), если флаг не говорит обратное
        can_parry = damage_type == "physical"

        if not flags.get("ignore_parry") and can_parry:
            parry_chance = stats_def.get("parry_chance", 0.0)
            parry_cap = stats_def.get("parry_cap", 0.50)  # Читаем кап из DTO

            final_chance = min(parry_chance, parry_cap)

            if CombatCalculator._check_chance(final_chance):
                ctx["is_parried"] = True
                ctx["tokens_gained_def"]["parry"] = 1
                return CombatCalculator._finalize_log(ctx, 0, 0, attack_zones, block_zones)

        # ==========================================================================
        # 2. УКЛОНЕНИЕ (Dodge)
        # ==========================================================================
        if not flags.get("ignore_dodge"):
            dodge_val = stats_def.get("dodge_chance", 0.0)

            # Анти-уворот (Точность)
            anti_dodge = stats_atk.get("anti_dodge_chance", 0.0)

            # Кап уворота
            dodge_cap = stats_def.get("dodge_cap", 0.75)

            # Формула: (Уворот - Точность), но не больше Капа и не меньше 0
            final_dodge = max(0.0, min(dodge_cap, dodge_val - anti_dodge))

            if CombatCalculator._check_chance(final_dodge):
                ctx["is_dodged"] = True

                # Попытка контратаки при увороте
                counter_chance = stats_def.get("counter_attack_chance", 0.0)
                if CombatCalculator._check_chance(counter_chance):
                    ctx["is_counter"] = True
                    ctx["tokens_gained_def"]["counter"] = 1

                return CombatCalculator._finalize_log(ctx, 0, 0, attack_zones, block_zones)

        # ==========================================================================
        # 3. БЛОК (Block)
        # ==========================================================================
        if not flags.get("ignore_block"):
            CombatCalculator._step_block(stats_def, attack_zones, block_zones, ctx)
        else:
            log.trace("Блок проигнорирован флагом ignore_block")

        # ==========================================================================
        # 4. РАСЧЕТ УРОНА (Roll Damage)
        # ==========================================================================
        CombatCalculator._step_roll_damage(stats_atk, stats_def, damage_type, ctx, flags)

        # ==========================================================================
        # 5. СНИЖЕНИЕ УРОНА (Mitigation)
        # ==========================================================================
        CombatCalculator._step_mitigation(stats_atk, stats_def, damage_type, ctx)

        # ==========================================================================
        # 6. ЭФФЕКТЫ ПОСЛЕ УРОНА (Vampirism etc)
        # ==========================================================================
        CombatCalculator._step_vampirism(stats_atk, ctx)

        # Начисление токенов за результат
        if ctx["is_blocked"]:
            ctx["tokens_gained_def"]["block"] = 1
        elif ctx["damage_final"] > 0:
            ctx["tokens_gained_atk"]["hit"] = 1

        if ctx["is_crit"]:
            ctx["tokens_gained_atk"]["crit"] = 1

        # Распределение по Щиту и HP
        dmg_shield, dmg_hp = CombatCalculator._distribute_damage(current_shield, ctx["damage_final"])

        return CombatCalculator._finalize_log(ctx, dmg_shield, dmg_hp, attack_zones, block_zones)

    # --------------------------------------------------------------------------
    # ВНУТРЕННИЕ ШАГИ (Steps)
    # --------------------------------------------------------------------------

    @staticmethod
    def _step_block(stats_def: dict, attack_zones: list, block_zones: list, ctx: dict) -> None:
        # 1. Геометрический блок (Угадал зону)
        atk_set = set(attack_zones) if attack_zones else set()
        blk_set = set(block_zones) if block_zones else set()

        if atk_set.intersection(blk_set):
            ctx["is_blocked"] = True
            ctx["block_type"] = "geo"
            return

        # 2. Пассивный блок щитом (Stat Check)
        block_chance = stats_def.get("shield_block_chance", 0.0)
        block_cap = stats_def.get("shield_block_cap", 0.75)

        final_chance = min(block_chance, block_cap)

        if CombatCalculator._check_chance(final_chance):
            ctx["is_blocked"] = True
            ctx["block_type"] = "passive"

    @staticmethod
    def _step_roll_damage(stats_atk: dict, stats_def: dict, damage_type: str, ctx: dict, flags: dict) -> None:
        """
        Полностью динамический ролл урона на основе damage_type.
        """
        # Определяем категорию (физика или магия) для фоллбэков
        cat_prefix = "physical" if damage_type == "physical" else "magical"

        # --- А. Базовый Ролл (Base Roll) ---
        d_min, d_max = 0, 0

        if damage_type == "physical":
            # Классика для оружия: Мин - Макс
            d_min = int(stats_atk.get("physical_damage_min", 1))
            d_max = int(stats_atk.get("physical_damage_max", 2))
        else:
            # Магия / Стихии: От "Силы Магии" (Power)
            power = stats_atk.get("magical_damage_power", 0.0)

            # Если Power > 0, считаем разброс +/- 10%
            if power > 0:
                d_min = int(power * 0.9)
                d_max = int(power * 1.1)
            else:
                # Фоллбэк: если вдруг кто-то задал старые min/max для магии
                d_min = int(stats_atk.get("magical_damage_min", 0))
                d_max = int(stats_atk.get("magical_damage_max", 0))

        # Защита от нулевого урона (кроме кулаков)
        if d_max == 0 and damage_type == "physical":
            d_min, d_max = 1, 2

        if d_max == 0:
            ctx["damage_raw"] = 0
            # Если урона нет, выходим сразу (но это не промах, просто 0 урона)
            return

        dmg = random.randint(d_min, max(d_min, d_max))

        # --- Б. Бонусы (Damage Bonus) ---
        # 1. Специфичный бонус (fire_damage_bonus)
        specific_bonus = stats_atk.get(f"{damage_type}_damage_bonus", 0.0)

        # 2. Общий бонус категории (magical_damage_bonus), если это не чистая магия/физика
        general_bonus = 0.0
        if damage_type not in ("physical", "magical"):
            general_bonus = stats_atk.get(f"{cat_prefix}_damage_bonus", 0.0)

        total_bonus_pct = specific_bonus + general_bonus
        dmg = int(dmg * (1.0 + total_bonus_pct))

        # --- В. Множитель Скилла (Skill Multiplier) ---
        skill_mult = flags.get("damage_mult", 1.0)
        if skill_mult != 1.0:
            dmg = int(dmg * skill_mult)

        # --- Г. Крит (Crit) ---
        # 1. Шанс крита (fire_crit -> magical_crit)
        crit_val = stats_atk.get(f"{damage_type}_crit_chance", 0.0)
        if crit_val == 0.0:
            crit_val = stats_atk.get(f"{cat_prefix}_crit_chance", 0.0)

        # 2. Бонус крита от скилла
        skill_crit = flags.get("bonus_crit", 0.0)

        # 3. Анти-крит врага
        anti_crit = stats_def.get(f"anti_{cat_prefix}_crit_chance", 0.0) + stats_def.get("anti_crit_chance", 0.0)

        # 4. Кап крита
        crit_cap = stats_atk.get(f"{cat_prefix}_crit_cap", 0.75)

        # Итоговый шанс
        final_crit_chance = max(0.0, min(crit_cap, (crit_val + skill_crit) - anti_crit))

        if CombatCalculator._check_chance(final_crit_chance):
            ctx["is_crit"] = True

            # Сила крита (fire_power -> magical_power -> 1.5)
            pow_key = f"{cat_prefix}_crit_power_float"
            crit_power = stats_atk.get(pow_key, 1.5)

            # Блок щитом срезает крит (обычно крит не проходит в блок, но тут просто урон)
            if not ctx["is_blocked"]:
                dmg = int(dmg * crit_power)

        # --- Д. Срез урона Блоком (Block Mitigation) ---
        if ctx["is_blocked"]:
            block_power = stats_def.get("shield_block_power", 0.5)
            # Капа на силу блока нет (или он 100%), но проверим на всякий
            block_power = min(1.0, block_power)

            dmg = int(dmg * (1.0 - block_power))

        ctx["damage_raw"] = dmg

    @staticmethod
    def _step_mitigation(stats_atk: dict, stats_def: dict, damage_type: str, ctx: dict) -> None:
        dmg = ctx["damage_raw"]
        if dmg <= 0:
            ctx["damage_final"] = 0
            return

        # 1. Резист (Resistance vs Penetration)
        res_key = f"{damage_type}_resistance"
        pen_key = f"{damage_type}_penetration"

        resistance = stats_def.get(res_key, 0.0)
        penetration = stats_atk.get(pen_key, 0.0)

        # Фоллбэк на категорию (magical), если нет специфики
        cat_prefix = "physical" if damage_type == "physical" else "magical"

        if resistance == 0.0 and damage_type not in ("physical", "magical"):
            resistance = stats_def.get(f"{cat_prefix}_resistance", 0.0)

        if penetration == 0.0 and damage_type not in ("physical", "magical"):
            penetration = stats_atk.get(f"{cat_prefix}_penetration", 0.0)

        # Кап резиста
        res_cap = stats_def.get("resistance_cap", 0.85)

        # Эффективный резист
        net_resist = max(0.0, min(res_cap, resistance - penetration))

        dmg = int(dmg * (1.0 - net_resist))

        # 2. Плоское снижение (Flat Reduction)
        flat_red = int(stats_def.get("damage_reduction_flat", 0))
        dmg = max(1, dmg - flat_red)

        ctx["damage_final"] = dmg

    @staticmethod
    def _step_vampirism(stats_atk: dict, ctx: dict) -> None:
        vamp_power = stats_atk.get("vampiric_power", 0.0)
        vamp_chance = stats_atk.get("vampiric_trigger_chance", 0.0)

        if ctx["damage_final"] > 0 and vamp_power > 0 and CombatCalculator._check_chance(vamp_chance):
            lifesteal = int(ctx["damage_final"] * vamp_power)
            ctx["lifesteal_amount"] = lifesteal

    # --------------------------------------------------------------------------
    # УТИЛИТЫ (Helpers)
    # --------------------------------------------------------------------------

    @staticmethod
    def _finalize_log(ctx: dict, shield_dmg: int, hp_dmg: int, attack_zones: list, block_zones: list) -> dict:
        visual_bar = CombatCalculator._generate_visual_bar(attack_zones, block_zones, ctx)
        ctx["visual_bar"] = visual_bar
        return CombatCalculator._pack_result(ctx, shield_dmg, hp_dmg)

    @staticmethod
    def _generate_visual_bar(attack_zones: list, block_zones: list, ctx: dict) -> str:
        zones_order = ["head", "chest", "legs", "feet"]
        symbols = []

        # Если удар не состоялся (уворот/парирование), зоны не рисуем (или рисуем пустые)
        if ctx.get("is_dodged") or ctx.get("is_parried"):
            return ""  # Можно вернуть спец символ "💨"

        for zone in zones_order:
            is_attacked = zone in (attack_zones or [])
            is_blocked = zone in (block_zones or [])

            if is_attacked and is_blocked:
                symbols.append("🛡")  # Удар в блок
            elif is_attacked:
                symbols.append("🟥")  # Попадание
            elif is_blocked:
                symbols.append("🟦")  # Блок (пустой)
            else:
                symbols.append("▫️")  # Пусто

        return f"[{''.join(symbols)}]"

    @staticmethod
    def _distribute_damage(current_shield: int, damage: int) -> tuple[int, int]:
        if damage <= 0:
            return 0, 0
        if current_shield >= damage:
            return damage, 0
        shield_dmg = current_shield
        hp_dmg = damage - current_shield
        return shield_dmg, hp_dmg

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
