from typing import Any

from pydantic import BaseModel, Field


class FeintCostDTO(BaseModel):
    """
    Стоимость финта (Tactical).
    """

    # Стоимость в тактических токенах.
    # Примеры:
    # {"crit": 1, "hit": 2} -> Требует 1 токен крита и 2 токена хита.
    # {"any": 5} -> Требует 5 любых токенов (списание по дефолтному приоритету).
    tactics: dict[str, int] = Field(default_factory=dict)

    stamina: int = 0  # Выносливость (для instant финтов, будущее)


class FeintConfigDTO(BaseModel):
    """
    Конфигурация финта (Tactical Move).
    Источник: Владение оружием, стойка, опыт.
    """

    feint_id: str
    name_ru: str
    description_ru: str

    # === COST ===
    cost: FeintCostDTO = Field(default_factory=FeintCostDTO)

    # === TARGETING ===
    # Финты обычно бьют по 1 цели (модификатор атаки), но могут быть исключения (instant)
    target_count: int = 1

    # === INSTRUCTIONS (Для AbilityService) ===

    # Прямое изменение статов (RAW)
    raw_mutations: dict[str, str] | None = None

    # Изменение флагов пайплайна
    pipeline_mutations: dict[str, Any] | None = None

    # Активация триггеров (ссылки на TRIGGER_RULES)
    triggers: list[str] | None = None

    # Условные триггеры
    conditional_triggers: dict[str, list[str]] | None = None

    # Полная замена урона
    override_damage: tuple[float, float] | None = None
