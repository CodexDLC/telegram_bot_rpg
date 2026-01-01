from typing import Any

from pydantic import BaseModel, Field


class CombatActorReadDTO(BaseModel):
    """
    Универсальное DTO для превращения Temp Context в боевого Актера.
    Используется CombatLifecycleService для инициализации сессии.
    Работает как фильтр: отсекает лишние данные из Temp Cache.
    """

    # 1. МАТЕМАТИЧЕСКАЯ МОДЕЛЬ (v:raw)
    # Это то, что собрал Ассемблер. Здесь лежат все источники статов.
    math_model: dict[str, Any] = Field(
        alias="math_model", description="Матрица источников (attributes и modifiers) в формате RBC v2.0"
    )

    # 2. ТЕКУЩЕЕ СОСТОЯНИЕ (vitals)
    # ХП и Энергия. Если там -1, значит сервис должен рассчитать максимум.
    vitals: dict[str, Any] = Field(default_factory=lambda: {"hp_current": -1, "energy_current": -1})

    # 3. ОСНАЩЕНИЕ (loadout)
    # Список активных скиллов, абилок и предметов на поясе.
    loadout: dict[str, list[Any]] = Field(default_factory=lambda: {"belt": [], "skills": [], "abilities": []})

    # 4. ПАСПОРТНЫЕ ДАННЫЕ (meta)
    # Информация для отображения и логики (кто это, как зовут).
    meta: dict[str, Any] = Field(description="Мета-данные: entity_id, type (player/monster), name, team")

    # Важно: разрешаем наличие других полей в JSON (например, core_stats),
    # но игнорируем их при чтении в эту модель.
    model_config = {"populate_by_name": True, "extra": "ignore"}
