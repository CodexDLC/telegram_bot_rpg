# app/services/game_service/combat/combat_session_service.py
import json

from loguru import logger as log
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.combat_source_dto import CombatSessionContainerDTO, StatSourceData
from app.services.core_service.redis_service import redis_service
from app.services.game_service.combat.combat_aggregator import CombatAggregator
from app.services.game_service.combat.stats_calculator import StatsCalculator


class CombatSessionService:
    def __init__(self, session_id: str):
        self.session_id = session_id
        # Ключ теперь хранит JSON строку целиком
        self._key_template = f"combat:sess:{session_id}:actor:{{}}"

    async def initialize_actor(self, session: AsyncSession, char_id: int, team: str, name: str) -> None:
        """
        Создает DTO через агрегатор и пишет в Redis как JSON.
        """
        aggregator = CombatAggregator(session)

        # Получаем готовый DTO контейнер (см. Aggregator ниже)
        container = await aggregator.collect_session_container(char_id)

        # Дозаполняем мета-данные
        container.team = team
        container.name = name

        redis_key = self._key_template.format(char_id)

        # 🔥 СЕРИАЛИЗАЦИЯ В JSON ДЛЯ REDIS 🔥
        # model_dump_json() превращает объект в строку '{"char_id": 1, "stats": ...}'
        await redis_service.redis_client.set(redis_key, container.model_dump_json())

        log.info(f"Боец {char_id} записан в Redis (JSON).")

    async def get_aggregated_stats(self, char_id: int) -> dict[str, float] | None:
        """
        Читает JSON, парсит в DTO, считает цифры.
        """
        redis_key = self._key_template.format(char_id)
        raw_json = await redis_service.redis_client.get(redis_key)

        if not raw_json:
            return None

        # 🔥 ДЕСЕРИАЛИЗАЦИЯ ИЗ JSON 🔥
        try:
            container = CombatSessionContainerDTO.model_validate_json(raw_json)
        except (ValidationError, json.JSONDecodeError) as e:
            log.error(f"Ошибка парсинга боевой сессии для {char_id}: {e}")
            return None

        # Отдаем в калькулятор
        return StatsCalculator.aggregate_all(container.stats)

    async def add_buff(self, char_id: int, stat_key: str, buff_id: str, value: float, is_percent: bool = False) -> bool:
        """
        Пример атомарного обновления (Read -> Modify -> Write).
        В продакшене тут нужен Redis Lock, но для начала пойдет так.
        """
        redis_key = self._key_template.format(char_id)
        raw_json = await redis_service.redis_client.get(redis_key)

        if not raw_json:
            return False

        container = CombatSessionContainerDTO.model_validate_json(raw_json)

        # Инициализируем стат, если его не было (например, временный щит)
        if stat_key not in container.stats:
            container.stats[stat_key] = StatSourceData()

        # Добавляем в нужный словарь
        if is_percent:
            container.stats[stat_key].buffs_percent[buff_id] = value
        else:
            container.stats[stat_key].buffs_flat[buff_id] = value

        # Сохраняем обратно
        await redis_service.redis_client.set(redis_key, container.model_dump_json())
        return True
