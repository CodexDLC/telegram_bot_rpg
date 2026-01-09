from apps.game_core.resources.game_data.skills.schemas import SkillCategory, SkillDTO, SkillGroup

TRADE_SKILLS = [
    SkillDTO(
        skill_key="accounting",
        name_en="Accounting",
        name_ru="Бухгалтерия",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.TRADE,
        stat_weights={"intelligence": 2, "luck": 2},  # Dual 2+2
        rate_mod=1.0,
        wall_mod=1.0,
    ),
    SkillDTO(
        skill_key="brokerage",
        name_en="Brokerage",
        name_ru="Посредничество",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.TRADE,
        stat_weights={"charisma": 2, "luck": 1, "intelligence": 1},
        rate_mod=1.0,
        wall_mod=1.0,
    ),
    SkillDTO(
        skill_key="contracts",
        name_en="Contracts",
        name_ru="Договоры",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.TRADE,
        stat_weights={"intelligence": 2, "charisma": 1, "luck": 1},
        rate_mod=1.0,
        wall_mod=1.0,
    ),
    SkillDTO(
        skill_key="trade_relations",
        name_en="Trade Relations",
        name_ru="Торговые связи",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.TRADE,
        stat_weights={"charisma": 2, "luck": 2},  # Dual 2+2
        rate_mod=1.0,
        wall_mod=1.0,
    ),
]
