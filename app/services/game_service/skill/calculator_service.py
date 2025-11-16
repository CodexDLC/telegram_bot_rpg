# app/services/game_service/skill/calculator_service.py
from loguru import logger as log
from app.resources.game_data.skill_library import (
    SKILL_RECIPES,
    TITLE_THRESHOLDS_PERCENT,
    BASE_MAX_XP
)
from app.resources.schemas_dto.skill import SkillProgressDTO, SkillDisplayDTO


class SkillCalculatorService:
    """
    Сервис для вычислений, связанных с прогрессом навыков.

    Этот сервис является "чистым" - он не взаимодействует с базой данных
    или внешними системами. Его единственная задача - принимать DTO с
    прогрессом навыка и, на основе правил из "Библиотеки" (`skill_library`),
    рассчитывать производные данные для отображения (звание, процент и т.д.).
    """

    @staticmethod
    def get_skill_display_info(progress_dto: SkillProgressDTO) -> SkillDisplayDTO:
        """
        Рассчитывает "на лету" данные для отображения прогресса навыка.

        На основе общего опыта (`total_xp`) и правил из библиотеки вычисляет:
        - Эффективный максимальный опыт (с учетом множителя).
        - Процент прогресса до эффективного максимума.
        - Звание, соответствующее текущему проценту.

        Args:
            progress_dto (SkillProgressDTO): DTO с данными о прогрессе навыка
                                             (skill_key, total_xp).

        Returns:
            SkillDisplayDTO: DTO с рассчитанными данными для отображения.
        """
        skill_key = progress_dto.skill_key
        total_xp = progress_dto.total_xp
        log.debug(f"Расчет display info для навыка '{skill_key}' с total_xp={total_xp}.")

        # Шаг 1: Получение множителя опыта из библиотеки.
        skill_info = SKILL_RECIPES.get(skill_key)
        if not skill_info or "xp_multiplier" not in skill_info:
            log.warning(f"Не найден 'xp_multiplier' для '{skill_key}' в SKILL_RECIPES. Используется множитель 1.0.")
            multiplier = 1.0
        else:
            multiplier = skill_info["xp_multiplier"]
        log.debug(f"  - Множитель опыта (multiplier): {multiplier}")

        # Шаг 2: Расчет эффективного максимального опыта.
        effective_max_xp = int(BASE_MAX_XP * multiplier)
        log.debug(f"  - Эффективный максимум XP (effective_max_xp): {effective_max_xp}")

        # Шаг 3: Расчет процента прогресса.
        if effective_max_xp <= 0:
            # Защита от деления на ноль или отрицательного значения.
            percentage = 100.0 if total_xp > 0 else 0.0
            log.warning(f"  - effective_max_xp равен {effective_max_xp}. Процент установлен в {percentage}%.")
        else:
            # Процент не может быть больше 100.
            percentage = min((total_xp / effective_max_xp) * 100, 100.0)
        log.debug(f"  - Процент прогресса (percentage): {percentage:.2f}%")

        # Шаг 4: Определение звания на основе процента.
        current_title = "Новичок"  # Звание по умолчанию
        # Идем по отсортированным порогам (90, 70, 40...)
        for percent_threshold, title in sorted(TITLE_THRESHOLDS_PERCENT.items(), reverse=True):
            if percentage >= percent_threshold:
                current_title = title
                break
        log.debug(f"  - Присвоенное звание (title): '{current_title}'")

        # Формируем и возвращаем DTO для отображения.
        display_dto = SkillDisplayDTO(
            skill_key=skill_key,
            title=current_title,
            percentage=round(percentage, 2),
            total_xp=total_xp,
            effective_max_xp=effective_max_xp
        )
        log.debug(f"Сформирован SkillDisplayDTO: {display_dto.model_dump_json()}")
        return display_dto
