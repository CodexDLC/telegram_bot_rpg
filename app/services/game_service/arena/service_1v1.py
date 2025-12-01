# app/services/game_service/arena/service_1v1.py
import time

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

# Импортируем менеджеры
from app.services.core_service.manager.arena_manager import arena_manager
from app.services.core_service.manager.combat_manager import combat_manager  # Для проверки статуса
from app.services.game_service.combat.combat_service import CombatService
from app.services.game_service.matchmaking_service import MatchmakingService
from database.repositories import get_character_repo


class Arena1v1Service:
    def __init__(self, session: AsyncSession, char_id: int):
        self.session = session
        self.char_id = char_id
        self.mm_service = MatchmakingService(session)
        self.mode = "1v1"  # Константа для этого сервиса

    async def join_queue(self) -> int:
        # 1. Чистим статус через Менеджер (Абстракция соблюдена)
        await combat_manager.delete_player_status(self.char_id)

        # 2. Считаем GS
        gs = await self.mm_service.get_cached_gs(self.char_id)

        # 3. Сохраняем в ZSET
        await arena_manager.add_to_queue(self.mode, self.char_id, float(gs))

        # 4. Сохраняем мету
        meta = {"start_time": time.time(), "gs": gs}
        await arena_manager.create_request(self.char_id, meta)

        log.info(f"Char {self.char_id} (GS: {gs}) встал в очередь {self.mode}.")
        return gs

    async def check_and_match(self, attempt: int = 1) -> str | None:
        # 1. ПАССИВНАЯ ПРОВЕРКА
        # Тут нам нужен метод проверки статуса. Если его нет в менеджерах,
        # то пока оставим прямой доступ или вынесем.
        active_session = await self._check_active_battle()
        if active_session:
            return active_session

        # 2. Получаем свои данные через ArenaManager
        my_req = await arena_manager.get_request(self.char_id)
        if not my_req:
            return None  # Вылетел из очереди

        my_gs = my_req["gs"]

        # 3. Диапазон
        range_pct = min(0.15, 0.02 * ((attempt + 1) // 2))
        min_score = my_gs * (1.0 - range_pct)
        max_score = my_gs * (1.0 + range_pct)

        # 4. Поиск через ArenaManager
        candidates = await arena_manager.get_candidates(self.mode, min_score, max_score)

        opponent_id = None
        for c_id_str in candidates:
            if int(c_id_str) != self.char_id:
                opponent_id = int(c_id_str)
                break

        if not opponent_id:
            return None

            # 5. Атомарный захват (через ArenaManager)
        # Пытаемся удалить соперника
        is_removed = await arena_manager.remove_from_queue(self.mode, opponent_id)

        if not is_removed:
            return None  # Не успели

        # Удаляем себя
        await arena_manager.remove_from_queue(self.mode, self.char_id)

        # Чистим заявки
        await arena_manager.delete_request(self.char_id)
        await arena_manager.delete_request(opponent_id)

        # 6. Создаем бой
        session_id = await self._create_pvp_battle(opponent_id)
        return session_id

    async def cancel_queue(self):
        """Выход через менеджер."""
        await arena_manager.remove_from_queue(self.mode, self.char_id)
        await arena_manager.delete_request(self.char_id)

    async def _check_active_battle(self) -> str | None:
        # Читаем статус через Менеджер
        val = await combat_manager.get_player_status(self.char_id)
        return val.split(":")[1] if val and val.startswith("combat:") else None

    async def _set_player_status(self, char_id: int, session_id: str):
        # Пишем статус через Менеджер
        await combat_manager.set_player_status(char_id, f"combat:{session_id}", ttl=300)

    async def _create_pvp_battle(self, opponent_id: int) -> str:
        # 1. Достаем красивые имена (Косметика)
        me = await get_character_repo(self.session).get_character(self.char_id)
        enemy = await get_character_repo(self.session).get_character(opponent_id)

        # 2. Создаем "комнату" (Сессию)
        session_id = await CombatService.create_battle([], is_pve=False)
        cs = CombatService(session_id)

        # 3. Загружаем в комнату "куклы" бойцов (Heavy Load logic внутри)
        await cs.add_participant(self.session, self.char_id, "blue", me.name)
        await cs.add_participant(self.session, opponent_id, "red", enemy.name)

        # 4. Раздаем карты (инициализация)
        await cs.initialize_battle_state()

        # 5. Вешаем таблички "Занято" (см. ниже)
        await self._set_player_status(self.char_id, session_id)
        await self._set_player_status(opponent_id, session_id)

        return session_id

    async def create_shadow_battle(self) -> str:
        """Создает бой с Тенью (при тайм-ауте)."""
        await self.cancel_queue()  # Чистим очередь через менеджер

        char_repo = get_character_repo(self.session)
        me = await char_repo.get_character(self.char_id)
        name_me = me.name if me else "Unknown"

        # Создаем бой (is_pve=True)
        session_id = await CombatService.create_battle([], is_pve=True)
        cs = CombatService(session_id)

        await cs.add_participant(self.session, self.char_id, "blue", name_me)

        # Создаем Тень (слабая копия)
        # В будущем сюда можно передать (me.stats * 0.8)
        await cs.add_dummy_participant(-1, 100, 50, "👥 Тень")

        await cs.initialize_battle_state()

        # Ставим статус ТОЛЬКО СЕБЕ (Тени статус в Redis не нужен)
        await self._set_player_status(self.char_id, session_id)

        return session_id
