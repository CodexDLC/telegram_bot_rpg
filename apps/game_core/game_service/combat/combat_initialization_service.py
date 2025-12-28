# TODO: DRAFT ARCHITECTURE (NOT IMPLEMENTED YET)
# import uuid
# import time
# from typing import Any
#
# from loguru import logger as log
# from sqlalchemy.ext.asyncio import AsyncSession
#
# from apps.common.schemas_dto.combat_source_dto import (
#     CombatSessionContainerDTO,
#     FighterStateDTO,
#     StatSourceData,
# )
# from apps.common.schemas_dto.monster_dto import GeneratedMonsterDTO
# from apps.common.services.core_service.manager.account_manager import AccountManager
# from apps.common.services.core_service.manager.combat_manager import CombatManager
# from apps.game_core.game_service.combat.core.combat_stats_calculator import StatsCalculator
#
#
# class CombatInitializationService:
#     """
#     Фабрика боевых сессий.
#     Отвечает ИСКЛЮЧИТЕЛЬНО за создание структуры боя в Redis.
#     Не управляет ходом боя.
#     """
#
#     def __init__(self, session: AsyncSession, combat_manager: CombatManager, account_manager: AccountManager):
#         self.session = session
#         self.combat_manager = combat_manager
#         self.account_manager = account_manager
#
#     async def create_pve_tutorial_battle(
#         self, char_id: int, monster_data: dict[str, Any], location_id: str
#     ) -> str:
#         """
#         Создает учебный бой (1 на 1) с монстром из DTO.
#         """
#         session_id = str(uuid.uuid4())
#
#         # 1. Создаем метаданные сессии
#         await self._create_session_meta(session_id, mode="tutorial", battle_type="pve")
#
#         # 2. Добавляем Игрока
#         # TODO: Загружать реальные данные игрока (шмот, статы) через AccountManager/Repo
#         # Пока используем упрощенную инициализацию
#         await self._add_player_participant(session_id, char_id)
#
#         # 3. Добавляем Монстра (из DTO)
#         # Генерируем временный ID для монстра (отрицательный хэш)
#         m_id = -abs(hash(f"{session_id}_{monster_data.get('id')}")) % 1000000
#         if m_id == 0: m_id = -1
#
#         await self._add_monster_participant_from_dto(session_id, m_id, monster_data)
#
#         # 4. Настраиваем очереди (Игрок <-> Монстр)
#         await self._initialize_exchange_queues_1v1(session_id, char_id, m_id)
#
#         log.info(f"CombatInit | Created tutorial battle {session_id} for char {char_id} vs monster {m_id}")
#         return session_id
#
#     async def _create_session_meta(self, session_id: str, mode: str, battle_type: str):
#         meta = {
#             "active": 1,
#             "round": 0,
#             "start_time": int(time.time()),
#             "mode": mode,
#             "type": battle_type,
#         }
#         await self.combat_manager.redis.set_hash_fields(f"combat:rbc:{session_id}:meta", meta)
#
#     async def _add_player_participant(self, session_id: str, char_id: int):
#         """
#         Добавляет игрока.
#         """
#         # В будущем здесь будет загрузка из БД.
#         # Сейчас делаем базовую инициализацию.
#
#         # Получаем базовые статы (если есть в Redis, иначе дефолт)
#         # Для туториала статы уже должны быть в ac:{char_id}:stats
#         account_stats = await self.account_manager.get_account_field(char_id, "stats")
#         if not account_stats:
#             account_stats = {} # Дефолты
#
#         # Формируем контейнер
#         stats_map = {}
#         for k, v in account_stats.items():
#             stats_map[k] = StatSourceData(base=float(v))
#
#         # Добавляем HP/Energy Max (базовые)
#         if "hp_max" not in stats_map: stats_map["hp_max"] = StatSourceData(base=100.0)
#         if "energy_max" not in stats_map: stats_map["energy_max"] = StatSourceData(base=100.0)
#
#         # Считаем финальные статы
#         final_stats = StatsCalculator.calculate_all(stats_map)
#
#         state = FighterStateDTO(
#             hp_current=int(final_stats.get("hp_max", 100)),
#             energy_current=int(final_stats.get("energy_max", 100)),
#         )
#
#         container = CombatSessionContainerDTO(
#             char_id=char_id,
#             team="blue",
#             name=f"Player {char_id}", # TODO: Имя из Redis
#             state=state,
#             stats=stats_map
#         )
#
#         await self.combat_manager.set_rbc_actor_state(session_id, char_id, container)
#
#     async def _add_monster_participant_from_dto(self, session_id: str, m_id: int, monster_data: dict):
#         """
#         Добавляет монстра на основе DTO (словаря).
#         """
#         # Парсим статы из DTO
#         raw_stats = monster_data.get("attributes", {})
#         if not raw_stats and "stats" in monster_data: # Фоллбэк на старый формат
#              raw_stats = monster_data["stats"]
#
#         stats_map = {}
#         for k, v in raw_stats.items():
#             stats_map[k] = StatSourceData(base=float(v))
#
#         # Монстрам часто нужно накинуть HP, если в базе только статы
#         # Предполагаем, что hp_max рассчитывается от endurance, но можно задать базу
#         if "hp_max" not in stats_map:
#             # Простая формула для туториала
#             endurance = raw_stats.get("endurance", 1)
#             hp = 50 + (endurance * 10)
#             stats_map["hp_max"] = StatSourceData(base=float(hp))
#
#         final_stats = StatsCalculator.calculate_all(stats_map)
#
#         state = FighterStateDTO(
#             hp_current=int(final_stats.get("hp_max", 50)),
#             energy_current=100,
#         )
#
#         container = CombatSessionContainerDTO(
#             char_id=m_id,
#             team="red",
#             name=monster_data.get("name", "Unknown Monster"),
#             is_ai=True,
#             state=state,
#             stats=stats_map
#         )
#
#         await self.combat_manager.set_rbc_actor_state(session_id, m_id, container)
#
#     async def _initialize_exchange_queues_1v1(self, session_id: str, player_id: int, monster_id: int):
#         """
#         Связывает игрока и монстра в очереди.
#         """
#         # Игрок бьет монстра
#         await self.combat_manager.redis.client.rpush(f"combat:rbc:{session_id}:exchange:{player_id}", monster_id)
#         # Монстр бьет игрока
#         await self.combat_manager.redis.client.rpush(f"combat:rbc:{session_id}:exchange:{monster_id}", player_id)
