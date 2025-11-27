# app/services/game_service/combat/combat_calculator.py
import random
from typing import Any


class CombatCalculator:
    """
    Чистая математика боя (Pure Logic).
    Рефакторинг: Pipeline Pattern (Конвейер).
    """

    # --- КОНСТАНТЫ (Hard Caps) ---
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
        """
        Главный метод-оркестратор. Запускает этапы расчета по очереди.
        """
        # 0. Инициализация контекста (State Object для расчета)
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
        }

        # 1. Этап: ПАРИРОВАНИЕ (Прерывает цепочку при успехе)
        if CombatCalculator._step_parry(stats_def, damage_type, ctx):
            return CombatCalculator._pack_result(ctx, 0, 0)

        # 2. Этап: УВОРОТ (Прерывает цепочку при успехе)
        if CombatCalculator._step_dodge(stats_atk, stats_def, damage_type, ctx):
            return CombatCalculator._pack_result(ctx, 0, 0)

        # 3. Этап: БЛОК (Определяет флаги, но не прерывает)
        CombatCalculator._step_block(stats_def, attack_zones, block_zones, ctx)

        # 4. Этап: РАСЧЕТ БАЗОВОГО УРОНА И КРИТА
        CombatCalculator._step_roll_damage(stats_atk, stats_def, damage_type, ctx)

        # 5. Этап: МИТИГАЦИЯ (Резисты и Броня)
        CombatCalculator._step_mitigation(stats_atk, stats_def, damage_type, ctx)

        # 6. Этап: ВАМПИРИЗМ (Пост-эффект)
        CombatCalculator._step_vampirism(stats_atk, ctx)

        # 7. Этап: РАСПРЕДЕЛЕНИЕ (Финал)
        dmg_shield, dmg_hp = CombatCalculator._distribute_damage(current_shield, ctx["damage_final"], ctx["logs"])

        return CombatCalculator._pack_result(ctx, dmg_shield, dmg_hp)

    # =========================================================================
    # ПРИВАТНЫЕ МЕТОДЫ ЭТАПОВ (STEPS)
    # =========================================================================

    @staticmethod
    def _step_parry(stats_def: dict, damage_type: str, ctx: dict) -> bool:
        """Возвращает True, если удар парирован (урон 0)."""
        if damage_type == "phys":
            parry_chance = stats_def.get("parry_chance", 0.0)
            if CombatCalculator._check_chance(parry_chance):
                ctx["is_parried"] = True
                ctx["logs"].append("⚔️ <b>ПАРИРОВАНИЕ!</b> (Удар отбит)")
                return True
        return False

    @staticmethod
    def _step_dodge(stats_atk: dict, stats_def: dict, damage_type: str, ctx: dict) -> bool:
        """Возвращает True, если удар уклонен (урон 0). Также проверяет контратаку."""
        if damage_type == "phys":
            dodge_raw = stats_def.get("dodge_chance", 0.0)
            anti_dodge = stats_atk.get("anti_dodge", 0.0)

            dodge_chance = max(0.0, min(CombatCalculator.CAP_DODGE, dodge_raw - anti_dodge))

            if CombatCalculator._check_chance(dodge_chance):
                ctx["is_dodged"] = True
                ctx["logs"].append("💨 <b>УВОРОТ!</b>")

                # Контратака (под-этап уворота)
                counter_chance = stats_def.get("counter_attack_chance", 0.0)
                if CombatCalculator._check_chance(counter_chance):
                    ctx["is_counter"] = True
                    ctx["logs"].append("⚡ <b>КОНТРАТАКА!</b>")

                return True
        return False

    @staticmethod
    def _step_block(stats_def: dict, attack_zones: list, block_zones: list, ctx: dict) -> None:
        """Проверяет условия блока (Геометрия или Пассивка)."""
        # А. Геометрический блок
        if set(attack_zones).intersection(set(block_zones)):
            ctx["is_blocked"] = True
            ctx["block_type"] = "geo"
            ctx["logs"].append("🛡 <b>БЛОК (Зона)!</b>")
            return

        # Б. Пассивный блок щитом
        shield_chance = stats_def.get("shield_block_chance", 0.0)
        if shield_chance > 0 and CombatCalculator._check_chance(shield_chance):
            ctx["is_blocked"] = True
            ctx["block_type"] = "passive"
            ctx["logs"].append("🛡 <b>БЛОК (Щит)!</b>")

    @staticmethod
    def _step_roll_damage(stats_atk: dict, stats_def: dict, damage_type: str, ctx: dict) -> None:
        """Считает 'сырой' урон и применяет множители крита/блока."""
        prefix = "magical" if damage_type == "magic" else "physical"
        dmg_prefix = "magic" if damage_type == "magic" else "phys"

        # 1. Ролл Базы
        d_min = int(stats_atk.get(f"{dmg_prefix}_damage_min", 1))
        d_max = int(stats_atk.get(f"{dmg_prefix}_damage_max", 2))
        if d_max < d_min:
            d_max = d_min

        dmg = random.randint(d_min, d_max)

        # 2. Крит
        crit_raw = stats_atk.get(f"{prefix}_crit_chance", 0.0)
        anti_crit = stats_def.get(f"anti_{prefix}_crit_chance", 0.0)

        crit_cap = CombatCalculator.CAP_MAGIC_CRIT if damage_type == "magic" else CombatCalculator.CAP_PHYS_CRIT
        crit_chance = max(0.0, min(crit_cap, crit_raw - anti_crit))

        if CombatCalculator._check_chance(crit_chance):
            ctx["is_crit"] = True

            if ctx["is_blocked"]:
                # Крит в блок: урон не умножаем, но флаг крита (для тактики) стоит
                ctx["logs"].append("🛡 <b>Крит заблокирован!</b>")
            else:
                # Чистый крит
                crit_power = stats_atk.get(f"{prefix}_crit_power_float", 1.5)
                dmg = int(dmg * crit_power)
                ctx["logs"].append("💥 <b>КРИТИЧЕСКИЙ УДАР!</b>")
        else:
            if not ctx["is_blocked"]:
                ctx["logs"].append("🗡 Попадание.")

        # 3. Снижение урона от Блока (Block Mitigation)
        if ctx["is_blocked"]:
            block_mitigation = stats_def.get("shield_block_power", 0.5)
            block_mitigation = min(1.0, block_mitigation)
            dmg = int(dmg * (1.0 - block_mitigation))

        ctx["damage_raw"] = dmg

    @staticmethod
    def _step_mitigation(stats_atk: dict, stats_def: dict, damage_type: str, ctx: dict) -> None:
        """Применяет резисты и плоскую броню."""
        dmg = ctx["damage_raw"]
        if dmg <= 0:
            ctx["damage_final"] = 0
            return

        # 1. Процент (Resist - Penetration)
        res_stat = "magical_resistance" if damage_type == "magic" else "physical_resistance"
        pen_stat = "magical_penetration" if damage_type == "magic" else "physical_penetration"

        net_resist = stats_def.get(res_stat, 0.0) - stats_atk.get(pen_stat, 0.0)
        net_resist = min(0.85, net_resist)  # Кап резиста

        dmg = int(dmg * (1.0 - net_resist))

        # 2. Плоская броня
        flat_armor = int(stats_def.get("damage_reduction_flat", 0))
        dmg = max(1, dmg - flat_armor)

        ctx["damage_final"] = dmg

    @staticmethod
    def _step_vampirism(stats_atk: dict, ctx: dict) -> None:
        """Рассчитывает отхил от нанесенного урона."""
        dmg_done = ctx["damage_final"]
        vamp_power = stats_atk.get("vampiric_power", 0.0)

        if vamp_power > 0 and dmg_done > 0:
            trigger_chance = stats_atk.get("vampiric_trigger_chance", 0.8)

            if CombatCalculator._check_chance(trigger_chance):
                heal = int(dmg_done * vamp_power)
                if heal > 0:
                    ctx["lifesteal_amount"] = heal
                    ctx["logs"].append(f"🩸 Вампиризм: +{heal} HP")

    # --- Вспомогательные методы (Helpers) ---

    @staticmethod
    def _distribute_damage(current_shield: int, damage: int, logs: list) -> tuple[int, int]:
        if damage <= 0:
            return 0, 0

        if current_shield >= damage:
            logs.append(f"🛡 Щит поглотил: {damage}")
            return damage, 0
        else:
            dmg_to_shield = current_shield
            dmg_to_hp = damage - current_shield

            if current_shield > 0:
                logs.append("💔 <b>ЩИТ ПРОБИТ!</b>")

            logs.append(f"🩸 Урон: <b>{dmg_to_hp}</b>")
            return dmg_to_shield, dmg_to_hp

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
            "is_dodged": ctx["is_dodged"],
            "is_parried": ctx["is_parried"],
            "is_counter": ctx["is_counter"],
            "lifesteal": ctx["lifesteal_amount"],
            "logs": ctx["logs"],
        }
