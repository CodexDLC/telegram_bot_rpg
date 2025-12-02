import asyncio
import time

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.combat_source_dto import CombatSessionContainerDTO
from app.services.core_service.manager.arena_manager import arena_manager
from app.services.core_service.manager.combat_manager import combat_manager
from app.services.game_service.combat.combat_lifecycle_service import CombatLifecycleService
from app.services.game_service.matchmaking_service import MatchmakingService
from database.repositories import get_character_repo


class Arena1v1Service:
    """
    Сервис для управления 1v1 боями на арене.

    Отвечает за постановку в очередь, поиск противника, создание боевой сессии
    и обработку отмены поиска.
    """

    def __init__(self, session: AsyncSession, char_id: int):
        """
        Инициализирует Arena1v1Service.

        Args:
            session: Асинхронная сессия базы данных.
            char_id: Уникальный идентификатор персонажа.
        """
        self.session = session
        self.char_id = char_id
        self.mm_service = MatchmakingService(session)
        self.mode = "1v1"
        log.debug(f"Arena1v1Service | status=initialized char_id={char_id}")

    async def join_queue(self) -> int:
        """
        Добавляет персонажа в очередь на 1v1 арену.

        Выполняет очистку старых статусов, актуализирует Gear Score,
        добавляет персонажа в очередь Redis (ZSET) и создает метаданные заявки.

        Returns:
            Актуальный Gear Score персонажа.
        """
        await combat_manager.delete_player_status(self.char_id)
        gs = await self.mm_service.get_cached_gs(self.char_id)
        await arena_manager.add_to_queue(self.mode, self.char_id, float(gs))
        meta = {"start_time": time.time(), "gs": gs}
        await arena_manager.create_request(self.char_id, meta)
        log.info(f"Arena1v1 | event=joined_queue char_id={self.char_id} gs={gs}")
        return gs

    async def wait_for_match(self, poll_steps: int = 6, poll_delay: float = 5.0) -> str | None:
        """
        Осуществляет поллинг для ожидания матча.

        Args:
            poll_steps: Максимальное количество попыток поллинга.
            poll_delay: Задержка между попытками поллинга в секундах.

        Returns:
            Идентификатор боевой сессии, если матч найден, иначе None.
        """
        for i in range(1, poll_steps + 1):
            session_id = await self.check_and_match(attempt=i)
            if session_id:
                log.info(f"Arena1v1 | event=match_found_during_wait char_id={self.char_id} session_id='{session_id}'")
                return session_id
            await asyncio.sleep(poll_delay)
        log.info(f"Arena1v1 | event=wait_timeout char_id={self.char_id}")
        return None

    async def check_and_match(self, attempt: int = 1) -> str | None:
        """
        Проверяет наличие активного боя или ищет противника в очереди.

        Args:
            attempt: Номер текущей попытки поиска (влияет на расширение диапазона GS).

        Returns:
            Идентификатор боевой сессии, если бой найден или создан, иначе None.
        """
        active_session = await self._check_active_battle()
        if active_session:
            log.debug(f"Arena1v1 | event=active_battle_found char_id={self.char_id} session_id='{active_session}'")
            return active_session

        my_req = await arena_manager.get_request(self.char_id)
        if not my_req:
            log.debug(f"Arena1v1 | event=request_not_found char_id={self.char_id}")
            return None

        my_gs = my_req["gs"]
        range_pct = min(0.30, 0.05 * attempt)
        min_score = my_gs * (1.0 - range_pct)
        max_score = my_gs * (1.0 + range_pct)

        candidates = await arena_manager.get_candidates(self.mode, min_score, max_score)

        opponent_id = None
        for c_id_str in candidates:
            c_id = int(c_id_str)
            if c_id != self.char_id:
                opponent_id = c_id
                break

        if not opponent_id:
            log.debug(f"Arena1v1 | event=no_opponent_found char_id={self.char_id} attempt={attempt}")
            return None

        is_removed = await arena_manager.remove_from_queue(self.mode, opponent_id)
        if not is_removed:
            log.debug(f"Arena1v1 | event=opponent_taken char_id={self.char_id} opponent_id={opponent_id}")
            return None

        await arena_manager.remove_from_queue(self.mode, self.char_id)
        await arena_manager.delete_request(self.char_id)
        await arena_manager.delete_request(opponent_id)

        session_id = await self._create_pvp_battle(opponent_id)
        log.info(
            f"Arena1v1 | event=pvp_battle_created char_id={self.char_id} opponent_id={opponent_id} session_id='{session_id}'"
        )
        return session_id

    async def cancel_queue(self) -> None:
        """
        Удаляет персонажа из очереди на арену и удаляет его заявку.
        """
        await arena_manager.remove_from_queue(self.mode, self.char_id)
        await arena_manager.delete_request(self.char_id)
        log.info(f"Arena1v1 | event=queue_cancelled char_id={self.char_id}")

    async def create_shadow_battle(self) -> str:
        """
        Создает бой с "Тенью" (AI-противником), которая является клоном персонажа игрока.

        Используется, когда поиск реального противника занимает слишком много времени.

        Returns:
            Идентификатор созданной боевой сессии.
        """
        await self.cancel_queue()

        char_repo = get_character_repo(self.session)
        me = await char_repo.get_character(self.char_id)
        name_me = me.name if me else "Unknown"

        session_id = await CombatLifecycleService.create_battle(is_pve=True, mode="arena")
        await CombatLifecycleService.add_participant(self.session, session_id, self.char_id, "blue", name_me)

        player_json = await combat_manager.get_actor_json(session_id, self.char_id)

        if player_json:
            shadow_dto = CombatSessionContainerDTO.model_validate_json(player_json)
            shadow_id = -self.char_id
            shadow_dto.char_id = shadow_id
            shadow_dto.name = f"👥 Тень ({name_me})"
            shadow_dto.team = "red"
            shadow_dto.is_ai = True

            await combat_manager.add_participant_id(session_id, shadow_id)
            await combat_manager.save_actor_json(session_id, shadow_id, shadow_dto.model_dump_json())
            log.info(f"Arena1v1 | event=shadow_created char_id={self.char_id} shadow_id={shadow_id}")
        else:
            await CombatLifecycleService.add_dummy_participant(session_id, -1, 100, 50, "Глючная Тень")
            log.warning(
                f"Arena1v1 | event=shadow_creation_failed reason='Player JSON not found' char_id={self.char_id}"
            )

        await CombatLifecycleService.initialize_battle_state(session_id)
        await self._set_player_status(self.char_id, session_id)
        log.info(f"Arena1v1 | event=shadow_battle_created char_id={self.char_id} session_id='{session_id}'")
        return session_id

    async def _check_active_battle(self) -> str | None:
        """
        Проверяет, участвует ли персонаж уже в активном бою.

        Returns:
            Идентификатор боевой сессии, если персонаж в бою, иначе None.
        """
        val = await combat_manager.get_player_status(self.char_id)
        if val and val.startswith("combat:"):
            return val.split(":")[1]
        return None

    async def _set_player_status(self, char_id: int, session_id: str) -> None:
        """
        Устанавливает статус игрока в Redis, указывая на участие в боевой сессии.

        Args:
            char_id: Идентификатор персонажа.
            session_id: Идентификатор боевой сессии.
        """
        await combat_manager.set_player_status(char_id, f"combat:{session_id}", ttl=300)
        log.debug(f"Arena1v1 | event=player_status_set char_id={char_id} status='combat:{session_id}'")

    async def _create_pvp_battle(self, opponent_id: int) -> str:
        """
        Создает новую PvP боевую сессию между двумя персонажами.

        Args:
            opponent_id: Идентификатор персонажа-противника.

        Returns:
            Идентификатор созданной боевой сессии.
        """
        repo = get_character_repo(self.session)
        me = await repo.get_character(self.char_id)
        enemy = await repo.get_character(opponent_id)

        name_me = me.name if me else f"Player {self.char_id}"
        name_enemy = enemy.name if enemy else f"Player {opponent_id}"

        session_id = await CombatLifecycleService.create_battle(is_pve=False, mode="arena")

        await CombatLifecycleService.add_participant(self.session, session_id, self.char_id, "blue", name_me)
        await CombatLifecycleService.add_participant(self.session, session_id, opponent_id, "red", name_enemy)

        await CombatLifecycleService.initialize_battle_state(session_id)

        await self._set_player_status(self.char_id, session_id)
        await self._set_player_status(opponent_id, session_id)
        log.info(
            f"Arena1v1 | event=pvp_battle_initialized char_id={self.char_id} opponent_id={opponent_id} session_id='{session_id}'"
        )
        return session_id
