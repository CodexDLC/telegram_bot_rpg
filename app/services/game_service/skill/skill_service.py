# app/services/game_service/skill/skill_service.py

from loguru import logger as log

from app.resources.schemas_dto.character_dto import CharacterStatsReadDTO
from app.services.game_service.skill.rate_service import calculate_rates_data
from database.db_contract.i_characters_repo import ICharacterStatsRepo
from database.db_contract.i_skill_repo import ISkillProgressRepo, ISkillRateRepo


class CharacterSkillsService:
    """
    Фасад (Координатор) для управления бизнес-логикой навыков.
    """

    def __init__(self, stats_repo: ICharacterStatsRepo, rate_repo: ISkillRateRepo, progress_repo: ISkillProgressRepo):
        self._stats_repo = stats_repo
        self._rate_repo = rate_repo
        self._progress_repo = progress_repo
        log.debug(f"{self.__class__.__name__} инициализирован с репозиториями.")

    async def finalize_tutorial_stats(
        self, character_id: int, bonus_stats: dict[str, int]
    ) -> CharacterStatsReadDTO | None:
        """Финализирует распределение очков после туториала."""
        log.info(f"Начало финализации статов туториала для character_id={character_id}")

        # 1. Применение статов
        final_stats_dto = await self._stats_repo.add_stats(character_id, bonus_stats)
        if not final_stats_dto:
            return None

        # 2. Инициализация навыков
        await self._progress_repo.initialize_all_base_skills(character_id)

        # 3. Расчет БСО
        rates_data = calculate_rates_data(character_id, final_stats_dto)
        await self._rate_repo.upsert_skill_rates(rates_data)

        return final_stats_dto

    async def register_action_xp(
        self, char_id: int, item_subtype: str, outcome: str, custom_base: int | None = None
    ) -> None:
        """
        Универсальный начислитель опыта для ОДИНОЧНЫХ действий (Крафт, Сбор).
        НЕ ИСПОЛЬЗУЕТСЯ В БОЮ (там пакетная обработка).
        """
        from app.resources.game_data.xp_rules import BASE_ACTION_XP, OUTCOME_MULTIPLIERS, XP_SOURCE_MAP

        skill_key = XP_SOURCE_MAP.get(item_subtype)
        if not skill_key:
            return

        outcome_mult = OUTCOME_MULTIPLIERS.get(outcome, 0.0)
        if outcome_mult == 0:
            return

        # Получаем рейты (можно оптимизировать кэшированием)
        rates = await self._rate_repo.get_all_skill_rates(char_id)

        xp_rate_val = 0
        for r in rates:
            if r.skill_key == skill_key:
                xp_rate_val = r.xp_per_tick
                break

        base = custom_base or BASE_ACTION_XP
        # Формула: (Base * Outcome) * (1 + Rate / 100)
        efficiency_mod = 1.0 + (xp_rate_val / 100.0)
        final_xp = int((base * outcome_mult) * efficiency_mod)

        if final_xp > 0:
            await self._progress_repo.add_skill_xp(char_id, skill_key, final_xp)
            log.info(f"Single XP: {char_id} +{final_xp} xp to '{skill_key}' (Action: {item_subtype})")

    async def apply_combat_xp_batch(self, char_id: int, xp_buffer: dict[str, int]) -> None:
        """
        🔥 ПАКЕТНАЯ ОБРАБОТКА ОПЫТА ПОСЛЕ БОЯ.
        Принимает словарь {skill_key: raw_points}, накопленный в Redis.
        Умножает на рейты и пишет в БД.
        """
        if not xp_buffer:
            return

        log.debug(f"Слив буфера опыта для char_id={char_id}: {xp_buffer}")

        # 1. Получаем все рейты персонажа ОДНИМ запросом
        rates = await self._rate_repo.get_all_skill_rates(char_id)
        rates_map = {r.skill_key: r.xp_per_tick for r in rates}

        # 2. Итерируемся по накопленным навыкам
        for skill_key, raw_points in xp_buffer.items():
            if raw_points <= 0:
                continue

            # Достаем рейт (эффективность)
            rate_val = rates_map.get(skill_key, 0)  # Если рейта нет (баг?), считаем как 0% бонус

            # Формула: НакопленныеОчки * (1 + Эффективность/100)
            # Пример: Набил 200 очков мечом. Сила дает +50% рейта. Итог: 300 XP.
            efficiency_mod = 1.0 + (rate_val / 100.0)
            final_xp = int(raw_points * efficiency_mod)

            if final_xp > 0:
                # Пишем в БД
                await self._progress_repo.add_skill_xp(char_id, skill_key, final_xp)
                # TODO: Тут будет вызов check_level_up(char_id, skill_key)

        log.info(f"Боевой опыт для {char_id} успешно начислен.")
