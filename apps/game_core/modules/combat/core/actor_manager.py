# apps/game_core/modules/combat/core/actor_manager.py
import json
from typing import Any, cast

from loguru import logger as log
from redis.asyncio.client import Pipeline

from apps.common.services.core_service import CombatManager
from apps.common.services.core_service.redis_key import RedisKeys as Rk
from apps.game_core.modules.combat.core.combat_context import CombatActorContext, CombatSessionContext
from apps.game_core.system.calculators.stats_waterfall_calculator import StatsWaterfallCalculator


class ActorManager:
    """
    Репозиторий Боя (RBC v2.0).
    Отвечает за пакетную загрузку и сохранение контекста боя.
    """

    def __init__(self, combat_manager: CombatManager):
        self.combat_manager = combat_manager
        self.calculator = StatsWaterfallCalculator()

    async def load_session_context(self, session_id: str) -> CombatSessionContext | None:
        """
        Загружает полный контекст сессии (Meta + All Actors) за 1 RTT.
        Используется Executor'ом перед обработкой пачки задач.
        """
        # 1. Загружаем Meta
        meta = await self.combat_manager.get_rbc_session_meta(session_id)
        if not meta:
            log.warning(f"ActorManager | Session meta not found: {session_id}")
            return None

        # Парсим Meta
        try:
            step_counter = int(meta.get("step_counter", 0))
            # active_actors может быть не актуальным, лучше полагаться на actors_info
            actors_info_json = meta.get("actors_info", "{}")
            actors_info: dict[str, str] = json.loads(actors_info_json)
            teams_json = meta.get("teams", "{}")
            teams: dict[str, list[int]] = json.loads(teams_json)
        except json.JSONDecodeError as e:
            log.error(f"ActorManager | Meta parse error: {e}")
            return None

        # 2. Формируем список ключей для всех актеров
        # Нам нужно загрузить :state (HASH), :cache (JSON), :effects (JSON) для каждого
        actor_ids = list(actors_info.keys())
        if not actor_ids:
            return CombatSessionContext(
                session_id=session_id, step_counter=step_counter, active_actors=0, meta=meta, actors={}
            )

        # 3. Pipeline Load (Batch)
        # Используем execute_pipeline из RedisService для абстракции

        def _load_pipeline(pipe: Pipeline) -> None:
            for char_id_str in actor_ids:
                base_key = Rk.get_rbc_actor_key(session_id, char_id_str)
                # State (HASH)
                pipe.hgetall(f"{base_key}:state")
                # Cache (JSON)
                pipe.json().get(f"{base_key}:cache")
                # Effects (JSON)
                pipe.json().get(f"{base_key}:effects")

        results = await self.combat_manager.redis_service.execute_pipeline(_load_pipeline)

        # 4. Parsing Results
        actors_context: dict[int, CombatActorContext] = {}

        # Результаты идут тройками: [state, cache, effects, state, cache, effects...]
        for i, char_id_str in enumerate(actor_ids):
            base_idx = i * 3
            if base_idx + 2 >= len(results):
                break

            raw_state = results[base_idx]
            raw_cache = results[base_idx + 1]
            raw_effects = results[base_idx + 2]

            if not raw_state:
                log.warning(f"ActorManager | Actor state missing: {char_id_str}")
                continue

            # Используем новую переменную для int id, чтобы избежать конфликта типов с char_id_str
            current_char_id = int(char_id_str)
            role = actors_info.get(char_id_str, "unknown")

            # Определяем команду (обратный поиск)
            team = "neutral"
            for t_name, members in teams.items():
                if current_char_id in members:
                    team = t_name
                    break

            # Parse State
            hp = int(raw_state.get(b"hp", 0))
            en = int(raw_state.get(b"en", 0))
            tactics = int(raw_state.get(b"tactics", 0))
            afk = int(raw_state.get(b"afk_level", 0))
            tokens_json = raw_state.get(b"tokens")
            tokens = json.loads(tokens_json) if tokens_json else {}

            # Parse Cache & Effects (RedisJSON returns dict/list directly)
            stats = raw_cache if raw_cache else {}
            effects = raw_effects if raw_effects else []

            ctx = CombatActorContext(
                char_id=current_char_id,
                hp=hp,
                energy=en,
                tactics=tactics,
                afk_level=afk,
                tokens=tokens,
                stats=stats,
                effects=effects,
                role=role,
                team=team,
            )
            actors_context[current_char_id] = ctx

        return CombatSessionContext(
            session_id=session_id,
            step_counter=step_counter,
            active_actors=len(actors_context),
            meta=meta,
            actors=actors_context,
        )

    async def commit_session_changes(self, session_id: str, context: CombatSessionContext, logs: list[str]) -> None:
        """
        Сохраняет изменения контекста обратно в Redis (Pipeline).
        """

        def _commit_pipeline(pipe: Pipeline) -> None:
            # 1. Update Meta (Step Counter)
            pipe.hset(Rk.get_rbc_meta_key(session_id), "step_counter", str(context.step_counter))

            # 2. Update Actors
            for char_id, actor in context.actors.items():
                # TODO: Оптимизация - сохранять только если были изменения (Dirty Flag)
                # Пока пишем всё для надежности

                base_key = Rk.get_rbc_actor_key(session_id, str(char_id))

                # State
                state_key = f"{base_key}:state"
                pipe.hset(
                    state_key,
                    mapping={
                        "hp": actor.hp,
                        "en": actor.energy,
                        "tactics": actor.tactics,
                        "afk_level": actor.afk_level,
                        "tokens": json.dumps(actor.tokens),
                    },
                )

                # Effects (JSON)
                effects_key = f"{base_key}:effects"
                # cast(Any, ...) используется, чтобы успокоить mypy (List инвариантен)
                pipe.json().set(effects_key, "$", cast(Any, actor.effects))

                # Cache (JSON) - если менялся (например, пересчет статов)
                # В текущей модели Executor не пересчитывает статы (Waterfall), он только читает.
                # Пересчет делает отдельный Job или Lazy Load.
                # Но если мы меняем статы "на лету" (временные баффы), то надо писать.
                # Пока пропустим запись cache, считаем его Read-Only в цикле боя.

            # 3. Append Logs
            if logs:
                log_key = Rk.get_combat_log_key(session_id)
                pipe.rpush(log_key, *logs)

        await self.combat_manager.redis_service.execute_pipeline(_commit_pipeline)
