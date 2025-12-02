# app/services/game_service/arena/service_1v1.py
import asyncio
import time

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.combat_source_dto import CombatSessionContainerDTO
from app.services.core_service.manager.arena_manager import arena_manager
from app.services.core_service.manager.combat_manager import combat_manager

# 🔥 ИМПОРТИРУЕМ НОВЫЙ СЕРВИС ЖИЗНЕННОГО ЦИКЛА
from app.services.game_service.combat.combat_lifecycle_service import CombatLifecycleService
from app.services.game_service.matchmaking_service import MatchmakingService
from database.repositories import get_character_repo


class Arena1v1Service:
    def __init__(self, session: AsyncSession, char_id: int):
        self.session = session
        self.char_id = char_id
        self.mm_service = MatchmakingService(session)
        self.mode = "1v1"

    async def join_queue(self) -> int:
        """Вход в очередь."""
        # 1. Очистка старых статусов
        await combat_manager.delete_player_status(self.char_id)

        # 2. Актуализация Gear Score
        gs = await self.mm_service.get_cached_gs(self.char_id)

        # 3. Добавление в очередь (Redis ZSET)
        await arena_manager.add_to_queue(self.mode, self.char_id, float(gs))

        # 4. Создание метаданных заявки
        meta = {"start_time": time.time(), "gs": gs}
        await arena_manager.create_request(self.char_id, meta)

        log.info(f"Char {self.char_id} (GS: {gs}) встал в очередь {self.mode}.")
        return gs

    async def wait_for_match(self, poll_steps: int = 6, poll_delay: float = 5.0) -> str | None:
        """
        Поллинг (ожидание) матча.
        """
        for i in range(1, poll_steps + 1):
            session_id = await self.check_and_match(attempt=i)
            if session_id:
                return session_id
            await asyncio.sleep(poll_delay)
        return None

    async def check_and_match(self, attempt: int = 1) -> str | None:
        """Попытка найти соперника или проверить статус."""

        # 1. Проверяем, не забрали ли нас уже в бой (Пассивная проверка)
        active_session = await self._check_active_battle()
        if active_session:
            return active_session

        # 2. Проверяем, в очереди ли мы еще
        my_req = await arena_manager.get_request(self.char_id)
        if not my_req:
            return None  # Вылетел или отменил

        my_gs = my_req["gs"]

        # 3. Расширяем диапазон поиска с каждой попыткой
        range_pct = min(0.30, 0.05 * attempt)
        min_score = my_gs * (1.0 - range_pct)
        max_score = my_gs * (1.0 + range_pct)

        # 4. Ищем кандидатов
        candidates = await arena_manager.get_candidates(self.mode, min_score, max_score)

        opponent_id = None
        for c_id_str in candidates:
            c_id = int(c_id_str)
            if c_id != self.char_id:
                opponent_id = c_id
                break

        if not opponent_id:
            return None

        # 5. Атомарный захват (Optimistic Lock)
        is_removed = await arena_manager.remove_from_queue(self.mode, opponent_id)
        if not is_removed:
            return None  # Кто-то успел раньше

        # Удаляем себя
        await arena_manager.remove_from_queue(self.mode, self.char_id)

        # Чистим метаданные заявок
        await arena_manager.delete_request(self.char_id)
        await arena_manager.delete_request(opponent_id)

        # 6. Создаем бой
        session_id = await self._create_pvp_battle(opponent_id)
        return session_id

    async def cancel_queue(self):
        """Отмена поиска."""
        await arena_manager.remove_from_queue(self.mode, self.char_id)
        await arena_manager.delete_request(self.char_id)

    async def create_shadow_battle(self) -> str:
        """Создание боя с Тенью (Полная копия игрока)."""
        await self.cancel_queue()

        char_repo = get_character_repo(self.session)
        me = await char_repo.get_character(self.char_id)
        name_me = me.name if me else "Unknown"

        # 1. Создаем бой
        session_id = await CombatLifecycleService.create_battle(is_pve=True, mode="arena")

        # 2. Добавляем Игрока (Blue) - это загрузит его статы в Redis
        await CombatLifecycleService.add_participant(self.session, session_id, self.char_id, "blue", name_me)

        # 3. 🔥 КЛОНИРОВАНИЕ: Создаем Тень на основе данных игрока
        # Читаем только что сохраненного игрока из Redis
        player_json = await combat_manager.get_actor_json(session_id, self.char_id)

        if player_json:
            # Десериализуем в объект
            shadow_dto = CombatSessionContainerDTO.model_validate_json(player_json)

            # Модифицируем под Тень
            shadow_id = -self.char_id  # Отрицательный ID, чтобы не конфликтовать
            shadow_dto.char_id = shadow_id
            shadow_dto.name = f"👥 Тень ({name_me})"
            shadow_dto.team = "red"
            shadow_dto.is_ai = True  # Включаем AI

            # Сохраняем Тень как нового участника
            await combat_manager.add_participant_id(session_id, shadow_id)
            await combat_manager.save_actor_json(session_id, shadow_id, shadow_dto.model_dump_json())

            log.info(f"Создана Тень {shadow_id} (копия {self.char_id})")
        else:
            # Fallback (на случай сбоя): создаем манекен
            await CombatLifecycleService.add_dummy_participant(session_id, -1, 100, 50, "Глючная Тень")

        # 4. Инициализация (расчет целей)
        await CombatLifecycleService.initialize_battle_state(session_id)

        # Ставим статус
        await self._set_player_status(self.char_id, session_id)

        return session_id

    # --- Private Helpers ---

    async def _check_active_battle(self) -> str | None:
        val = await combat_manager.get_player_status(self.char_id)
        if val and val.startswith("combat:"):
            return val.split(":")[1]
        return None

    async def _set_player_status(self, char_id: int, session_id: str):
        await combat_manager.set_player_status(char_id, f"combat:{session_id}", ttl=300)

    async def _create_pvp_battle(self, opponent_id: int) -> str:
        repo = get_character_repo(self.session)
        me = await repo.get_character(self.char_id)
        enemy = await repo.get_character(opponent_id)

        name_me = me.name if me else f"Player {self.char_id}"
        name_enemy = enemy.name if enemy else f"Player {opponent_id}"

        session_id = await CombatLifecycleService.create_battle(is_pve=False, mode="arena")

        await CombatLifecycleService.add_participant(self.session, session_id, self.char_id, "blue", name_me)
        await CombatLifecycleService.add_participant(self.session, session_id, opponent_id, "red", name_enemy)

        await CombatLifecycleService.initialize_battle_state(session_id)

        # Ставим статусы обоим
        await self._set_player_status(self.char_id, session_id)
        await self._set_player_status(opponent_id, session_id)

        return session_id
