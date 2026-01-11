# from typing import Any
#
# from apps.common.schemas_dto import CharacterModifiersSaveDto, CharacterStatsReadDTO
# from apps.game_core.resources.game_data.stats_formulas import DEFAULT_VALUES, MODIFIER_RULES
#
#
# class ModifiersCalculatorService:
#     """
#     Сервис для динамического расчета производных характеристик (модификаторов) персонажа.
#
#     Логика расчета определяется конфигурацией в `stats_formulas.py`,
#     что позволяет легко изменять формулы без изменения кода сервиса.
#     """
#
#     @staticmethod
#     def calculate_all_modifiers_for_stats(base_stats: CharacterStatsReadDTO) -> CharacterModifiersSaveDto:
#         """
#         Рассчитывает все модификаторы персонажа на основе его базовых характеристик.
#
#         Использует правила, определенные в `MODIFIER_RULES`, для вычисления
#         значений каждого модификатора.
#
#         Args:
#             base_stats: DTO, содержащий базовые характеристики персонажа.
#
#         Returns:
#             DTO `CharacterModifiersSaveDto`, содержащий все рассчитанные модификаторы.
#         """
#         result_data: dict[str, Any] = DEFAULT_VALUES.copy()
#
#         for target_field, dependencies in MODIFIER_RULES.items():
#             total_value = 0.0
#             if isinstance(dependencies, dict):
#                 for stat_name, coefficient in dependencies.items():
#                     stat_value = getattr(base_stats, stat_name, 0)
#                     total_value += stat_value * coefficient
#
#             current = result_data.get(target_field, 0)
#             result_data[target_field] = current + total_value
#
#         return CharacterModifiersSaveDto(**result_data)
