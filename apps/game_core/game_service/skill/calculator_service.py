from loguru import logger as log

from apps.common.schemas_dto import SkillDisplayDTO, SkillProgressDTO
from apps.game_core.resources.game_data.skill_library import BASE_MAX_XP, SKILL_RECIPES, TITLE_THRESHOLDS_PERCENT


class SkillCalculatorService:
    """
    Сервис для выполнения "чистых" вычислений, связанных с прогрессом навыков.

    Не взаимодействует с базой данных или внешними системами. Его задача —
    принимать DTO с прогрессом навыка и, на основе правил из `SKILL_RECIPES`,
    рассчитывать производные данные для отображения (звание, процент прогресса и т.д.).
    """

    @staticmethod
    def get_skill_display_info(progress_dto: SkillProgressDTO) -> SkillDisplayDTO:
        """
        Рассчитывает данные для отображения прогресса навыка "на лету".

        На основе общего опыта (`total_xp`) и правил из библиотеки навыков вычисляет:
        - Эффективный максимальный опыт (с учетом множителя).
        - Процент прогресса до эффективного максимума.
        - Звание, соответствующее текущему проценту.

        Args:
            progress_dto: DTO с данными о прогрессе навыка (`skill_key`, `total_xp`).

        Returns:
            DTO `SkillDisplayDTO` с рассчитанными данными для отображения.
        """
        skill_key = progress_dto.skill_key
        total_xp = progress_dto.total_xp
        log.debug(f"SkillCalculator | event=calculate_display_info skill='{skill_key}' total_xp={total_xp}")

        skill_info = SKILL_RECIPES.get(skill_key)
        multiplier = 1.0
        if skill_info and isinstance(skill_info, dict) and "xp_multiplier" in skill_info:
            xp_multiplier = skill_info["xp_multiplier"]
            if isinstance(xp_multiplier, (int, float)):
                multiplier = float(xp_multiplier)
            else:
                log.warning(
                    f"SkillCalculator | reason='Invalid xp_multiplier type' skill='{skill_key}' type='{type(xp_multiplier)}' using_default=1.0"
                )
        else:
            log.warning(f"SkillCalculator | reason='xp_multiplier not found' skill='{skill_key}' using_default=1.0")

        effective_max_xp = int(BASE_MAX_XP * multiplier)
        log.debug(f"SkillCalculator | effective_max_xp={effective_max_xp} skill='{skill_key}'")

        if effective_max_xp <= 0:
            percentage = 100.0 if total_xp > 0 else 0.0
            log.warning(
                f"SkillCalculator | reason='Effective max XP is zero or less' skill='{skill_key}' percentage={percentage}"
            )
        else:
            percentage = min((total_xp / effective_max_xp) * 100, 100.0)
        log.debug(f"SkillCalculator | percentage={percentage:.2f}% skill='{skill_key}'")

        current_title = "Новичок"
        for percent_threshold, title in sorted(TITLE_THRESHOLDS_PERCENT.items(), reverse=True):
            if percentage >= percent_threshold:
                current_title = title
                break
        log.debug(f"SkillCalculator | title='{current_title}' skill='{skill_key}'")

        display_dto = SkillDisplayDTO(
            skill_key=skill_key,
            title=current_title,
            percentage=round(percentage, 2),
            total_xp=total_xp,
            effective_max_xp=effective_max_xp,
        )
        log.debug(f"SkillCalculator | display_dto_created skill='{skill_key}'")
        return display_dto
