from apps.game_core.modules.combat.dto.combat_internal_dto import ActorSnapshot, ActorStats
from pydantic import ValidationError

from apps.common.schemas_dto.modifier_dto import CombatModifiersDTO, CombatSkillsDTO
from apps.game_core.system.calculators.stats_waterfall_calculator import StatsWaterfallCalculator


class StatsEngine:
    """
    Движок расчета характеристик (Stats Engine).
    Отвечает за актуализацию ActorStats на основе ActorSnapshot.raw.
    Использует StatsWaterfallCalculator для математики.
    """

    @staticmethod
    def ensure_stats(actor: ActorSnapshot) -> None:
        """
        Гарантирует, что у актера есть актуальные ActorStats.
        Если stats нет или они 'грязные' -> пересчитывает.
        """
        if actor.stats is None:
            # Полный пересчет (первый запуск)
            StatsEngine._recalculate_full(actor)
        elif actor.dirty_stats:
            # Частичный пересчет (оптимизация)
            # Пока делаем полный, так как Waterfall быстрый
            StatsEngine._recalculate_full(actor)

        # Если stats есть и dirty_stats пуст -> ничего не делаем (используем кэш)

    @staticmethod
    def _recalculate_full(actor: ActorSnapshot) -> None:
        """
        Полный цикл пересчета.
        """
        # 1. Подготовка данных для калькулятора
        raw_data = actor.raw.model_dump()

        # 2. Расчет (Waterfall)
        # Возвращает плоский словарь модификаторов и словарь формул
        calculated_mods, explanation = StatsWaterfallCalculator.calculate_waterfall(raw_data)

        # 3. Сборка ActorStats
        # Берем скиллы из Snapshot (они не считаются в Waterfall, а просто копируются)
        skills_data = actor.skills

        # Создаем DTO
        # Используем from_flat_dict или конструктор напрямую?
        # Так как у нас есть четкое разделение (mods vs skills), лучше напрямую.

        # Важно: calculated_mods может содержать лишние поля (от bridge),
        # но Pydantic (CombatModifiersDTO) их отфильтрует, если extra='ignore'.
        # У нас extra='forbid' в CombatModifiersDTO, поэтому надо быть аккуратным.
        # Но Waterfall возвращает только то, что мы просили (плюс derived).
        # Если derived ключи совпадают с полями DTO -> все ок.

        # Чтобы избежать ошибок валидации, можно профильтровать calculated_mods
        # по полям CombatModifiersDTO. Но это дорого.
        # Доверимся тому, что Waterfall возвращает корректные ключи.

        try:
            mods_dto = CombatModifiersDTO(**calculated_mods)
        except (ValidationError, TypeError):
            # Fallback: если Waterfall вернул мусор, фильтруем вручную
            valid_keys = CombatModifiersDTO.model_fields.keys()
            filtered_mods = {k: v for k, v in calculated_mods.items() if k in valid_keys}
            mods_dto = CombatModifiersDTO(**filtered_mods)

        skills_dto = CombatSkillsDTO(**skills_data)

        actor.stats = ActorStats(mods=mods_dto, skills=skills_dto)

        # 4. Сохраняем объяснения (для дебага/логов)
        actor.explanation = explanation

        # 5. Сбрасываем флаги
        actor.dirty_stats.clear()
