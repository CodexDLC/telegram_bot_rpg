# app/services/game_service/skill/calculator_service.py
import logging


# Импортируем "Библиотеку" как источник правил
from app.resources.game_data.skill_library import (
    SKILL_RECIPES,
    TITLE_THRESHOLDS_PERCENT,
    BASE_MAX_XP
)
# Импортируем DTO "вывода"

# Импортируем DTO "ввода" (из которого берем total_xp)
from app.resources.schemas_dto.skill import SkillProgressDTO, SkillDisplayDTO

log = logging.getLogger(__name__)


class SkillCalculatorService:
    """
    Сервис, отвечающий за РАСЧЕТ И ОТОБРАЖЕНИЕ прогресса навыков.
    Он не лезет в БД. Он просто "считает" на основе DTO и Библиотеки.
    """

    @staticmethod
    def get_skill_display_info(
            progress_dto: SkillProgressDTO
    ) -> SkillDisplayDTO:
        """
        Рассчитывает "на лету" звание и процент
        на основе DTO прогресса и Библиотеки.
        """

        skill_key = progress_dto.skill_key
        total_xp = progress_dto.total_xp

        # 1. Получаем Мультиплеер (Множитель) из Библиотеки
        skill_info = SKILL_RECIPES.get(skill_key)
        if not skill_info or "xp_multiplier" not in skill_info:
            log.warning(f"Нет 'xp_multiplier' для {skill_key} в skill_library.py! Используем 1.0")
            multiplier = 1.0
        else:
            multiplier = skill_info["xp_multiplier"]

        # 2. Рассчитываем ЭФФЕКТИВНЫЙ максимум XP (Твоя идея)
        effective_max_xp = int(BASE_MAX_XP * multiplier)

        # 3. Рассчитываем Процент
        if effective_max_xp == 0:  # (Защита от деления на ноль)
            percentage = 100.0
        else:
            percentage = min((total_xp / effective_max_xp) * 100, 100.0)

        # 4. Рассчитываем Звание (Нелинейная логика)
        current_title = "Неизвестно"  # (Заглушка, если total_xp < 0)

        # Идем по "Библиотеке" (90, 70, 40...)
        for percent_threshold, title in TITLE_THRESHOLDS_PERCENT.items():
            if percentage >= percent_threshold:
                current_title = title
                break

        return SkillDisplayDTO(
            skill_key=skill_key,
            title=current_title,
            percentage=round(percentage, 2),
            total_xp=total_xp,
            effective_max_xp=effective_max_xp
        )