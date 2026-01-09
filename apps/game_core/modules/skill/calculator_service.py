# from loguru import logger as log
#
# from apps.common.schemas_dto import SkillDisplayDTO, SkillProgressDTO
# from apps.game_core.resources.game_data.skills.skill_library import BASE_MAX_XP,
#
# # TODO: [LEGACY] ЗАГЛУШКА ДЛЯ СТАРОЙ СИСТЕМЫ
# # Ранее множители брались из SKILL_RECIPES.
# # В новой системе скиллов (Skill Library 2.0) эта логика будет изменена.
# # Оставлено как заглушка (Stub) для поддержания работоспособности калькулятора.
# _LEGACY_XP_MULTIPLIERS = {
#     "mining": 1.0,
#     "herbalism": 1.0,
#     "skinning": 1.0,
#     "woodcutting": 1.0,
#     "hunting": 1.0,
#     "archaeology": 1.0,
#     "gathering": 1.0,
#     "alchemy": 1.5,
#     "science": 1.5,
#     "weapon_craft": 2.0,
#     "armor_craft": 2.0,
#     "jewelry_craft": 2.0,
#     "artifact_craft": 2.5,
#     "accounting": 1.0,
#     "brokerage": 1.0,
#     "contracts": 1.0,
#     "trade_relations": 1.0,
#     "leadership": 1.0,
#     "organization": 1.0,
#     "team_spirit": 1.0,
#     "egoism": 1.0,
#     "advanced_melee_combat": 5.0,
#     "advanced_ranged_combat": 5.0,
# }
#
#
# class SkillCalculatorService:
#     """
#     Сервис для выполнения "чистых" вычислений, связанных с прогрессом навыков.
#
#     Не взаимодействует с базой данных или внешними системами. Его задача —
#     принимать DTO с прогрессом навыка и, на основе правил (теперь локальных заглушек),
#     рассчитывать производные данные для отображения (звание, процент прогресса и т.д.).
#     """
#
#     @staticmethod
#     def get_skill_display_info(progress_dto: SkillProgressDTO) -> SkillDisplayDTO:
#         """
#         Рассчитывает данные для отображения прогресса навыка "на лету".
#
#         На основе общего опыта (`total_xp`) и локальных правил вычисляет:
#         - Эффективный максимальный опыт (с учетом множителя).
#         - Процент прогресса до эффективного максимума.
#         - Звание, соответствующее текущему проценту.
#
#         Args:
#             progress_dto: DTO с данными о прогрессе навыка (`skill_key`, `total_xp`).
#
#         Returns:
#             DTO `SkillDisplayDTO` с рассчитанными данными для отображения.
#         """
#         skill_key = progress_dto.skill_key
#         total_xp = progress_dto.total_xp
#         log.debug(f"SkillCalculator | event=calculate_display_info skill='{skill_key}' total_xp={total_xp}")
#
#         # Используем локальную заглушку вместо SKILL_RECIPES
#         multiplier = _LEGACY_XP_MULTIPLIERS.get(skill_key, 1.0)
#
#         effective_max_xp = int(BASE_MAX_XP * multiplier)
#         log.debug(f"SkillCalculator | effective_max_xp={effective_max_xp} skill='{skill_key}'")
#
#         if effective_max_xp <= 0:
#             percentage = 100.0 if total_xp > 0 else 0.0
#             log.warning(
#                 f"SkillCalculator | reason='Effective max XP is zero or less' skill='{skill_key}' percentage={percentage}"
#             )
#         else:
#             percentage = min((total_xp / effective_max_xp) * 100, 100.0)
#         log.debug(f"SkillCalculator | percentage={percentage:.2f}% skill='{skill_key}'")
#
#         current_title = "Новичок"
#         for percent_threshold, title in sorted(TITLE_THRESHOLDS_PERCENT.items(), reverse=True):
#             if percentage >= percent_threshold:
#                 current_title = title
#                 break
#         log.debug(f"SkillCalculator | title='{current_title}' skill='{skill_key}'")
#
#         display_dto = SkillDisplayDTO(
#             skill_key=skill_key,
#             title=current_title,
#             percentage=round(percentage, 2),
#             total_xp=total_xp,
#             effective_max_xp=effective_max_xp,
#         )
#         log.debug(f"SkillCalculator | display_dto_created skill='{skill_key}'")
#         return display_dto
