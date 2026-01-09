import json
from typing import Any

from redis.asyncio.client import Pipeline

from apps.common.schemas_dto.combat_source_dto import SessionDataDTO
from apps.common.services.redis.redis_key import RedisKeys as Rk
from apps.common.services.redis.redis_service import RedisService


class CombatManager:
    """
    Менеджер для управления данными боевых сессий в Redis (RBC v3.0).
    Инкапсулирует ключи и методы доступа к данным.
    """

    def __init__(self, redis_service: RedisService):
        self.redis = redis_service

    # ==========================================================================
    # 1. ГЛОБАЛЬНОЕ СОСТОЯНИЕ (META & TARGETS)
    # ==========================================================================

    async def get_rbc_session_meta(self, session_id: str) -> dict[str, str] | None:
        """Загрузка HASH :meta"""
        return await self.redis.get_all_hash(Rk.get_rbc_meta_key(session_id))

    async def pop_player_target(self, session_id: str, char_id: int) -> int | None:
        """
        [ATOMIC] Извлекает (Pop) первую цель из персонального пула :targets.
        """
        key = Rk.get_rbc_targets_key(session_id)
        # JSON.ARRPOP позволяет атомарно забрать ID цели из массива по пути $.char_id
        res = await self.redis.eval_script(
            "return redis.call('JSON.ARRPOP', KEYS[1], '$.' .. ARGV[1], 0)", keys=[key], args=[str(char_id)]
        )
        return int(res[0]) if res and res[0] else None

    async def peek_player_target(self, session_id: str, char_id: int) -> int | None:
        """
        Возвращает первую цель из очереди, НЕ удаляя ее (PEEK).
        Используется для ViewService.
        """
        key = Rk.get_rbc_targets_key(session_id)
        # JSON.GET path $.char_id[0]
        res = await self.redis.json_get(key, f"$.{char_id}[0]")

        if res and isinstance(res, list) and len(res) > 0 and res[0] is not None:
            return int(res[0])
        return None

    async def create_session_batch(self, session_id: str, data: SessionDataDTO, ttl: int) -> None:
        """
        Создает сессию в Redis (Meta, Targets, Actors).
        """

        def _fill_pipe(pipe: Pipeline) -> None:
            # 1. Global Meta (Hash)
            pipe.hset(Rk.get_rbc_meta_key(session_id), mapping=data.meta)
            pipe.expire(Rk.get_rbc_meta_key(session_id), ttl)

            # 2. Global Targets (JSON)
            targets_key = Rk.get_rbc_targets_key(session_id)
            pipe.json().set(targets_key, "$", data.targets)  # type: ignore
            pipe.expire(targets_key, ttl)

            # 3. Actors (Namespace)
            for aid, keys in data.actors.items():
                base_key = Rk.get_rbc_actor_key(session_id, str(aid))

                # :state (Hash)
                pipe.hset(f"{base_key}:state", mapping=keys["state"])
                pipe.expire(f"{base_key}:state", ttl)

                # :raw (JSON)
                pipe.json().set(f"{base_key}:raw", "$", keys["raw"])  # type: ignore
                pipe.expire(f"{base_key}:raw", ttl)

                # :loadout (JSON)
                pipe.json().set(f"{base_key}:loadout", "$", keys["loadout"])  # type: ignore
                pipe.expire(f"{base_key}:loadout", ttl)

                # :meta (JSON)
                pipe.json().set(f"{base_key}:meta", "$", keys["meta"])  # type: ignore
                pipe.expire(f"{base_key}:meta", ttl)

                # :active_abilities (JSON)
                pipe.json().set(f"{base_key}:active_abilities", "$", keys["active_abilities"])  # type: ignore
                pipe.expire(f"{base_key}:active_abilities", ttl)

                # :data_xp (JSON)
                pipe.json().set(f"{base_key}:data_xp", "$", keys["data_xp"])  # type: ignore
                pipe.expire(f"{base_key}:data_xp", ttl)

                # :moves (JSON) - Init with empty dicts
                moves_key = Rk.get_combat_moves_key(session_id, str(aid))
                empty_moves = {"exchange": {}, "item": {}, "instant": {}}
                pipe.json().set(moves_key, "$", empty_moves)  # type: ignore
                pipe.expire(moves_key, ttl)

        await self.redis.execute_pipeline(_fill_pipe)

    async def universal_hot_join(
        self, session_id: str, char_id: int, team_name: str, actor_data: dict, is_ai: bool = True
    ) -> None:
        """
        [UNIVERSAL HOT-JOIN] Атомарно внедряет любого актера (игрока, бота, хаос) в текущую сессию.
        1. Создает инфраструктуру ключей актера.
        2. Обновляет Meta (teams, actors_info).
        3. Обновляет Targets (взаимная видимость врагов).
        """

        # 1. Создаем инфраструктуру (Pipeline)
        def _fill_pipe(pipe: Pipeline) -> None:
            base = Rk.get_rbc_actor_key(session_id, str(char_id))

            pipe.hset(f"{base}:state", mapping=actor_data["state"])
            pipe.json().set(f"{base}:raw", "$", actor_data["raw"])  # type: ignore
            pipe.json().set(f"{base}:loadout", "$", actor_data["loadout"])  # type: ignore
            pipe.json().set(f"{base}:meta", "$", actor_data["meta"])  # type: ignore
            pipe.json().set(f"{base}:active_abilities", "$", [])  # type: ignore
            pipe.json().set(f"{base}:data_xp", "$", {})  # type: ignore

            moves_key = Rk.get_combat_moves_key(session_id, str(char_id))
            pipe.json().set(moves_key, "$", {"exchange": {}, "item": {}, "instant": {}})  # type: ignore

        await self.redis.execute_pipeline(_fill_pipe)

        # 2. Lua-скрипт для "склейки" социальных связей
        script = """
        local meta_key = KEYS[1]
        local targets_key = KEYS[2]
        local char_id = ARGV[1]
        local team_name = ARGV[2]
        local is_ai = ARGV[3]
        
        -- A. Обновляем actors_info
        local info_raw = redis.call("HGET", meta_key, "actors_info")
        local info = cjson.decode(info_raw or "{}")
        info[char_id] = (is_ai == "1") and "ai" or "player"
        redis.call("HSET", meta_key, "actors_info", cjson.encode(info))
        
        -- B. Обновляем teams
        local teams_raw = redis.call("HGET", meta_key, "teams")
        local teams = cjson.decode(teams_raw or "{}")
        if not teams[team_name] then teams[team_name] = {} end
        
        -- Проверка на дубликат в команде (на всякий случай)
        local exists = false
        for _, id in ipairs(teams[team_name]) do
            if tostring(id) == char_id then exists = true break end
        end
        if not exists then
            table.insert(teams[team_name], tonumber(char_id))
            redis.call("HSET", meta_key, "teams", cjson.encode(teams))
        end
        
        -- C. РЕЗОЛВИНГ ЦЕЛЕЙ (Targets)
        -- Мы берем ВСЕ текущие списки целей и добавляем туда нового врага
        local targets_raw = redis.call("JSON.GET", targets_key, "$")
        local all_targets = {}
        if targets_raw then
            all_targets = cjson.decode(targets_raw)[1] or {}
        end
        
        local new_actor_targets = {}
        
        for actor_id, target_list in pairs(all_targets) do
            -- Определяем команду этого актера (нужно найти его в teams)
            -- Это дорого (O(N*M)), но для Hot Join допустимо.
            -- Или мы можем считать, что если он не в нашей команде - он враг.
            
            local is_enemy = true
            -- Проверяем, есть ли он в нашей команде
            if teams[team_name] then
                for _, member_id in ipairs(teams[team_name]) do
                    if tostring(member_id) == actor_id then 
                        is_enemy = false 
                        break 
                    end
                end
            end
            
            if is_enemy then
                -- Мы добавляем себя ему в список целей (если еще нет)
                local already_target = false
                for _, tid in ipairs(target_list) do
                    if tostring(tid) == char_id then already_target = true break end
                end
                if not already_target then
                    table.insert(target_list, tonumber(char_id))
                end
                
                -- Он добавляется к нам в список целей
                table.insert(new_actor_targets, tonumber(actor_id))
            end
        end
        
        -- Записываем обновленные списки обратно
        all_targets[char_id] = new_actor_targets
        redis.call("JSON.SET", targets_key, "$", cjson.encode(all_targets))
        
        return 1
        """

        await self.redis.eval_script(
            script,
            keys=[Rk.get_rbc_meta_key(session_id), Rk.get_rbc_targets_key(session_id)],
            args=[str(char_id), team_name, "1" if is_ai else "0"],
        )

    async def add_log(self, session_id: str, text: str, tags: list[str] | None = None) -> None:
        """Добавляет запись в лог боя."""
        import time

        log_msg = {"text": text, "timestamp": time.time(), "tags": tags or []}
        await self.redis.push_to_list(Rk.get_combat_log_key(session_id), json.dumps(log_msg))

    # ==========================================================================
    # 2. ДАННЫЕ АКТОРА (BATCH LOADING)
    # ==========================================================================

    async def load_full_context_data(self, session_id: str, char_ids: list[int]) -> dict[str, Any]:
        """
        Загружает данные всех участников сессии.
        Возвращает структурированный словарь: {char_id: {state, raw, loadout, ...}}
        """
        raw_results = await self.load_actors_data_batch(session_id, char_ids)

        step = 7
        structured_data = {}
        for i, cid in enumerate(char_ids):
            idx = i * step

            res_state = raw_results[idx]
            res_raw = raw_results[idx + 1]
            res_loadout = raw_results[idx + 2]
            res_meta = raw_results[idx + 3]
            res_active = raw_results[idx + 4]
            res_xp = raw_results[idx + 5]
            res_move = raw_results[idx + 6]

            structured_data[cid] = {
                "state": res_state,
                "raw": res_raw if res_raw else {},
                "loadout": res_loadout if res_loadout else {},
                "meta": res_meta if res_meta else {},
                "abilities": res_active if res_active else [],
                "xp": res_xp if res_xp else {},
                "move": res_move if res_move else {},  # Теперь это словарь списков {exchange: [], ...}
            }

        structured_data["global_queue"] = raw_results[-1]
        return structured_data

    async def load_actors_data_batch(self, session_id: str, char_ids: list[int]) -> list[Any]:
        """
        Пакетная загрузка всех данных актеров (7 ключей на каждого).
        """

        def _load_batch(pipe: Pipeline) -> None:
            for cid in char_ids:
                base_key = Rk.get_rbc_actor_key(session_id, str(cid))
                # 0. State
                pipe.hgetall(f"{base_key}:state")
                # 1. Raw
                pipe.json().get(f"{base_key}:raw")  # type: ignore
                # 2. Loadout
                pipe.json().get(f"{base_key}:loadout")  # type: ignore
                # 3. Meta
                pipe.json().get(f"{base_key}:meta")  # type: ignore
                # 4. Active Abilities
                pipe.json().get(f"{base_key}:active_abilities")  # type: ignore
                # 5. XP Buffer
                pipe.json().get(f"{base_key}:data_xp")  # type: ignore
                # 6. Moves (Intents)
                pipe.json().get(Rk.get_combat_moves_key(session_id, str(cid)))  # type: ignore

            pipe.lrange(Rk.get_rbc_queue_key(session_id), 0, -1)

        return await self.redis.execute_pipeline(_load_batch)

    async def load_snapshot_data_batch(
        self, session_id: str, char_ids: list[int]
    ) -> tuple[dict[int, list[int]], list[Any]]:
        """
        Легкая загрузка для UI (Targets + Actors Data).
        Возвращает (targets_map, actors_data_list).
        """

        def _load(pipe: Pipeline) -> None:
            # 1. Targets
            pipe.json().get(Rk.get_rbc_targets_key(session_id))  # type: ignore

            # 2. Actors
            for cid in char_ids:
                base_key = Rk.get_rbc_actor_key(session_id, str(cid))
                pipe.hgetall(f"{base_key}:state")
                pipe.json().get(f"{base_key}:meta")  # type: ignore
                pipe.json().get(f"{base_key}:loadout")  # type: ignore
                pipe.json().get(f"{base_key}:active_abilities")  # type: ignore
                pipe.json().get(Rk.get_combat_moves_key(session_id, str(cid)))  # type: ignore

        results = await self.redis.execute_pipeline(_load)

        targets_raw = results[0]
        targets_map = {}
        if targets_raw:
            for k, v in targets_raw.items():
                if k.isdigit():
                    targets_map[int(k)] = v

        return targets_map, results[1:]

    # ==========================================================================
    # 3. НАМЕРЕНИЯ (MOVES - MULTI-TARGETING)
    # ==========================================================================

    async def append_move(self, session_id: str, char_id: int, strategy: str, move_dto: dict) -> None:
        """
        [SPAMMING] Добавляет намерение в СЛОВАРЬ соответствующей стратегии.
        strategy: 'exchange', 'item', 'instant'
        """
        key = Rk.get_combat_moves_key(session_id, str(char_id))
        move_id = move_dto.get("move_id")
        if not move_id:
            raise ValueError("Move DTO must have move_id")

        # Путь: $.strategy.move_id
        path = f"$.{strategy}.{move_id}"

        # Используем JSON.SET для записи в словарь
        await self.redis.json_set(key, path, move_dto)

        # Обновляем TTL ключа (продлеваем жизнь всем намерениям)
        await self.redis.expire(key, 300)

    async def append_moves_batch(self, session_id: str, char_id: int, moves_dtos: list[Any]) -> None:
        """
        [BATCH] Добавляет несколько намерений (без удаления целей).
        Используется для Instant/Item мувов AI.
        """

        def _save_batch(pipe: Pipeline) -> None:
            key = Rk.get_combat_moves_key(session_id, str(char_id))
            for move in moves_dtos:
                path = f"$.{move.strategy}.{move.move_id}"
                pipe.json().set(key, path, move.model_dump())  # type: ignore
            pipe.expire(key, 300)

        await self.redis.execute_pipeline(_save_batch)

    async def register_exchange_move_atomic(
        self, session_id: str, char_id: int, target_id: int, move_dto: dict
    ) -> bool:
        """
        [ATOMIC] Регистрирует ход типа 'exchange'.
        1. Проверяет наличие target_id в списке целей игрока.
        2. Если есть - удаляет его из списка.
        3. Добавляет move_dto в moves:exchange (как ключ словаря).
        Возвращает True, если успешно.
        """
        targets_key = Rk.get_rbc_targets_key(session_id)
        moves_key = Rk.get_combat_moves_key(session_id, str(char_id))

        move_id = move_dto.get("move_id")
        if not move_id:
            return False

        # LUA Script
        script = """
        local targets = redis.call('JSON.GET', KEYS[1], '$.' .. ARGV[1])
        if not targets then return 0 end
        
        local idx_res = redis.call('JSON.ARRINDEX', KEYS[1], '$.' .. ARGV[1], tonumber(ARGV[2]))
        
        if not idx_res or idx_res[1] == -1 then
            return 0
        end
        
        local real_idx = idx_res[1]
        
        -- 1. Удаляем цель (POP по индексу)
        redis.call('JSON.ARRPOP', KEYS[1], '$.' .. ARGV[1], real_idx)
        
        -- 2. Добавляем ход (JSON.SET в словарь)
        -- Путь: $.exchange.move_id
        local path = '$.exchange.' .. ARGV[4]
        redis.call('JSON.SET', KEYS[2], path, ARGV[3])
        
        return 1
        """

        import json

        res = await self.redis.eval_script(
            script,
            keys=[targets_key, moves_key],
            args=[str(char_id), str(target_id), json.dumps(move_dto), str(move_id)],
        )
        return bool(res)

    async def register_moves_batch_atomic(self, session_id: str, char_id: int, moves_data: list[dict[str, Any]]) -> int:
        """
        [ATOMIC BATCH] Регистрирует несколько ходов для AI.
        Для каждого хода:
        1. Находит цель в targets.
        2. Удаляет её (POP).
        3. Записывает мув.

        moves_data: List of { "move_json": str, "target_id": int, "strategy": str, "move_id": str }
        Возвращает количество успешно зарегистрированных ходов.
        """
        if not moves_data:
            return 0

        targets_key = Rk.get_rbc_targets_key(session_id)
        moves_key = Rk.get_combat_moves_key(session_id, str(char_id))

        # LUA Script
        script = """
        local success_count = 0
        local moves = cjson.decode(ARGV[2])
        local char_id = ARGV[1]
        
        for _, move_item in ipairs(moves) do
            local target_id = move_item.target_id
            local move_json = move_item.move_json
            local strategy = move_item.strategy
            local move_id = move_item.move_id
            
            -- 1. Ищем цель
            local idx_res = redis.call('JSON.ARRINDEX', KEYS[1], '$.' .. char_id, target_id)
            
            if idx_res and idx_res[1] ~= -1 then
                local real_idx = idx_res[1]
                
                -- 2. Удаляем цель
                redis.call('JSON.ARRPOP', KEYS[1], '$.' .. char_id, real_idx)
                
                -- 3. Записываем мув
                local path = '$.' .. strategy .. '.' .. move_id
                redis.call('JSON.SET', KEYS[2], path, move_json)
                
                success_count = success_count + 1
            end
        end
        
        return success_count
        """

        import json

        res = await self.redis.eval_script(
            script, keys=[targets_key, moves_key], args=[str(char_id), json.dumps(moves_data)]
        )
        return int(res) if res else 0

    async def check_move_exists(self, session_id: str, char_id: int) -> bool:
        """Проверяет наличие ключа с намерениями."""
        key = Rk.get_combat_moves_key(session_id, str(char_id))
        return await self.redis.key_exists(key)

    async def get_moves_batch(self, session_id: str, char_ids: list[int]) -> dict[int, Any]:
        """Загружает только moves для списка игроков."""

        def _load(pipe):
            for cid in char_ids:
                pipe.json().get(Rk.get_combat_moves_key(session_id, str(cid)))

        results = await self.redis.execute_pipeline(_load)
        return {cid: res for cid, res in zip(char_ids, results, strict=False) if res}

    async def push_actions_batch(self, session_id: str, actions_json: list[str]) -> None:
        """Запись резолвленных задач в системную очередь q:actions."""
        if not actions_json:
            return
        key = Rk.get_rbc_queue_key(session_id)

        def _push(pipe):
            pipe.rpush(key, *actions_json)

        await self.redis.execute_pipeline(_push)

    async def transfer_intents_to_actions(
        self, session_id: str, actions_json: list[str], deletes: list[dict[str, Any]]
    ) -> None:
        """
        [ATOMIC] Переносит резолвленные намерения (Intents) в очередь действий (Actions).

        actions_json: Список JSON-строк (CombatActionDTO) для добавления в очередь.
        deletes: Список словарей { "char_id": int, "strategy": str, "move_id": str } для удаления.
        """
        if not actions_json and not deletes:
            return

        def _fill_pipe(pipe: Pipeline) -> None:
            # 1. Добавляем в системную очередь сессии q:actions
            if actions_json:
                queue_key = Rk.get_rbc_queue_key(session_id)
                pipe.rpush(queue_key, *actions_json)

            # 2. Удаляем пули из хранилища намерений игрока
            for item in deletes:
                moves_key = Rk.get_combat_moves_key(session_id, str(item["char_id"]))
                # Путь удаления: $.exchange.uuid_1
                path = f"$.{item['strategy']}.{item['move_id']}"
                pipe.json().delete(moves_key, path)  # type: ignore
                # Продлеваем TTL
                pipe.expire(moves_key, 300)

        await self.redis.execute_pipeline(_fill_pipe)

    # ==========================================================================
    # 4. БЛОКИРОВКА (BUSY LOCK)
    # ==========================================================================

    async def check_and_lock_busy_for_collector(self, session_id: str) -> bool:
        """
        Проверяет, свободна ли сессия. Если свободна — резервирует её для воркера.
        Используется чтобы не плодить одинаковые задачи в ARQ.

        Возвращает True, если удалось поставить метку "pending" (значит, можно ставить задачу).
        Возвращает False, если занято (другой воркер или уже в очереди).
        """
        key = f"combat:rbc:{session_id}:sys:busy"

        # Пытаемся поставить временную метку "pending" (в ожидании воркера)
        # Если ключ уже есть (стоит метка другого воркера или pending) - вернет False
        # TTL 30 сек - защита от зависания в очереди
        return await self.redis.redis_client.set(key, "pending", nx=True, ex=30)  # type: ignore

    async def acquire_worker_lock(self, session_id: str, worker_id: str) -> bool:
        """
        [WORKER] Захват лока (перезапись pending).
        """
        key = f"combat:rbc:{session_id}:sys:busy"
        script = """
        local val = redis.call('GET', KEYS[1])
        if val == 'pending' or not val then
            redis.call('SET', KEYS[1], ARGV[1], 'EX', 60)
            return 1
        end
        return 0
        """
        res = await self.redis.eval_script(script, keys=[key], args=[worker_id])
        return bool(res)

    async def check_worker_lock(self, session_id: str, worker_id: str) -> bool:
        """
        [WORKER] Проверка, что лок все еще принадлежит нам.
        """
        key = f"combat:rbc:{session_id}:sys:busy"
        val = await self.redis.get_value(key)
        return val == worker_id

    async def release_worker_lock_safe(self, session_id: str, worker_id: str) -> None:
        """
        [WORKER] Снятие лока только если он наш.
        """
        key = f"combat:rbc:{session_id}:sys:busy"
        script = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
            return redis.call('DEL', KEYS[1])
        else
            return 0
        end
        """
        await self.redis.eval_script(script, keys=[key], args=[worker_id])

    # ==========================================================================
    # 5. КОММИТ (BATCH SAVING)
    # ==========================================================================

    async def commit_battle_results(self, session_id: str, updates: dict, logs: list[str], processed_count: int):
        """
        Массовое сохранение итогов раунда через Pipeline.
        """

        def _commit(pipe: Pipeline):
            for cid, data in updates.items():
                base = f"{Rk.get_rbc_actor_key(session_id, str(cid))}"

                if "state" in data:
                    pipe.hset(f"{base}:state", mapping=data["state"])

                if "abilities" in data:
                    pipe.json().set(f"{base}:active_abilities", "$", data["abilities"])  # type: ignore

                if "xp" in data:
                    pipe.json().set(f"{base}:data_xp", "$", data["xp"])  # type: ignore

                if "raw_temp" in data:
                    pipe.json().set(f"{base}:raw", ".temp", data["raw_temp"])  # type: ignore

            if logs:
                pipe.rpush(Rk.get_combat_log_key(session_id), *logs)

            if processed_count > 0:
                pipe.ltrim(Rk.get_rbc_queue_key(session_id), processed_count, -1)

        await self.redis.execute_pipeline(_commit)

    # ==========================================================================
    # 6. ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ==========================================================================

    async def get_actor_state(self, session_id: str, char_id: int) -> dict[str, str] | None:
        key = f"{Rk.get_rbc_actor_key(session_id, str(char_id))}:state"
        return await self.redis.get_all_hash(key)

    async def get_actor_raw(self, session_id: str, char_id: int) -> dict[str, Any] | None:
        key = f"{Rk.get_rbc_actor_key(session_id, str(char_id))}:raw"
        data = await self.redis.json_get(key)
        if isinstance(data, list) and data:
            return data[0]
        return data if isinstance(data, dict) else {}

    async def get_combat_log_list(self, session_id: str) -> list[str]:
        key = Rk.get_combat_log_key(session_id)
        return await self.redis.get_list_range(key)

    async def cleanup_rbc_session(self, session_id: str, history_ttl: int = 86400) -> None:
        def _cleanup(pipe: Pipeline) -> None:
            pipe.delete(Rk.get_rbc_targets_key(session_id))
            pipe.delete(Rk.get_rbc_queue_key(session_id))
            pipe.expire(Rk.get_rbc_meta_key(session_id), history_ttl)
            pipe.expire(Rk.get_combat_log_key(session_id), history_ttl)

        await self.redis.execute_pipeline(_cleanup)
