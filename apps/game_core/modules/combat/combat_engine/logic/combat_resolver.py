from apps.game_core.modules.combat.combat_engine.logic.math_core import MathCore
from apps.game_core.modules.combat.dto.combat_internal_dto import ActorStats
from apps.game_core.modules.combat.dto.combat_pipeline_dto import InteractionResultDTO, PipelineContextDTO

# ==============================================================================
# 2. LOGIC
# ==============================================================================

TRIGGER_RULES = {
    "ON_HIT": {"trigger_combo": {"chance": 0.25, "mutations": {"check_evasion": False, "check_crit": True}}},
    "ON_DODGE": {"trigger_counter_dodge": {"chance": 0.5, "mutations": {"enable_counter": True}}},
    "ON_DODGE_FAIL": {},
    "ON_PARRY": {},
    "ON_PARRY_FAIL": {},
    "ON_BLOCK": {},
    "ON_BLOCK_FAIL": {},
    "ON_CRIT": {},
    "ON_CRIT_FAIL": {},
}


class CombatResolver:
    """
    Stateless Math Engine.
    """

    @classmethod
    def resolve_exchange(
        cls, attacker_stats: ActorStats, defender_stats: ActorStats, context: PipelineContextDTO
    ) -> InteractionResultDTO:
        result = InteractionResultDTO()

        if not context.phases.run_calculator:
            return result

        # 1. Accuracy (Попали ли вообще?)
        if not cls._step_accuracy_roll(attacker_stats, context, result):
            return result

        # 2. Crit / Trigger Roll (Сработал ли спец-эффект оружия?)
        cls._step_crit_roll(attacker_stats, defender_stats, context, result)

        # 3. Evasion (Увернулся ли враг?)
        if cls._step_evasion_roll(attacker_stats, defender_stats, context, result):
            return result

        # 4. Parry (Спарировал?)
        if cls._step_parry_roll(attacker_stats, defender_stats, context, result):
            return result

        # 5. Block (Заблокировал?)
        if cls._step_block_roll(attacker_stats, defender_stats, context, result):
            return result

        # 6. Damage Calculation
        cls._step_calculate_damage(attacker_stats, defender_stats, context, result)

        return result

    @staticmethod
    def _step_accuracy_roll(atk_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO) -> bool:
        if not ctx.stages.check_accuracy:
            return True

        if ctx.flags.force.miss:
            res.is_miss = True
            res.tokens_awarded_defender.append("TEMPO")
            return False

        if ctx.flags.force.hit:
            CombatResolver._resolve_triggers(ctx, res, "ON_HIT")
            return True

        # Используем "accuracy" -> превратится в "{hand}_accuracy"
        base_acc = CombatResolver._get_offensive_val(atk_stats, ctx, "accuracy")
        multiplier = ctx.mods.accuracy_mult
        final_acc = base_acc * multiplier

        if not MathCore.check_chance(final_acc):
            res.is_miss = True
            res.tokens_awarded_defender.append("TEMPO")
            return False

        CombatResolver._resolve_triggers(ctx, res, "ON_HIT")
        return True

    @staticmethod
    def _step_evasion_roll(
        atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ) -> bool:
        if not ctx.stages.check_evasion:
            return False

        if ctx.flags.force.dodge:
            res.is_dodged = True
            res.tokens_awarded_defender.append("DODGE")
            CombatResolver._resolve_triggers(ctx, res, "ON_DODGE")
            CombatResolver._check_counter_attack(def_stats, ctx, res)
            return True

        if ctx.flags.force.hit_evasion:
            CombatResolver._resolve_triggers(ctx, res, "ON_DODGE_FAIL")
            return False

        # Access via .mods
        base_evasion = def_stats.mods.dodge_chance
        evasion_cap = def_stats.mods.dodge_cap
        anti_evasion = def_stats.mods.anti_dodge_chance

        final_chance = 0.0
        if ctx.flags.formula.evasion_halved:
            final_chance = (base_evasion * 0.5) - anti_evasion
            final_chance = min(final_chance, evasion_cap)
        elif ctx.flags.formula.ignore_evasion_cap:
            final_chance = base_evasion - anti_evasion
        elif ctx.flags.formula.zero_anti_evasion:
            final_chance = base_evasion
            final_chance = min(final_chance, evasion_cap)
        else:
            final_chance = base_evasion - anti_evasion
            final_chance = min(final_chance, evasion_cap)

        if final_chance <= 0:
            CombatResolver._resolve_triggers(ctx, res, "ON_DODGE_FAIL")
            return False

        if MathCore.check_chance(final_chance):
            res.is_dodged = True
            res.tokens_awarded_defender.append("DODGE")
            CombatResolver._resolve_triggers(ctx, res, "ON_DODGE")
            CombatResolver._check_counter_attack(def_stats, ctx, res)
            return True
        else:
            CombatResolver._resolve_triggers(ctx, res, "ON_DODGE_FAIL")
            return False

    @staticmethod
    def _step_parry_roll(
        atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ) -> bool:
        if not ctx.stages.check_parry:
            return False

        if ctx.flags.restriction.ignore_parry:
            CombatResolver._resolve_triggers(ctx, res, "ON_PARRY_FAIL")
            return False

        if ctx.flags.force.parry:
            res.is_parried = True
            res.tokens_awarded_defender.append("PARRY")
            CombatResolver._resolve_triggers(ctx, res, "ON_PARRY")
            if ctx.flags.mastery.medium_armor or ctx.flags.can_counter_on_parry:
                CombatResolver._check_counter_attack(def_stats, ctx, res)
            return True

        # Access via .mods
        parry_chance = def_stats.mods.parry_chance
        parry_cap = def_stats.mods.parry_cap

        final_chance = 0.0
        if ctx.flags.formula.parry_halved:
            final_chance = parry_chance * 0.5
            final_chance = min(final_chance, parry_cap)
        elif ctx.flags.formula.ignore_parry_cap:
            final_chance = parry_chance
        else:
            final_chance = parry_chance
            final_chance = min(final_chance, parry_cap)

        if final_chance > 0 and MathCore.check_chance(final_chance):
            res.is_parried = True
            res.tokens_awarded_defender.append("PARRY")
            CombatResolver._resolve_triggers(ctx, res, "ON_PARRY")
            if ctx.flags.mastery.medium_armor:
                mastery_chance = def_stats.skills.skill_medium_armor
                if MathCore.check_chance(mastery_chance):
                    CombatResolver._check_counter_attack(def_stats, ctx, res)
            elif ctx.flags.can_counter_on_parry:
                CombatResolver._check_counter_attack(def_stats, ctx, res)
            return True
        else:
            CombatResolver._resolve_triggers(ctx, res, "ON_PARRY_FAIL")
            return False

    @staticmethod
    def _step_block_roll(
        atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ) -> bool:
        if not ctx.stages.check_block:
            return False
        if ctx.flags.restriction.ignore_block:
            CombatResolver._resolve_triggers(ctx, res, "ON_BLOCK_FAIL")
            return False
        if ctx.flags.force.block:
            res.is_blocked = True
            res.tokens_awarded_defender.append("BLOCK")
            CombatResolver._resolve_triggers(ctx, res, "ON_BLOCK")
            return True

        # Access via .mods
        block_chance = def_stats.mods.shield_block_chance
        block_cap = def_stats.mods.shield_block_cap

        final_chance = 0.0
        if ctx.flags.formula.block_halved:
            final_chance = block_chance * 0.5
            final_chance = min(final_chance, block_cap)
        elif ctx.flags.formula.ignore_block_cap:
            final_chance = block_chance
        else:
            final_chance = min(block_chance, block_cap)

        if final_chance > 0 and MathCore.check_chance(final_chance):
            res.is_blocked = True
            res.tokens_awarded_defender.append("BLOCK")
            CombatResolver._resolve_triggers(ctx, res, "ON_BLOCK")
            return True

        if ctx.flags.mastery.shield_reflect and MathCore.check_chance(0.25):
            ctx.flags.state.partial_absorb_reflect = True

        CombatResolver._resolve_triggers(ctx, res, "ON_BLOCK_FAIL")
        return False

    @staticmethod
    def _step_crit_roll(
        atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ):
        if not ctx.stages.check_crit:
            return

        if ctx.flags.force.crit:
            res.is_crit = True
            CombatResolver._resolve_triggers(ctx, res, "ON_CRIT")
            return

        if ctx.flags.restriction.cannot_crit:
            CombatResolver._resolve_triggers(ctx, res, "ON_CRIT_FAIL")
            return

        is_magic = False
        elements = ["fire", "water", "air", "earth", "light", "darkness", "arcane", "nature"]
        for elem in elements:
            if getattr(ctx.flags.damage, elem, False):
                is_magic = True
                break

        if is_magic:
            my_crit_chance = atk_stats.mods.magical_crit_chance
        else:
            my_crit_chance = CombatResolver._get_offensive_val(atk_stats, ctx, "crit_chance")

        skill_multiplier = 1.0
        if ctx.flags.meta.weapon_class:
            skill_key = f"skill_{ctx.flags.meta.weapon_class}"
            skill_val = getattr(atk_stats.skills, skill_key, 0.0)
            skill_multiplier = 1.0 + (skill_val / 100.0)

        final_chance = my_crit_chance * skill_multiplier
        crit_cap = CombatResolver._get_offensive_val(atk_stats, ctx, "crit_cap")
        final_chance = min(final_chance, crit_cap)

        if final_chance > 0 and MathCore.check_chance(final_chance):
            res.is_crit = True
            CombatResolver._resolve_triggers(ctx, res, "ON_CRIT")
        else:
            CombatResolver._resolve_triggers(ctx, res, "ON_CRIT_FAIL")

    @staticmethod
    def _calculate_crit_multiplier(ctx: PipelineContextDTO) -> float:
        elements = ["fire", "water", "air", "earth", "light", "darkness", "arcane", "nature"]
        is_magic = any(getattr(ctx.flags.damage, elem, False) for elem in elements)
        if is_magic:
            return 3.0

        if ctx.flags.formula.crit_damage_boost:
            return ctx.mods.weapon_effect_value

        return 1.0

    @staticmethod
    def _step_calculate_damage(
        atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ) -> float:
        if not ctx.stages.calculate_damage:
            return 0.0

        if ctx.override_damage:
            min_d, max_d = ctx.override_damage
        else:
            base = CombatResolver._get_offensive_val(atk_stats, ctx, "damage_base")
            spread = CombatResolver._get_offensive_val(atk_stats, ctx, "damage_spread")

            if ctx.flags.damage.physical:
                base += atk_stats.mods.physical_damage_bonus

            min_d = base * (1.0 - spread)
            max_d = base * (1.0 + spread)

        raw_damage = MathCore.random_range(min_d, max_d)
        total_damage = 0.0

        crit_multiplier = 1.0
        if res.is_crit:
            crit_multiplier = CombatResolver._calculate_crit_multiplier(ctx)
            res.crit_mult = crit_multiplier

        # --- PHYSICAL ---
        if ctx.flags.damage.physical:
            phys_dmg = raw_damage

            if res.is_crit:
                phys_dmg *= crit_multiplier
                heavy_skill = def_stats.skills.skill_heavy_armor
                if heavy_skill > 0:
                    bonus_part = crit_multiplier - 1.0
                    if bonus_part > 0:
                        phys_dmg *= 1.0 - (heavy_skill * 0.2)

            phys_res_pct = def_stats.mods.physical_resistance
            phys_pen_pct = CombatResolver._get_offensive_val(atk_stats, ctx, "penetration")
            mitigation_pct = max(0.0, phys_res_pct - phys_pen_pct)
            phys_dmg *= 1.0 - mitigation_pct

            armor_flat = def_stats.mods.damage_reduction_flat
            phys_dmg = max(0.0, phys_dmg - armor_flat)

            if res.is_crit:
                res.tokens_awarded_attacker.append("CRIT_TOKEN")
            else:
                res.tokens_awarded_attacker.append("HIT_TOKEN")

            total_damage += phys_dmg

        # --- PURE ---
        if ctx.flags.damage.pure:
            pure_dmg = raw_damage
            if res.is_crit:
                pure_dmg *= 1.5
            total_damage += pure_dmg

        # --- ELEMENTAL ---
        elements = ["fire", "water", "air", "earth", "light", "darkness", "arcane", "nature"]
        for elem in elements:
            if getattr(ctx.flags.damage, elem, False):
                elem_dmg = raw_damage

                if res.is_crit:
                    elem_dmg *= crit_multiplier

                resist_pct = getattr(def_stats.mods, f"{elem}_resistance", 0.0)
                pen_pct = 0.0

                if atk_stats.mods.magical_penetration > 0:
                    pen_pct = atk_stats.mods.magical_penetration

                mitigation_pct = max(0.0, resist_pct - pen_pct)
                elem_dmg *= 1.0 - mitigation_pct
                total_damage += elem_dmg

        # 3. ОБЩИЕ МОДИФИКАТОРЫ
        if ctx.flags.state.hit_index > 0:
            heavy_skill = def_stats.skills.skill_heavy_armor
            if heavy_skill > 0:
                total_damage *= 1.0 - (heavy_skill * 0.5)

        if ctx.flags.state.partial_absorb_reflect:
            absorbed = total_damage * 0.40
            total_damage -= absorbed
            res.reflected_damage += int(absorbed)

        total_damage = max(0.0, total_damage)
        res.damage_final = int(total_damage)
        return total_damage

    @staticmethod
    def _check_counter_attack(def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO):
        if not ctx.can_counter:
            return

        base_chance = def_stats.mods.counter_attack_chance
        cap = def_stats.mods.counter_attack_cap
        counter_chance = min(base_chance, cap)

        if res.is_dodged and ctx.flags.mastery.light_armor and MathCore.check_chance(0.50):
            skill_lvl = def_stats.skills.skill_light_armor
            mult = 1.0 + skill_lvl
            counter_chance *= mult

        if ctx.flags.enable_counter:
            counter_chance += 0.20

        if counter_chance > 0 and MathCore.check_chance(counter_chance):
            res.is_counter = True
            res.tokens_awarded_defender.append("COUNTER")

    @staticmethod
    def _resolve_triggers(ctx: PipelineContextDTO, res: InteractionResultDTO, step_key: str):
        rules_book = TRIGGER_RULES.get(step_key)
        if not rules_book or not isinstance(rules_book, dict):
            return

        for trigger_name, rule_data in rules_book.items():
            if not getattr(ctx.triggers, trigger_name, False):
                continue

            raw_chance = rule_data.get("chance", 0.0)
            chance = float(raw_chance) if isinstance(raw_chance, (int, float)) else 0.0

            if not MathCore.check_chance(chance):
                continue

            for key, value in rule_data.get("mutations", {}).items():
                if hasattr(ctx.stages, key):
                    setattr(ctx.stages, key, value)
                elif hasattr(ctx.flags, key):
                    setattr(ctx.flags, key, value)

    @staticmethod
    def _get_offensive_val(stats: ActorStats, ctx: PipelineContextDTO, stat_name: str) -> float:
        """
        Достает значение стата из нужной руки (с префиксом).
        """
        current_source = ctx.flags.meta.source_type

        prefix = ""
        if current_source == "off_hand":
            prefix = "off_hand_"
        elif current_source == "main_hand":
            prefix = "main_hand_"

        full_stat_name = f"{prefix}{stat_name}"

        if not prefix and current_source == "magic":
            full_stat_name = f"magical_{stat_name}"

        # Access via .mods
        val = getattr(stats.mods, full_stat_name, 0.0)
        return val
