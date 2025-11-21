from typing import Any

from app.resources.game_data.stats_formulas import DEFAULT_VALUES, MODIFIER_RULES
from app.resources.schemas_dto.character_dto import CharacterStatsReadDTO
from app.resources.schemas_dto.modifier_dto import CharacterModifiersSaveDto


class ModifiersCalculatorService:
    """
    Сервис динамического расчета характеристик.
    Работает по принципу Data-Driven: логика расчета вынесена в конфиг stats_formulas.py.
    """

    @staticmethod
    def calculate_all_modifiers_for_stats(base_stats: CharacterStatsReadDTO) -> CharacterModifiersSaveDto:
        """
        Проходит циклом по словарю правил и собирает DTO модификаторов.
        """
        # 1. Подготавливаем словарь для результата
        # Начинаем с дефолтных значений (констант)
        result_data: dict[str, Any] = DEFAULT_VALUES.copy()

        # 2. Основной цикл расчета
        for target_field, dependencies in MODIFIER_RULES.items():
            total_value = 0.0

            # Проходим по всем статам, от которых зависит это поле
            # (обычно один, но может быть и сумма: Luck + Charisma)
            if isinstance(dependencies, dict):
                for stat_name, coefficient in dependencies.items():
                    # Безопасно достаем значение стата из DTO (например, base_stats.strength)
                    stat_value = getattr(base_stats, stat_name, 0)
                    total_value += stat_value * coefficient

            # Если поле уже было (например, в дефолтах), прибавляем к нему
            # Если нет — записываем
            current = result_data.get(target_field, 0)
            result_data[target_field] = current + total_value

        # 3. Валидация и создание DTO
        # Pydantic сам преобразует float в int там, где поле объявлено как int (например hp_max)
        return CharacterModifiersSaveDto(**result_data)
