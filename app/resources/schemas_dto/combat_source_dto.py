from pydantic import BaseModel, Field


class StatSourcesDTO(BaseModel):
    """
    Детализация одного стата по источникам.
    Это 'Значение' в словаре статов.
    """

    base: int = 0  # Родные статы (распределенные)
    equipment: int = 0  # Сумма со всего шмота
    skills: int = 0  # Сумма пассивок

    # Баффы храним отдельно, так как их часто надо снимать по ID
    # Пример: {"rage_potion": 5, "cleric_blessing": 10}
    buffs: dict[str, int] = Field(default_factory=dict)

    @property
    def total(self) -> int:
        """Вычисляет итоговое значение на лету."""
        return self.base + self.equipment + self.skills + sum(self.buffs.values())


class CombatComplexStatsDTO(BaseModel):
    """
    ПОЛНЫЙ реестр статов для Боевой Сессии (Redis).
    Здесь всё разложено по источникам для гибкости.
    """

    # --- 0. Ресурсы ---
    hp_max: StatSourcesDTO = Field(default_factory=StatSourcesDTO)

    # --- 1. Первичные (Primary Stats) ---
    strength: StatSourcesDTO = Field(default_factory=StatSourcesDTO)
    agility: StatSourcesDTO = Field(default_factory=StatSourcesDTO)
    endurance: StatSourcesDTO = Field(default_factory=StatSourcesDTO)
    intelligence: StatSourcesDTO = Field(default_factory=StatSourcesDTO)
    wisdom: StatSourcesDTO = Field(default_factory=StatSourcesDTO)
    men: StatSourcesDTO = Field(default_factory=StatSourcesDTO)
    perception: StatSourcesDTO = Field(default_factory=StatSourcesDTO)
    charisma: StatSourcesDTO = Field(default_factory=StatSourcesDTO)
    luck: StatSourcesDTO = Field(default_factory=StatSourcesDTO)

    # --- 2. Боевые параметры (Offense & Defense) ---
    # Храним в условных единицах (например, 5 = 5%)
    phys_crit_chance: StatSourcesDTO = Field(default_factory=StatSourcesDTO)
    magic_crit_chance: StatSourcesDTO = Field(default_factory=StatSourcesDTO)
    dodge_chance: StatSourcesDTO = Field(default_factory=StatSourcesDTO)

    # Урон оружия (Min/Max) тоже раскладываем по источникам!
    # base = кулак, equipment = меч, skills = пассивка "+10 урона"
    phys_damage_min: StatSourcesDTO = Field(default_factory=StatSourcesDTO)
    phys_damage_max: StatSourcesDTO = Field(default_factory=StatSourcesDTO)

    # --- 3. Зональная Броня (Armor per Zone) ---
    # base = кожа/чешуя, equipment = доспех
    armor_head: StatSourcesDTO = Field(default_factory=StatSourcesDTO)
    armor_chest: StatSourcesDTO = Field(default_factory=StatSourcesDTO)
    armor_belly: StatSourcesDTO = Field(default_factory=StatSourcesDTO)
    armor_legs: StatSourcesDTO = Field(default_factory=StatSourcesDTO)
    armor_feet: StatSourcesDTO = Field(default_factory=StatSourcesDTO)

    # Природная броня (работает поверх зон)
    armor_natural: StatSourcesDTO = Field(default_factory=StatSourcesDTO)

    # Щит (Базовая сила блока)
    shield_mitigation: StatSourcesDTO = Field(default_factory=StatSourcesDTO)
