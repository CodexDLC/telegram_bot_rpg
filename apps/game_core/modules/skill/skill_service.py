# from loguru import logger as log
#
# from apps.common.database.db_contract.i_characters_repo import ICharacterStatsRepo
# from apps.common.database.db_contract.i_skill_repo import ISkillProgressRepo, ISkillRateRepo
# from apps.common.schemas_dto import CharacterStatsReadDTO
# from apps.game_core.modules.skill.rate_service import calculate_rates_data
#
#
# class CharacterSkillsService:
#     """
#     Фасад (координатор) для управления бизнес-логикой навыков персонажа.
#
#     Инкапсулирует взаимодействие с репозиториями навыков и статистик,
#     а также оркестрирует расчеты опыта и ставок.
#     """
#
#     def __init__(self, stats_repo: ICharacterStatsRepo, rate_repo: ISkillRateRepo, progress_repo: ISkillProgressRepo):
#         """
#         Инициализирует CharacterSkillsService.
#
#         Args:
#             stats_repo: Репозиторий для работы со статистиками персонажей.
#             rate_repo: Репозиторий для работы со ставками опыта навыков.
#             progress_repo: Репозиторий для работы с прогрессом навыков.
#         """
#         self._stats_repo = stats_repo
#         self._rate_repo = rate_repo
#         self._progress_repo = progress_repo
#         log.debug("CharacterSkillsService | status=initialized")
#
#     async def finalize_tutorial_stats(
#         self, character_id: int, bonus_stats: dict[str, int]
#     ) -> CharacterStatsReadDTO | None:
#         """
#         Финализирует распределение очков характеристик после туториала.
#
#         Применяет бонусные характеристики, инициализирует все базовые навыки
#         и рассчитывает базовые ставки опыта для каждого навыка.
#
#         Args:
#             character_id: Идентификатор персонажа.
#             bonus_stats: Словарь с бонусными характеристиками для применения.
#
#         Returns:
#             DTO `CharacterStatsReadDTO` с обновленными характеристиками персонажа,
#             или None, если персонаж не найден.
#         """
#         log.info(f"CharacterSkills | event=finalize_tutorial_stats char_id={character_id}")
#
#         final_stats_dto = await self._stats_repo.add_stats(character_id, bonus_stats)
#         if not final_stats_dto:
#             log.warning(
#                 f"CharacterSkills | status=failed reason='Character not found for stats update' char_id={character_id}"
#             )
#             return None
#
#         await self._progress_repo.initialize_all_base_skills(character_id)
#         log.debug(f"CharacterSkills | event=base_skills_initialized char_id={character_id}")
#
#         rates_data = calculate_rates_data(character_id, final_stats_dto)
#         await self._rate_repo.upsert_skill_rates(rates_data)
#         log.debug(f"CharacterSkills | event=skill_rates_upserted char_id={character_id}")
#
#         return final_stats_dto
#
#     async def register_action_xp(
#         self, char_id: int, item_subtype: str, outcome: str, custom_base: int | None = None
#     ) -> None:
#         """
#         Начисляет опыт за одиночное действие (например, крафт, сбор).
#
#         Этот метод не используется для боевого опыта, который обрабатывается пакетно.
#
#         Args:
#             char_id: Идентификатор персонажа.
#             item_subtype: Подтип предмета/действия (например, "woodcutting", "mining").
#             outcome: Результат действия ("success", "fail", "crit").
#             custom_base: Опциональная базовая величина опыта, если отличается от стандартной.
#         """
#         from apps.game_core.resources.game_data.xp_rules import BASE_ACTION_XP, OUTCOME_MULTIPLIERS, XP_SOURCE_MAP
#
#         skill_key = XP_SOURCE_MAP.get(item_subtype)
#         if not skill_key:
#             log.warning(
#                 f"CharacterSkills | status=skipped reason='No skill mapping for subtype' char_id={char_id} subtype='{item_subtype}'"
#             )
#             return
#
#         outcome_mult = OUTCOME_MULTIPLIERS.get(outcome, 0.0)
#         if outcome_mult == 0:
#             log.debug(
#                 f"CharacterSkills | status=skipped reason='Zero multiplier for outcome' char_id={char_id} outcome='{outcome}'"
#             )
#             return
#
#         rates = await self._rate_repo.get_all_skill_rates(char_id)
#         xp_rate_val = next((r.xp_per_tick for r in rates if r.skill_key == skill_key), 0)
#
#         base = custom_base or BASE_ACTION_XP
#         efficiency_mod = 1.0 + (xp_rate_val / 100.0)
#         final_xp = int((base * outcome_mult) * efficiency_mod)
#
#         if final_xp > 0:
#             await self._progress_repo.add_skill_xp(char_id, skill_key, final_xp)
#             log.info(
#                 f"CharacterSkills | event=single_xp_gained char_id={char_id} skill='{skill_key}' xp={final_xp} action='{item_subtype}'"
#             )
#
#     async def apply_combat_xp_batch(self, char_id: int, xp_buffer: dict[str, int]) -> None:
#         """
#         Применяет пакетно накопленный боевой опыт к навыкам персонажа.
#
#         Принимает словарь `xp_buffer` (skill_key: raw_points), накопленный в Redis,
#         умножает на ставки опыта и записывает в базу данных.
#
#         Args:
#             char_id: Идентификатор персонажа.
#             xp_buffer: Словарь, где ключ — `skill_key`, а значение — накопленные
#                        "сырые" очки опыта для этого навыка.
#         """
#         if not xp_buffer:
#             log.debug(f"CharacterSkills | status=skipped reason='Empty XP buffer' char_id={char_id}")
#             return
#
#         log.debug(f"CharacterSkills | event=apply_combat_xp_batch char_id={char_id} buffer_size={len(xp_buffer)}")
#
#         rates = await self._rate_repo.get_all_skill_rates(char_id)
#         rates_map = {r.skill_key: r.xp_per_tick for r in rates}
#
#         for skill_key, raw_points in xp_buffer.items():
#             if raw_points <= 0:
#                 continue
#
#             rate_val = rates_map.get(skill_key, 0)
#             efficiency_mod = 1.0 + (rate_val / 100.0)
#             final_xp = int(raw_points * efficiency_mod)
#
#             if final_xp > 0:
#                 await self._progress_repo.add_skill_xp(char_id, skill_key, final_xp)
#                 log.info(
#                     f"CharacterSkills | event=combat_xp_gained char_id={char_id} skill='{skill_key}' xp={final_xp}"
#                 )
#                 # TODO: Добавить вызов check_level_up(char_id, skill_key)
#         log.info(f"CharacterSkills | status=combat_xp_applied char_id={char_id}")
