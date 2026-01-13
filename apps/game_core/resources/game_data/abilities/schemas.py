from typing import Any

from pydantic import BaseModel, Field


class AbilityCostDTO(BaseModel):
    """
    Стоимость абилки (Gift).
    """

    energy: int = 0  # Энергия (мана)
    gift: int = 0  # Токен Дара
    hp: int = 0  # Здоровье (кровавая магия)


class AbilityConfigDTO(BaseModel):
    """
    Конфигурация абилки (Gift Ability).
    Источник: Дар (магия, особые способности).
    """

    ability_id: str
    name_ru: str
    description_ru: str

    # === COST ===
    cost: AbilityCostDTO = Field(default_factory=AbilityCostDTO)

    # === TARGETING ===
    # Тип действия (instant, reaction, passive)
    type: str = "instant"
    # Цель (self, single_enemy, all_enemies, multi_enemy)
    target: str = "single_enemy"
    # Количество целей (если target="multi_enemy" или для ограничения all_enemies)
    target_count: int = 1

    # === INSTRUCTIONS (Для AbilityService) ===

    # Прямое изменение статов (RAW)
    # Пример: {"magical_damage_bonus": "*2.0"}
    raw_mutations: dict[str, str] | None = None

    # Изменение флагов пайплайна
    # Пример: {"damage.fire": True}
    pipeline_mutations: dict[str, Any] | None = None

    # Активация триггеров (ссылки на TRIGGER_RULES)
    triggers: list[str] | None = None

    # Условные триггеры
    conditional_triggers: dict[str, list[str]] | None = None

    # Полная замена урона
    override_damage: tuple[float, float] | None = None

    # Эффекты, накладываемые ПОСЛЕ расчета (Post-Calc)
    post_calc_effects: list[dict[str, Any]] | None = None
